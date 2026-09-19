# -*- coding: utf-8 -*-
"""Claude Desktop 前端（ion-dist）汉化补丁。

四层汉化的第 1~3 层：
  1) 桌面壳语言包      resources/zh-CN.json（+ en-US.json 双保险）
  2) 前端 i18n 语言包  ion-dist/i18n/{zh-Hans.json, zh-CN.json}（双命名）+ dynamic/ 同名
  3) 硬编码文案        zh-hans-patch.js 注入 index.html（运行时按对照表替换）
另有第 4 层（主视图 preload）在 build_and_install.py 里对 app.asar 注入。

为什么语言包要"双命名"：
  桌面壳的语言协商（tnt()）在不同模式下会得到 zh-CN 或 zh-Hans，
  前端按该名字去取 /i18n/<name>.json；只放一种时另一种名字会 404 → 界面回落英文。
  （网关/3P 模式实测就是 zh-CN，因此必须双命名。）
"""
import os, re, json, shutil

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PAYLOAD = os.path.join(ROOT, '语言包')

PATCH_JS_TEMPLATE = """(function () {
  if (window.__claudeZhHansPatch) return;
  window.__claudeZhHansPatch = true;
  var MAP = __MAP__;
  function trText(node) {
    var s = node.nodeValue; if (!s) return;
    var t = s.trim(); if (!t) return;
    var r = MAP[t]; if (r === undefined) return;
    node.nodeValue = s.replace(t, r);
  }
  function trAttrs(el) {
    if (!el || el.nodeType !== 1) return;
    var attrs = ['placeholder', 'title', 'aria-label'];
    for (var i = 0; i < attrs.length; i++) {
      var v = el.getAttribute && el.getAttribute(attrs[i]);
      if (v && MAP[v.trim()] !== undefined) el.setAttribute(attrs[i], MAP[v.trim()]);
    }
  }
  function walk(root) {
    if (!root) return;
    trAttrs(root);
    if (root.querySelectorAll) {
      var els = root.querySelectorAll('[placeholder],[title],[aria-label]');
      for (var i = 0; i < els.length; i++) trAttrs(els[i]);
    }
    var w = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, null, false);
    var n; while ((n = w.nextNode())) trText(n);
  }
  function boot() {
    walk(document.body);
    try {
      new MutationObserver(function (ms) {
        for (var i = 0; i < ms.length; i++) {
          var m = ms[i];
          if (m.type === 'characterData') { trText(m.target); continue; }
          var a = m.addedNodes; if (!a) continue;
          for (var j = 0; j < a.length; j++) {
            if (a[j].nodeType === 1) walk(a[j]);
            else if (a[j].nodeType === 3) trText(a[j]);
          }
        }
      }).observe(document.body, { childList: true, subtree: true, characterData: true });
    } catch (e) { }
    setTimeout(function () { walk(document.body); }, 1500);
    setTimeout(function () { walk(document.body); }, 4000);
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot);
  else boot();
})();
"""


def copy(src, dst, label):
    if not os.path.isfile(src):
        print('    [warn] payload 缺失:', src)
        return False
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copyfile(src, dst)
    print('    ok:', label)
    return True


def patch(unpacked_root):
    res = os.path.join(unpacked_root, 'app', 'resources')
    ion = os.path.join(res, 'ion-dist')
    assert os.path.isdir(ion), '解包目录里找不到 ion-dist'

    shell_zh = os.path.join(PAYLOAD, 'zh-CN.json')
    fe_zh = os.path.join(PAYLOAD, 'ion-dist-i18n-zh-Hans.json')
    fe_dyn = os.path.join(PAYLOAD, 'ion-dist-i18n-dynamic-zh-CN.json')

    # 1) 桌面壳
    copy(shell_zh, os.path.join(res, 'zh-CN.json'), '桌面壳 zh-CN.json')
    copy(shell_zh, os.path.join(res, 'en-US.json'), '桌面壳 en-US.json（双保险）')
    copy(shell_zh, os.path.join(res, 'i18n', 'zh-CN.json'), '桌面壳 resources/i18n/zh-CN.json')
    copy(shell_zh, os.path.join(res, 'i18n', 'zh-Hans.json'), '桌面壳 resources/i18n/zh-Hans.json')

    # 2) 前端 i18n（双命名）
    for name in ('zh-Hans.json', 'zh-CN.json'):
        copy(fe_zh, os.path.join(ion, 'i18n', name), '前端 i18n/' + name)
        copy(fe_dyn, os.path.join(ion, 'i18n', 'dynamic', name), '前端 i18n/dynamic/' + name)
    copy(fe_zh, os.path.join(ion, 'i18n', 'en-US.json'), '前端 en-US.json（双保险）')
    for name in ('zh-Hans.overrides.json', 'zh-CN.overrides.json'):
        p = os.path.join(ion, 'i18n', name)
        if os.path.isfile(p):
            os.remove(p)
            print('    已删除可能遮蔽翻译的 overrides:', name)

    # 3a) 语言白名单 Am（zh-Hans / zh-CN 都放进去）
    v1 = os.path.join(ion, 'assets', 'v1')
    patched = 0
    for fn in sorted(os.listdir(v1)):
        if patched >= 2:
            break
        if not fn.endswith('.js'):
            continue
        fp = os.path.join(v1, fn)
        if os.path.getsize(fp) < 8000:
            continue
        with open(fp, 'r', encoding='utf-8', errors='strict') as f:
            c = f.read()
        if 'var Am=["en-US","de-DE"' in c:
            c2, n = re.subn(
                r'var Am=\["en-US","de-DE"[^\]]*\]',
                'var Am=["en-US","de-DE","fr-FR","ko-KR","ja-JP","es-419","es-ES","it-IT",'
                '"hi-IN","pt-BR","id-ID","zh-Hans","zh-CN"]',
                c, count=1)
            assert n == 1, '白名单正则未命中：' + fn
            with open(fp, 'w', encoding='utf-8', newline='') as f:
                f.write(c2)
            patched += 1
            print('    ok: 语言白名单加入 zh-Hans/zh-CN ->', fn)
    assert patched >= 1, '未找到前端语言白名单（应用版本可能变化）'

    # 3b) 运行时替换脚本 + index.html 注入
    with open(os.path.join(PAYLOAD, 'zh-hans-dom-map.json'), 'r', encoding='utf-8-sig') as f:
        dom_map = json.load(f)
    js = PATCH_JS_TEMPLATE.replace('__MAP__', json.dumps(dom_map, ensure_ascii=False, separators=(',', ':')))
    with open(os.path.join(ion, 'zh-hans-patch.js'), 'w', encoding='utf-8', newline='') as f:
        f.write(js)
    print('    ok: zh-hans-patch.js 生成（%d 条对照）' % len(dom_map))

    idx = os.path.join(ion, 'index.html')
    with open(idx, 'r', encoding='utf-8') as f:
        ih = f.read()
    tag = '<script defer src="/zh-hans-patch.js"></script>'
    if 'zh-hans-patch.js' not in ih:
        ih = ih.replace('</head>', tag + '\n</head>', 1) if '</head>' in ih else tag + '\n' + ih
        with open(idx, 'w', encoding='utf-8', newline='') as f:
            f.write(ih)
        print('    ok: index.html 已注入替换脚本')
    else:
        print('    ok: index.html 已包含替换脚本')

    return {'whitelist': patched, 'map_entries': len(dom_map)}


if __name__ == '__main__':
    import sys
    print(patch(sys.argv[1]))
