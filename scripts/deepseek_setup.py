# -*- coding: utf-8 -*-
"""Claude Desktop -> DeepSeek 3P 网关配置（写 HKCU 策略，无需管理员）。

用法：
    python deepseek_setup.py apply [API_KEY]   # 写策略（key 也可预先放 .workbuddy/deepseek.key）
    python deepseek_setup.py remove            # 删除策略（恢复官方推理）
    python deepseek_setup.py status            # 查看当前状态

配套：deepseek-3p-proxy.py（本地中继，必须先运行）
"""
import sys, os, json, io

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
KEY_FILE = os.path.join(ROOT, '.workbuddy', 'deepseek.key')
REG_PATH = r'SOFTWARE\Policies\Claude'
RELAY_PORT = 17871
RELAY_BASE = 'http://127.0.0.1:%d' % RELAY_PORT

# 对外路由名 -> DeepSeek 真名 -> 选择器显示名（须与 deepseek-3p-proxy.py 的 ALIAS 一致）
ALIAS = [('claude-sonnet-4-5', 'deepseek-v4-pro', 'DeepSeek V4 Pro'),
         ('claude-haiku-4-5', 'deepseek-v4-flash', 'DeepSeek V4 Flash')]


def read_key():
    if os.path.isfile(KEY_FILE):
        k = io.open(KEY_FILE, encoding='utf-8-sig').read().strip()
        if k:
            return k
    return ''


def write_key(k):
    os.makedirs(os.path.dirname(KEY_FILE), exist_ok=True)
    io.open(KEY_FILE, 'w', encoding='utf-8').write(k.strip())


def apply(api_key=None, verbose=True):
    import winreg
    api_key = (api_key or read_key()).strip()
    if not api_key:
        print('  [错误] 缺少 API Key：把它写入 %s' % KEY_FILE)
        return False
    write_key(api_key)
    models = [{'name': n, 'labelOverride': label} for n, _, label in ALIAS]
    vals = {
        'inferenceProvider': 'gateway',
        'inferenceGatewayBaseUrl': RELAY_BASE,
        'inferenceGatewayApiKey': api_key,
        'inferenceGatewayAuthScheme': 'bearer',
        'modelDiscoveryEnabled': 'true',
        'inferenceModels': json.dumps(models, ensure_ascii=False, separators=(',', ':')),
    }
    try:
        k = winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, REG_PATH, 0, winreg.KEY_SET_VALUE)
        for n, v in vals.items():
            winreg.SetValueEx(k, n, 0, winreg.REG_SZ, v)
        winreg.CloseKey(k)
    except Exception as e:
        print('  [错误] 写注册表失败：%s: %s' % (type(e).__name__, e))
        return False
    if verbose:
        print('  已写入 HKCU\\%s：' % REG_PATH)
        for n in vals:
            shown = (api_key[:8] + '...') if n.endswith('ApiKey') else vals[n]
            print('    %-28s = %s' % (n, shown))
        print('  模型映射：')
        for n, real, label in ALIAS:
            print('    %-20s -> %-20s 显示名：%s' % (n, real, label))
    return True


def remove(verbose=True):
    import winreg
    try:
        winreg.DeleteKey(winreg.HKEY_CURRENT_USER, REG_PATH)
        if verbose:
            print('  已删除 HKCU\\%s（Claude 恢复官方推理）' % REG_PATH)
    except FileNotFoundError:
        if verbose:
            print('  策略本就不存在')
    except Exception as e:
        print('  [错误] 删除失败：%s: %s' % (type(e).__name__, e))
        return False
    return True


def status():
    import winreg, socket
    print('  API Key 文件：%s' % ('已就位' if read_key() else '缺失'))
    try:
        k = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_PATH)
        i, found = 0, {}
        while True:
            try:
                n, v, _ = winreg.EnumValue(k, i)
                found[n] = v
                i += 1
            except OSError:
                break
        print('  注册表策略：已配置（%d 项）' % len(found))
        for n in ('inferenceProvider', 'inferenceGatewayBaseUrl',
                  'modelDiscoveryEnabled', 'inferenceModels'):
            if n in found:
                print('    %-28s = %s' % (n, str(found[n])[:110]))
    except FileNotFoundError:
        print('  注册表策略：未配置')
    try:
        s = socket.create_connection(('127.0.0.1', RELAY_PORT), timeout=1)
        s.close()
        running = True
    except Exception:
        running = False
    print('  本地中继(127.0.0.1:%d)：%s' % (RELAY_PORT, '运行中' if running else '未运行'))
    return True


if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'status'
    print('=== Claude <-> DeepSeek 配置：%s ===' % cmd)
    if cmd == 'apply':
        sys.exit(0 if apply(sys.argv[2] if len(sys.argv) > 2 else None) else 1)
    elif cmd == 'remove':
        sys.exit(0 if remove() else 1)
    else:
        status()
