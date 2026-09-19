# -*- coding: utf-8 -*-
"""i18n 缺词批量机翻（EN -> zh-Hans），用于补齐 Claude 前端语言包。

- 基准：官方安装包缓存里的**原始** en-US.json（不是被我们覆盖过的）
- 已译条目保持不动；断点续跑（.workbuddy/i18n-zh-ckpt.json）
- 严格 JSON 往返、5/3/1 并发可调、429 退避、失败批落盘
- 完成后合并回 语言包/ion-dist-i18n-zh-Hans.json（自动备份 .orig.json）

⚠ 计费提醒：切换 URL/MODEL 前先确认该模型是否计费，不确定就问用户。
   默认使用阿里云百炼的**免费**模型 deepseek-v4.1-flash（推理模型：要给足 max_tokens）。
"""
import json, zipfile, os, io, time, re, glob, threading, sys
from concurrent.futures import ThreadPoolExecutor, as_completed
import urllib.request, urllib.error

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, '.workbuddy')
CKPT = os.path.join(DATA, 'i18n-zh-ckpt.json')
ZH_PACK = os.path.join(ROOT, '语言包', 'ion-dist-i18n-zh-Hans.json')

# ---- 通道配置（改这里切换供应商）-----------------------------------------
URL = 'https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions'
MODEL = 'deepseek-v4.1-flash'          # ★ 百炼免费档；deepseek-v3.2 是计费的，勿用
STYLE = 'openai'                        # openai | anthropic
KEY_FILE = os.path.join(DATA, 'ali.key')
# 其它通道备选：
#   Z.ai     URL='https://api.z.ai/api/paas/v4/chat/completions'  MODEL='glm-4.7-flash'  KEY=zai.key
#   DeepSeek URL='https://api.deepseek.com/anthropic/v1/messages' MODEL='deepseek-chat' STYLE='anthropic'
BATCH = 40
WORKERS = 3
MAX_TOKENS = 8000
# ---------------------------------------------------------------------------

SYS = ("You are a professional UI localizer for the Claude Desktop app. "
       "Translate each English UI string into natural Simplified Chinese. "
       "STRICT RULES: 1) Keep placeholders exactly: {name}, {count}, <tag>, %s etc. "
       "2) Never translate brand/product words: Claude, Anthropic, Artifacts, MCP, Slack, OAuth, API, URL, ID. "
       "3) Concise UI tone, no quotes added. "
       "4) Reply with ONLY a strict JSON object: {\"<original english>\": \"<chinese>\"} for every input. No markdown.")

lock = threading.Lock()
done_count = [0]
fail_count = [0]


def log(m):
    os.makedirs(DATA, exist_ok=True)
    with io.open(os.path.join(DATA, 'i18n-translate.log'), 'a', encoding='utf-8') as f:
        f.write(time.strftime('[%H:%M:%S] ') + m + '\n')


def get_key():
    if os.path.isfile(KEY_FILE):
        k = io.open(KEY_FILE, encoding='utf-8-sig').read().strip()
        if k:
            return k
    raise SystemExit('缺少 API Key：请写入 %s' % KEY_FILE)


def find_base_msix():
    la = os.environ.get('LOCALAPPDATA', '')
    cands = [c for c in glob.glob(os.path.join(la, 'ClaudeInstaller', 'cache', '*.msix'))
             if 'zh' not in os.path.basename(c).lower()]
    if not cands:
        raise SystemExit('找不到官方安装包缓存（%s\\ClaudeInstaller\\cache\\*.msix）' % la)
    cands.sort(key=lambda p: os.path.getmtime(p), reverse=True)
    return cands[0]


def load_untranslated():
    z = zipfile.ZipFile(find_base_msix())
    en = json.loads(z.read('app/resources/ion-dist/i18n/en-US.json').decode('utf-8'))
    zh = json.load(open(ZH_PACK, encoding='utf-8-sig'))
    return {k: v for k, v in en.items() if zh.get(k, None) == v}, zh


