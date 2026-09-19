# -*- coding: utf-8 -*-
"""DeepSeek -> Claude Desktop 3P 网关本地中继（127.0.0.1:17871）。

为什么需要它：
  · Claude Desktop 要求网关的「模型列表 /v1/models」与「对话 /v1/messages」共用一个 base URL；
  · DeepSeek 的模型列表在 <域名>/v1/models，对话端点在 <域名>/anthropic/v1/messages
    —— 前缀不同，单个 base URL 无法同时满足；
  · 且应用对模型名有硬性校验（必须 Anthropic 风格），否则日志报
    "Gateway /v1/models returned 0 usable models" → 配置被判 invalid_config
    → Claude 顶部弹「管理员配置无法使用」，模型选择器为空。

本中继做两件事：
  1. /v1/models 自己应答（返回下面的 Anthropic 风格路由名）
  2. 其它 /v1/* 原样转发到 https://api.deepseek.com/anthropic/v1/*
     并在转发前把路由名改写回 DeepSeek 真实模型名（见 ALIAS）

开关：
  MODE = 'alias'      对外暴露 Anthropic 风格名 + 转发前改写（默认，唯一可用方案）
         'passthrough' 直接暴露 DeepSeek 真名（会被应用过滤，仅调试用）
"""
import json, os, io, ssl, time, http.client
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
HOST, PORT = '127.0.0.1', 17871
UPSTREAM_HOST = 'api.deepseek.com'
UPSTREAM_PREFIX = '/anthropic'
KEY_FILE = os.path.join(ROOT, '.workbuddy', 'deepseek.key')
LOG_FILE = os.path.join(ROOT, '.workbuddy', 'proxy-3p.log')

MODE = 'alias'
# 对外路由名 -> DeepSeek 真实模型名（须与 deepseek_setup.py 的 ALIAS 一致）
ALIAS = {'claude-sonnet-4-5': 'deepseek-v4-pro', 'claude-haiku-4-5': 'deepseek-v4-flash'}
MODELS = list(ALIAS.keys())


def log(msg):
    try:
        os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
        with io.open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(time.strftime('[%Y-%m-%d %H:%M:%S] ') + msg + '\n')
    except Exception:
        pass


def local_key():
    try:
        return io.open(KEY_FILE, encoding='utf-8-sig').read().strip()
    except Exception:
        return ''


class Handler(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'

    def log_message(self, fmt, *args):
        pass

    def _json(self, code, obj):
        body = json.dumps(obj).encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path.split('?')[0].rstrip('/') == '/v1/models':
            names = MODELS if MODE == 'passthrough' else list(ALIAS.keys())
            log('GET /v1/models -> %s (%s)' % (names, MODE))
            self._json(200, {'object': 'list',
                             'data': [{'id': n, 'object': 'model', 'owned_by': 'deepseek'} for n in names]})
            return
        self._relay('GET', None)

    def do_POST(self):
        n = int(self.headers.get('Content-Length') or 0)
        body = self.rfile.read(n) if n else b''
        if MODE == 'alias' and body:
            try:
                obj = json.loads(body.decode('utf-8'))
                if isinstance(obj, dict) and obj.get('model') in ALIAS:
                    log('alias rewrite %s -> %s' % (obj['model'], ALIAS[obj['model']]))
                    obj['model'] = ALIAS[obj['model']]
                    body = json.dumps(obj).encode('utf-8')
            except Exception as e:
                log('alias rewrite skipped: %s' % e)
        self._relay('POST', body)

    def _relay(self, method, body):
        headers = {}
        for h in ('x-api-key', 'authorization', 'anthropic-version', 'anthropic-beta',
                  'content-type', 'accept'):
            v = self.headers.get(h)
            if v:
                headers[h] = v
        if 'x-api-key' not in headers and 'authorization' not in headers:
            k = local_key()
            if k:
                headers['x-api-key'] = k
        headers.setdefault('content-type', 'application/json')
        if body is not None:
            headers['Content-Length'] = str(len(body))
        try:
            conn = http.client.HTTPSConnection(UPSTREAM_HOST, timeout=300,
                                               context=ssl.create_default_context())
            conn.request(method, UPSTREAM_PREFIX + self.path, body=body, headers=headers)
            up = conn.getresponse()
            log('%s %s -> %d' % (method, self.path, up.status))
            self.send_response(up.status)
            for h, v in up.getheaders():
                if h.lower() in ('transfer-encoding', 'content-length', 'connection'):
                    continue
                self.send_header(h, v)
            cl = up.getheader('Content-Length')
            if cl is not None:
                self.send_header('Content-Length', cl)
            else:
                self.send_header('Transfer-Encoding', 'chunked')
            self.end_headers()
            while True:
                chunk = up.read(1024)
                if not chunk:
                    break
                if cl is None:
                    self.wfile.write(b'%x\r\n' % len(chunk) + chunk + b'\r\n')
                else:
                    self.wfile.write(chunk)
            if cl is None:
                self.wfile.write(b'0\r\n\r\n')
            self.wfile.flush()
            conn.close()
        except Exception as e:
            log('relay error %s %s: %s' % (method, self.path, e))
            self._json(502, {'type': 'error', 'error': {'type': 'upstream_error', 'message': str(e)}})


if __name__ == '__main__':
    log('=== relay start %s:%d MODE=%s models=%s ===' % (HOST, PORT, MODE, MODELS))
    print('DeepSeek 3P 中继已启动：http://%s:%d  (MODE=%s)' % (HOST, PORT, MODE))
    print('  GET  /v1/models -> 本地应答（模型发现）')
    print('  POST /v1/*      -> 转发到 https://%s%s/v1/*（并改写模型名）' % (UPSTREAM_HOST, UPSTREAM_PREFIX))
    print('Ctrl+C 停止。')
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
