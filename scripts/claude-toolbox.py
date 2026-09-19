# -*- coding: utf-8 -*-
"""睡醒的夜猫子 · Claude 桌面版工具箱

双击上级目录的 `Claude一键汉化.cmd` 打开本菜单：
  [1] 汉化 Claude          重建中文补丁包并安装
  [2] 配置 DeepSeek 网关   写 HKCU 策略（含模型显示名），指向本地中继
  [3] 启动 DeepSeek 中继   新开窗口运行本地中继（127.0.0.1:17871）
  [4] 一键全装             1 + 2 + 3（推荐）
  [5] 状态检查             版本 / 语言包 / 策略 / 中继
  [6] 还原官方版           装回官方 msix（英文、无补丁）
  [7] 还原 DeepSeek        删除 3P 策略（恢复官方推理）
  [0] 退出
"""
import os, sys, glob, socket, subprocess, time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PY = sys.executable or 'python'

PIPELINE = os.path.join(HERE, 'build_and_install.py')
PROXY = os.path.join(HERE, 'deepseek-3p-proxy.py')
SETUP = os.path.join(HERE, 'deepseek_setup.py')
WINDOWSAPPS = r'C:\Program Files\WindowsApps'
RELAY_PORT = 17871
PFN = 'pzs8sxrjxfjjc'

BANNER = r"""
  ____  _                 _        _   _  __        _         _
 / ___|| |  __ _ _   _  __| | ___  | | | |/ /_ _ _ _(_)__ __ _| |
| |    | | / _` | | | |/ _` |/ _ \ | |_| | ' \| ' \| / _/ _` |_|
| |___ | || (_| | |_| | (_| |  __/ |  _  |_||_|_||_|_\__\__,_(_)
 \____||_| \__,_|\__,_|\__,_|\___| |_| |_|  睡醒的夜猫子 · 工具箱
"""


def line(ch='-', n=66):
    print(ch * n)


def ps(cmd):
    try:
        r = subprocess.run(['powershell', '-NoProfile', '-Command', cmd],
                           capture_output=True, timeout=90)
        return r.stdout.decode('utf-8', 'replace').strip()
    except Exception:
        return ''


def installed_version():
    return ps("(Get-AppxPackage -Name 'Claude*').Version") or '未安装'


def base_msix():
    la = os.environ.get('LOCALAPPDATA', '')
    cands = [c for c in glob.glob(os.path.join(la, 'ClaudeInstaller', 'cache', '*.msix'))
             if 'zh' not in os.path.basename(c).lower()]
    cands.sort(key=lambda p: os.path.getmtime(p), reverse=True)
    return cands[0] if cands else None


def localization_state():
    v = installed_version()
    if not v or v.startswith('未'):
        return '未安装 Claude', False
    d = os.path.join(WINDOWSAPPS, 'Claude_%s_x64__%s' % (v, PFN))
    if not os.path.isdir(d):
        return '安装目录不可读', False
    res = os.path.join(d, 'app', 'resources')
    ion = os.path.join(res, 'ion-dist')
    parts = []
    parts.append('壳' + ('✓' if os.path.isfile(os.path.join(res, 'zh-CN.json')) else '✗'))
    parts.append('前端' + ('✓' if os.path.isfile(os.path.join(ion, 'i18n', 'zh-Hans.json'))
                          and os.path.isfile(os.path.join(ion, 'i18n', 'zh-CN.json')) else '✗'))
    parts.append('替换脚本' + ('✓' if os.path.isfile(os.path.join(ion, 'zh-hans-patch.js')) else '✗'))
    try:
        injected = b'__claudeZhCnPreload' in open(os.path.join(res, 'app.asar'), 'rb').read()
    except Exception:
        injected = False
    parts.append('主视图注入' + ('✓' if injected else '✗'))
    return ' '.join(parts), injected


def relay_running():
    try:
        s = socket.create_connection(('127.0.0.1', RELAY_PORT), timeout=1)
        s.close()
        return True
    except Exception:
        return False


