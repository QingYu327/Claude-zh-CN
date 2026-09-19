# -*- coding: utf-8 -*-
"""Claude Desktop 中文补丁构建管线（包内路径自适应）

流程：
  1) 用官方安装包缓存解包（MakeAppx unpack）
  2) 关闭 claude.exe 的 asar 完整性熔丝（否则改过 asar 会打不开）
  3) 注入主视图 preload（mainView.js / claudePagePreview.js）
  4) 前端补丁（语言包双命名 + 白名单 + DOM 替换脚本）
  5) 版本号 = 已装版本 + 0.0.0.1（避免 0x80073CFB）
  6) 打包 → 签名 → 安装（Add-AppxPackage）
每一步都做断言校验：脚本报成功 ≠ 生效，必须读回来确认。
"""
import subprocess, os, re, sys, shutil, zipfile, glob, tempfile, json

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)                       # 发布包根目录
PAYLOAD = os.path.join(ROOT, '语言包')
DATA = os.path.join(ROOT, '.workbuddy')            # 运行数据（.gitignore 排除）
PY = sys.executable or 'python'
PATCHER = os.path.join(HERE, 'patch_asar.py')
PRELOAD = os.path.join(HERE, 'claude-zh-preload.js')
SIGN_SUBJECT = 'Anthropic'

sys.path.insert(0, HERE)
import patch_frontend  # noqa: E402


def find_tool(name):
    pats = [
        os.path.join(os.environ.get('ProgramFiles(x86)', r'C:\Program Files (x86)'),
                     'Windows Kits', '10', 'bin', '*', 'x64', name),
        os.path.join(os.environ.get('ProgramFiles', r'C:\Program Files'),
                     'Windows Kits', '10', 'bin', '*', 'x64', name),
    ]
    found = []
    for p in pats:
        found += glob.glob(p)
    if not found:
        raise SystemExit('找不到 %s：请安装 Windows SDK（含 MakeAppx/signtool）' % name)

    def ver(path):
        m = re.search(r'[\\/]bin[\\/](10\.\d+\.\d+\.\d+)[\\/]', path)
        return [int(x) for x in m.group(1).split('.')] if m else [0]
    return sorted(found, key=ver)[-1]


def find_base_msix():
    la = os.environ.get('LOCALAPPDATA', '')
    cands = [c for c in glob.glob(os.path.join(la, 'ClaudeInstaller', 'cache', '*.msix'))
             if 'zh' not in os.path.basename(c).lower()]
    if not cands:
        raise SystemExit('找不到官方安装包缓存 %s\\ClaudeInstaller\\cache\\*.msix\n'
                         '请先用官方安装器正常安装一次 Claude Desktop。' % la)
    cands.sort(key=lambda p: os.path.getmtime(p), reverse=True)
    return cands[0]


def run(cmd):
    print('RUN:', ' '.join('"%s"' % c if ' ' in c else c for c in cmd))
    r = subprocess.run(cmd, capture_output=True, timeout=900)
    out = r.stdout.decode('utf-8', 'replace')
    err = r.stderr.decode('gbk', 'replace')       # PowerShell 报错是 GBK
    r.stdout, r.stderr = out, err
    print('  RC:', r.returncode)
    if out.strip():
        print('  OUT:', out.strip()[:1000])
    if err.strip():
        print('  ERR:', err.strip()[:1000])
    return r


def ps(script):
    return run(['powershell', '-NoProfile', '-Command', script])


