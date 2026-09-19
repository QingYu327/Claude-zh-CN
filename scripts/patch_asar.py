#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Custom ASAR repacker for Claude Desktop (Claude_2.2553.1.x).
Header layout: [0:4] magic(04 00 00 00) + 3x uint32 LE = (L+8, L+4, L)
               where L = JSON header length; file bytes start at offset 16+L.
Unpacked files (".exe/.dll/.node" etc.) carry "unpacked":true and their bytes
live in app.asar.unpacked -> we keep their header entries and write NO bytes.
In-asar files get sequential offsets; integrity SHA256 recomputed for the
modified file only (others unchanged -> hashes stay valid).
"""
import sys, os, json, hashlib

TARGETS = [
    '.vite/build/mainView.js',          # 主聊天视图 (Ri.CLAUDE_AI_WEB) 的 preload —— 真正的注入点
    '.vite/build/claudePagePreview.js', # 预览标签页的 preload —— 顺带覆盖
]

def load_header(a):
    magic = a[:4]
    u0 = int.from_bytes(a[4:8], 'little')
    u1 = int.from_bytes(a[8:12], 'little')
    u2 = int.from_bytes(a[12:16], 'little')
    L = u2
    assert u0 == L + 8 and u1 == L + 4, "header-size relationship mismatch: %d/%d/%d" % (u0, u1, L)
    header = json.loads(a[16:16 + L].decode('utf-8'))
    base = 16 + L
    return magic, L, header, base

def collect(node, path, acc):
    for name, info in node.items():
        p = (path + '/' + name).lstrip('/')
        if 'files' in info:
            collect(info['files'], p, acc)
        else:
            acc.append((p, info))

def sha256_hex(b):
    return hashlib.sha256(b).hexdigest()

def patch(in_path, preload_path, out_path):
    a = open(in_path, 'rb').read()
    magic, L, header, base = load_header(a)
    preload = open(preload_path, 'rb').read()

    acc = []
    collect(header['files'], '', acc)

    new_offset = 0
    file_bytes = {}
    modified = 0
    ref_ok = None
    for (p, info) in acc:
        if info.get('unpacked') is True:
            continue  # external bytes, keep entry as-is
        off = int(info['offset'])
        sz = int(info['size'])
        data = a[base + off: base + off + sz]
        assert len(data) == sz, "size mismatch for %s: got %d want %d" % (p, len(data), sz)
        if p in TARGETS:
            data = data + b'\n' + preload
            h = sha256_hex(data)
            info['size'] = len(data)
            info['integrity'] = {'algorithm': 'SHA256', 'hash': h,
                                 'blockSize': 4194304, 'blocks': [h]}
            info['offset'] = str(new_offset)
            file_bytes[p] = data
            new_offset += len(data)
            modified += 1
        else:
            # reference check on first small in-asar file to validate extraction
            if ref_ok is None and sz < 5000:
                ref_ok = (sha256_hex(data) == info['integrity']['hash'])
            info['offset'] = str(new_offset)
            file_bytes[p] = data
            new_offset += len(data)

    assert modified == len(TARGETS), "targets not found: modified %d of %d" % (modified, len(TARGETS))
    assert ref_ok is True, "REFERENCE HASH MISMATCH -> extraction logic wrong, aborting"

    new_json = json.dumps(header, separators=(',', ':'), ensure_ascii=False)
    new_L = len(new_json.encode('utf-8'))
    out = bytearray()
    out += magic
    out += (new_L + 8).to_bytes(4, 'little')
    out += (new_L + 4).to_bytes(4, 'little')
    out += new_L.to_bytes(4, 'little')
    out += new_json.encode('utf-8')
    for (p, info) in acc:
        if info.get('unpacked') is True:
            continue
        out += file_bytes[p]

    open(out_path, 'wb').write(out)
    # verify
    b = open(out_path, 'rb').read()
    m2, L2, h2, base2 = load_header(b)
    assert m2 == magic
    acc2 = []
    collect(h2['files'], '', acc2)
    cnt = 0
    for (p, info) in acc2:
        if info.get('unpacked') is True:
            continue
        off = int(info['offset']); sz = int(info['size'])
        d = b[base2 + off: base2 + off + sz]
        assert len(d) == sz
        if p in TARGETS:
            assert sha256_hex(d) == info['integrity']['hash']
            assert d.endswith(preload)
        cnt += 1
    print("OK wrote %s (%d bytes, %d in-asar files, target patched)" % (out_path, len(b), cnt))
    print("reference-hash-check:", ref_ok)

if __name__ == '__main__':
    if len(sys.argv) != 4:
        print("usage: patch_asar.py <in.asar> <preload.js> <out.asar>")
        sys.exit(2)
    patch(sys.argv[1], sys.argv[2], sys.argv[3])