def run(cmd, title=None):
    if title:
        line('=')
        print('>>', title)
        line('=')
    p = subprocess.Popen(cmd, cwd=ROOT)
    p.wait()
    return p.returncode


def start_relay():
    if relay_running():
        print('  中继已在运行（127.0.0.1:%d）' % RELAY_PORT)
        return True
    flags = getattr(subprocess, 'CREATE_NEW_CONSOLE', 0)
    subprocess.Popen([PY, PROXY], cwd=ROOT, creationflags=flags)
    for _ in range(20):
        time.sleep(0.5)
        if relay_running():
            print('  中继已启动（127.0.0.1:%d）' % RELAY_PORT)
            return True
    print('  [警告] 中继未监听端口，请手动双击「启动DeepSeek代理.cmd」查看报错')
    return False


def do_localize():
    return run([PY, PIPELINE], '汉化：重建 + 安装（约 2~4 分钟，请勿关闭窗口）') == 0


def do_deepseek():
    print('  提示：如需换 Key，先编辑 .workbuddy\\deepseek.key（或首次由本步写入）')
    return run([PY, SETUP, 'apply'], '配置 DeepSeek 网关（写 HKCU 策略）') == 0


def do_restore_official():
    m = base_msix()
    if not m:
        print('  找不到官方安装包缓存（%LOCALAPPDATA%\\ClaudeInstaller\\cache\\*.msix）')
        return False
    cmd = ['powershell', '-NoProfile', '-Command',
           "Add-AppxPackage -Path '%s' -ForceUpdateFromAnyVersion "
           "-ForceApplicationShutdown -ErrorAction Stop; Write-Output RESTORE-OK" % m]
    return run(cmd, '还原官方版（英文、无补丁）') == 0


def do_remove_deepseek():
    return run([PY, SETUP, 'remove'], '删除 DeepSeek 策略') == 0


def show_status():
    state, injected = localization_state()
    line('=')
    print('状态面板')
    line('=')
    print('  Claude 版本    : %s' % installed_version())
    print('  汉化文件       : %s' % state)
    print('  官方包缓存     : %s' % ('✓' if base_msix() else '✗ 缺失'))
    print('  DeepSeek 中继  : %s' % ('运行中' if relay_running() else '未运行'))
    line('-')
    subprocess.run([PY, SETUP, 'status'], cwd=ROOT)
    line('=')


def menu():
    while True:
        os.system('cls' if os.name == 'nt' else 'clear')
        print(BANNER)
        state, injected = localization_state()
        line('=')
        print('  Claude %s   |   中继 %s   |   汉化 %s'
              % (installed_version(), '开' if relay_running() else '关',
                 '已装' if injected else '未装'))
        line('=')
        print('  [1] 汉化 Claude（重建 + 安装）')
        print('  [2] 配置 DeepSeek 网关（写注册表）')
        print('  [3] 启动 DeepSeek 中继（127.0.0.1:%d）' % RELAY_PORT)
        print('  [4] 一键全装（1 + 2 + 3）')
        print('  [5] 状态检查')
        print('  [6] 还原官方版（英文）')
        print('  [7] 还原 DeepSeek（删策略）')
        print('  [0] 退出')
        line('=')
        try:
            c = input('  请选择: ').strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return
        if c == '1':
            do_localize()
        elif c == '2':
            do_deepseek()
            print('  改完注册表需重启 Claude 生效')
        elif c == '3':
            start_relay()
        elif c == '4':
            if do_localize():
                do_deepseek()
                start_relay()
                print('  全部完成：重启 Claude 即为中文 + DeepSeek 模型')
        elif c == '5':
            show_status()
        elif c == '6':
            do_restore_official()
        elif c == '7':
            do_remove_deepseek()
        elif c == '0':
            return
        else:
            print('  无效选项')
        line()
        input('  回车返回菜单...')


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'status':
        show_status()
    else:
        menu()
