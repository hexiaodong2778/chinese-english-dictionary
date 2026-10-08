# -*- coding: utf-8 -*-
"""查清 dict.db 里所有表、所有列、以及每列的真实内容。"""
import sys, io, sqlite3
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

con = sqlite3.connect(r"D:\Dictionary\build\dict.db")
con.row_factory = sqlite3.Row

print("=== 所有表与行数 ===")
tabs = [r[0] for r in con.execute(
    "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
for t in tabs:
    n = con.execute(f"SELECT COUNT(*) FROM [{t}]").fetchone()[0]
    print(f"  {t:<16} {n:>10,} 行")

print("\n=== 每张表的列定义 ===")
for t in tabs:
    cols = [r[1] for r in con.execute(f"PRAGMA table_info([{t}])")]
    print(f"\n[{t}]  {cols}")

# 深入 dict 表每个字段
print("\n=== dict 表：每列非空率与样本（抽 20000 行） ===")
cols = [r[1] for r in con.execute("PRAGMA table_info(dict)")]
rows = con.execute("SELECT * FROM dict LIMIT 20000").fetchall()
from collections import Counter
ne = Counter()
samp = {}
for r in rows:
    for c in cols:
        v = r[c]
        if v not in (None, ""):
            ne[c] += 1
            if c not in samp:
                samp[c] = v
for c in cols:
    n = ne[c]
    pct = n * 100.0 / max(1, len(rows))
    s = str(samp.get(c, ""))[:160].replace("\n", " | ")
    print(f"  {c:<16} {pct:5.1f}%   {s!r}")

# sentence 字段专门看
print("\n=== 专门检查可能含例句的字段 ===")
for c in cols:
    if any(k in c.lower() for k in ("sent", "example", "eg", "sample", "usage")):
        print(f"  发现疑似例句列: {c}")
        for r in con.execute(f"SELECT word,[{c}] FROM dict WHERE [{c}] IS NOT NULL AND [{c}]!='' LIMIT 5"):
            print(f"     {r[0]}: {str(r[1])[:250]}")
print("  （以上若为空，说明该字段不存在或无数据）")
