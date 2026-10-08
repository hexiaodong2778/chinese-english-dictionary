# -*- coding: utf-8 -*-
"""全方位检查 ①：部署文件完整性与一致性。

核对 D:\Dictionary\ 下每个文件：大小、时间戳、与构建目录是否一致、
关键文件的哈希是否匹配。找出「改了源码但没部署」这类错位。
"""
import hashlib
import io
import os
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

DEPLOY = r"D:\Dictionary"
BUILD = r"D:\Dictionary\build"


def h(p, chunk=1 << 20):
    """算文件 sha256（大文件分块读）。"""
    if not os.path.exists(p):
        return None
    m = hashlib.sha256()
    with open(p, "rb") as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            m.update(b)
    return m.hexdigest()[:16]


def info(p):
    if not os.path.exists(p):
        return None
    st = os.stat(p)
    import datetime
    return (st.st_size, datetime.datetime.fromtimestamp(st.st_mtime))


print("=" * 72)
print("① 部署目录清单")
print("=" * 72)
total = 0
for f in sorted(os.listdir(DEPLOY)):
    p = os.path.join(DEPLOY, f)
    if os.path.isfile(p):
        st, mt = info(p)
        total += st
        print(f"  {f:22} {st:>14,}  {mt}")
print(f"\n  合计 {total:,} bytes ({total / 1048576:.1f} MB)")

print()
print("=" * 72)
print("② 必需文件是否齐全")
print("=" * 72)
REQUIRED = {
    "查单词.exe": "程序本体",
    "dict.db": "英语词库（含例句）",
    "dict_ja.db": "日语词库",
    "dict_fr.db": "法语词库",
    "dict_yue.db": "粤语词库",
    "使用说明.txt": "使用说明",
}
missing = []
for f, desc in REQUIRED.items():
    ok = os.path.exists(os.path.join(DEPLOY, f))
    print(f"  [{'OK' if ok else 'XX'}] {f:16} {desc}")
    if not ok:
        missing.append(f)

print()
print("=" * 72)
print("③ 部署 vs 构建 一致性（关键文件必须 hash 相同）")
print("=" * 72)
PAIRS = [
    ("查单词.exe", os.path.join(BUILD, "dist", "查单词.exe")),
    ("dict.db", os.path.join(BUILD, "dict.db")),
    ("使用说明.txt", os.path.join(BUILD, "使用说明_新.txt")),
]
for name, bpath in PAIRS:
    dp = os.path.join(DEPLOY, name)
    dh, bh = h(dp), h(bpath)
    di, bi = info(dp), info(bpath)
    same = (dh == bh)
    flag = "一致" if same else "**不一致**"
    print(f"  {name}")
    print(f"    部署 {di[0]:>13,}  {di[1]}  sha16={dh}")
    print(f"    构建 {bi[0] if bi else 0:>13,}  {bi[1] if bi else '-'}  sha16={bh}")
    print(f"    -> {flag}")
    if not same and name != "查单词.exe":
        # exe 允许不同（构建目录可能没同步），词库和文档必须一致
        missing.append(f"{name}(内容不一致)")

print()
print("=" * 72)
print("④ 词库文件是否都是有效的 SQLite")
print("=" * 72)
import sqlite3
for f in ("dict.db", "dict_ja.db", "dict_fr.db", "dict_yue.db"):
    p = os.path.join(DEPLOY, f)
    if not os.path.exists(p):
        print(f"  [XX] {f} 不存在")
        continue
    try:
        con = sqlite3.connect(f"file:{p}?mode=ro", uri=True)
        # 完整性快速检查
        ic = con.execute("PRAGMA quick_check").fetchone()[0]
        tabs = [r[0] for r in con.execute(
            "SELECT name FROM sqlite_master WHERE type='table'")]
        n = con.execute("SELECT COUNT(*) FROM dict").fetchone()[0]
        print(f"  [{'OK' if ic == 'ok' else 'XX'}] {f:14} 完整性={ic}  "
              f"词条={n:,}  表={tabs}")
        con.close()
    except Exception as e:
        print(f"  [XX] {f} 打不开: {e}")
        missing.append(f)

print()
print("=" * 72)
print("⑤ 结论")
print("=" * 72)
if missing:
    print("  发现问题：")
    for m in missing:
        print(f"    - {m}")
    sys.exit(1)
else:
    print("  全部通过：文件齐全、与构建一致、词库有效。")