def call_llm(key, batch):
    user = json.dumps(batch, ensure_ascii=False)
    if STYLE == 'openai':
        body = json.dumps({'model': MODEL, 'temperature': 0.0, 'max_tokens': MAX_TOKENS,
                           'messages': [{'role': 'system', 'content': SYS},
                                        {'role': 'user', 'content': user}]}).encode('utf-8')
        req = urllib.request.Request(URL, data=body, headers={
            'Content-Type': 'application/json', 'Authorization': 'Bearer ' + key})
        with urllib.request.urlopen(req, timeout=300) as resp:
            data = json.loads(resp.read().decode('utf-8'))
        msg = data['choices'][0]['message']
        return msg.get('content') or msg.get('reasoning_content') or ''
    body = json.dumps({'model': MODEL, 'max_tokens': MAX_TOKENS, 'temperature': 0.0,
                       'system': SYS, 'messages': [{'role': 'user', 'content': user}]}).encode('utf-8')
    req = urllib.request.Request(URL, data=body, headers={
        'Content-Type': 'application/json', 'x-api-key': key, 'anthropic-version': '2023-06-01'})
    with urllib.request.urlopen(req, timeout=300) as resp:
        data = json.loads(resp.read().decode('utf-8'))
    return ''.join(b.get('text', '') for b in data.get('content', []))


def parse_json_loose(s):
    s = (s or '').strip()
    if s.startswith('```'):
        s = re.sub(r'^```[a-zA-Z]*\n?', '', s)
        s = re.sub(r'\n?```$', '', s)
    return json.loads(s)


def norm(s):
    """模型常把弯引号转成直引号 → 键匹配做归一化。"""
    return (s.replace('\u2019', "'").replace('\u2018', "'")
             .replace('\u201c', '"').replace('\u201d', '"')
             .replace('\u00a0', ' ').strip())


def translate_batch(key, batch, ckpt, save):
    for attempt in range(4):
        try:
            out = parse_json_loose(call_llm(key, batch))
            if not isinstance(out, dict):
                raise ValueError('not a dict')
            idx = {norm(k): v for k, v in out.items()}
            ok = {}
            for k in batch:
                t = idx.get(norm(k))
                if isinstance(t, str) and t.strip() and t.strip() != k:
                    ok[k] = t
            with lock:
                ckpt.update(ok)
                done_count[0] += len(ok)
                fail_count[0] += len(batch) - len(ok)
                save()
            log('batch ok %d/%d (总 %d)' % (len(ok), len(batch), done_count[0]))
            return
        except Exception as e:
            log('batch retry %d: %s (%d 条)' % (attempt + 1, str(e)[:120], len(batch)))
            time.sleep((10 if '429' in str(e) else 3) * (attempt + 1))
    with lock:
        fail_count[0] += len(batch)
        with io.open(CKPT + '.failed.json', 'a', encoding='utf-8') as f:
            json.dump(batch, f, ensure_ascii=False)
            f.write('\n')
    log('batch 永久失败 %d 条' % len(batch))


def main():
    key = get_key()
    untranslated, zh_pack = load_untranslated()
    ckpt = json.load(open(CKPT, encoding='utf-8-sig')) if os.path.isfile(CKPT) else {}
    todo = {k: v for k, v in untranslated.items() if k not in ckpt}
    log('start：未译 %d，已断点 %d，本次 %d' % (len(untranslated), len(ckpt), len(todo)))

    def save():
        tmp = CKPT + '.tmp'
        with io.open(tmp, 'w', encoding='utf-8') as f:
            json.dump(ckpt, f, ensure_ascii=False)
        os.replace(tmp, CKPT)

    items = list(todo.items())
    batches = [dict(items[i:i + BATCH]) for i in range(0, len(items), BATCH)]
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        futs = [ex.submit(translate_batch, key, b, ckpt, save) for b in batches]
        for i, f in enumerate(as_completed(futs)):
            f.result()
            if (i + 1) % 20 == 0:
                log('进度 %d/%d 批，%.1f 分钟' % (i + 1, len(batches), (time.time() - t0) / 60))

    zh_pack.update(ckpt)
    backup = ZH_PACK + '.orig.json'
    if not os.path.isfile(backup):
        import shutil
        shutil.copyfile(ZH_PACK, backup)
    with io.open(ZH_PACK, 'w', encoding='utf-8') as f:
        json.dump(zh_pack, f, ensure_ascii=False, separators=(',', ':'))
    print('DONE. 新增 %d，失败 %d' % (len(ckpt), fail_count[0]))


if __name__ == '__main__':
    main()