def main():
    MK = find_tool('makeappx.exe')
    ST = find_tool('signtool.exe')
    BASE = find_base_msix()
    WR = os.path.join(tempfile.gettempdir(), 'claude-zh-cn-work')
    UNPACKED = os.path.join(WR, 'unpacked')
    ASAR = os.path.join(UNPACKED, 'app', 'resources', 'app.asar')
    TMPASAR = os.path.join(WR, 'app.patched.asar')
    MANI = os.path.join(UNPACKED, 'AppxManifest.xml')
    NEW = os.path.join(WR, 'Claude-zh-CN.msix')
    print('== 基础包：%s' % BASE)
    print('== 工具  ：%s' % MK)

    # [1] 解包
    if os.path.isdir(WR):
        shutil.rmtree(WR, ignore_errors=True)
    os.makedirs(UNPACKED, exist_ok=True)
    r = run([MK, 'unpack', '/p', BASE, '/d', UNPACKED, '/o'])
    assert r.returncode == 0 and os.path.isfile(ASAR), 'UNPACK FAILED'
    print('[1] 解包完成，asar %d 字节' % os.path.getsize(ASAR))

    # [2] 关 asar 完整性熔丝
    SENTINEL = b'dL7pKGdnNz796PbbjQWNKmHXBZaB9tsX'
    FUSE_IDX = 4          # EnableEmbeddedAsarIntegrityValidation
    exe = os.path.join(UNPACKED, 'app', 'claude.exe')
    with open(exe, 'rb') as f:
        pos, tail, found = 0, b'', -1
        while True:
            chunk = f.read(4 * 1024 * 1024)
            if not chunk:
                break
            buf = tail + chunk
            i = buf.find(SENTINEL)
            if i >= 0:
                found = pos - len(tail) + i
                break
            tail = buf[-(len(SENTINEL) - 1):]
            pos += len(chunk)
    assert found >= 0, '熔丝哨兵未找到（应用版本可能变化）'
    off = found + 32 + 2 + FUSE_IDX
    with open(exe, 'r+b') as f:
        f.seek(off)
        cur = f.read(1)
        assert cur == b'\x31', '熔丝值异常：%r' % cur
        f.seek(off)
        f.write(b'\x30')
    with open(exe, 'rb') as f:
        f.seek(off)
        assert f.read(1) == b'\x30', '熔丝翻转失败'
    print('[2] asar 完整性熔丝已关闭 @%d' % off)

    # [3] preload 合并（源 + dom-map 构建期并集）并注入 asar
    src = open(PRELOAD, 'r', encoding='utf-8').read()
    dom_map = json.load(open(os.path.join(PAYLOAD, 'zh-hans-dom-map.json'), encoding='utf-8-sig'))
    present = set()
    for m in re.finditer(r'"((?:[^"\\]|\\.)+)"\s*:', src):
        try:
            present.add(json.loads('"%s"' % m.group(1)))
        except Exception:
            pass
    extra = ['%s: %s' % (json.dumps(k, ensure_ascii=False), json.dumps(v, ensure_ascii=False))
             for k, v in dom_map.items() if k not in present]
    marker = 'var MAP = {\n'
    assert marker in src, 'preload 里找不到 MAP 字面量'
    src = src.replace(marker, marker + '    // ==== merged from zh-hans-dom-map.json (%d) ====\n    %s,\n'
                      % (len(extra), ',\n    '.join(extra)), 1)
    merged = os.path.join(WR, 'preload.merged.js')
    open(merged, 'w', encoding='utf-8', newline='').write(src)
    print('[3] preload 合并：+%d 条' % len(extra))

    r = run([PY, PATCHER, ASAR, merged, TMPASAR])
    assert r.returncode == 0 and os.path.isfile(TMPASAR), 'PATCH FAILED'
    assert b'__claudeZhCnPreload' in open(TMPASAR, 'rb').read(), '注入标记缺失'
    os.replace(TMPASAR, ASAR)
    assert b'__claudeZhCnPreload' in open(ASAR, 'rb').read(), 'asar 未替换成功'
    print('[3] asar 注入完成，%d 字节' % os.path.getsize(ASAR))

    # [4] 前端补丁
    info = patch_frontend.patch(UNPACKED)
    print('[4] 前端补丁：', info)

    # [5] 版本号
    r = ps("(Get-AppxPackage -Name 'Claude*').Version")
    cur = r.stdout.strip()
    if re.match(r'^\d+\.\d+\.\d+\.\d+$', cur):
        p = [int(x) for x in cur.split('.')]
        nv = '%d.%d.%d.%d' % (p[0], p[1], p[2], p[3] + 1)
        print('    已装 %s -> 新版本 %s' % (cur, nv))
    else:
        mt0 = open(MANI, 'r', encoding='utf-8').read()
        m2 = re.search(r'Version="(\d+)\.(\d+)\.(\d+)\.(\d+)"', mt0)
        nv = '%s.%s.%s.%d' % (m2.group(1), m2.group(2), m2.group(3), int(m2.group(4)) + 1)
    mt = open(MANI, 'r', encoding='utf-8').read()
    m = re.search(r'(<Identity\b[^>]*?\bVersion=")(\d+)\.(\d+)\.(\d+)\.(\d+)(")', mt, re.S)
    assert m, '清单里找不到 Version'
    open(MANI, 'w', encoding='utf-8').write(mt[:m.start()] + m.group(1) + nv + m.group(6) + mt[m.end():])
    assert nv in open(MANI, 'r', encoding='utf-8').read(), '版本号写入失败'
    print('[5] 版本 ->', nv)

    for f in ('AppxSignature.p7x', 'AppxBlockMap.xml'):
        p = os.path.join(UNPACKED, f)
        if os.path.isfile(p):
            os.remove(p)

    # [6] 打包 + 签名
    r = run([MK, 'pack', '/d', UNPACKED, '/p', NEW, '/o'])
    assert r.returncode == 0 and os.path.isfile(NEW), 'PACK FAILED'
    print('[6] 打包完成 %.1f MB' % (os.path.getsize(NEW) / 1048576))
    r = ps("Get-ChildItem Cert:\\CurrentUser\\My | Where-Object { $_.Subject -like '*%s*' } "
           "| Select-Object -First 1 -ExpandProperty Thumbprint" % SIGN_SUBJECT)
    thumb = r.stdout.strip()
    if not thumb:
        raise SystemExit('未找到 Subject 含 %r 的签名证书，见 README「首次使用」。' % SIGN_SUBJECT)
    r = run([ST, 'sign', '/fd', 'SHA256', '/sha1', thumb, NEW])
    assert r.returncode == 0, 'SIGN FAILED'
    print('[6] 签名完成')

    # [7] 包内容校验
    z = zipfile.ZipFile(NEW)
    names = z.namelist()
    idx = z.read('app/resources/ion-dist/index.html').decode('utf-8', 'ignore')
    wl = any('"zh-Hans"' in z.read(n).decode('utf-8', 'ignore')
             for n in names if n.startswith('app/resources/ion-dist/assets/v1/')
             and n.endswith('.js') and 'shared' in n)
    print('[7] 包内校验：主视图注入', b'__claudeZhCnPreload' in z.read('app/resources/app.asar'),
          '| 前端zh-Hans', 'app/resources/ion-dist/i18n/zh-Hans.json' in names,
          '| 前端zh-CN', 'app/resources/ion-dist/i18n/zh-CN.json' in names,
          '| 替换脚本', 'app/resources/ion-dist/zh-hans-patch.js' in names,
          '| index注入', 'zh-hans-patch.js' in idx,
          '| 白名单', wl,
          '| 壳zh-CN', 'app/resources/zh-CN.json' in names)

    # [8] 安装
    r = ps("Add-AppxPackage -Path '%s' -ForceUpdateFromAnyVersion "
           "-ForceApplicationShutdown -ErrorAction Stop; Write-Output INSTALL-OK" % NEW)
    print('[8] 安装 RC =', r.returncode)
    if r.returncode != 0:
        raise SystemExit('安装失败（常见原因：需要管理员权限 / 签名证书未受信任）')
    print('\n完成：重启 Claude 即可看到中文界面。')


if __name__ == '__main__':
    main()
