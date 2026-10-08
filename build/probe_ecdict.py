# -*- coding: utf-8 -*-
"""彻底查清 ECDICT 原始数据里到底有哪些字段、有没有例句。"""
import sys, io, csv, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

CSV = r"D:\Dictionary\build\ecdict.csv"
print("存在:", os.path.exists(CSV), " 大小:", os.path.getsize(CSV))

with open(CSV, "r", encoding="utf-8", errors="replace") as f:
    rd = csv.DictReader(f)
    cols = rd.fieldnames
    print("\n=== 全部列名 ===")
    for i, c in enumerate(cols):
        print(f"  {i:2d}. {c}")

    # 统计每列的非空率 + 抽样
    from collections import Counter, defaultdict
    nonempty = Counter()
    samples = defaultdict(list)
    n = 0
    for row in rd:
        n += 1
        for c in cols:
            v = (row.get(c) or "").strip()
            if v:
                nonempty[c] += 1
                if len(samples[c]) < 3:
                    samples[c].append(v[:200])
    print(f"\n=== 总行数 {n:,} ===")
    print("\n=== 各列非空率与样本 ===")
    for c in cols:
        pct = nonempty[c] * 100.0 / n if n else 0
        print(f"\n[{c}]  非空 {nonempty[c]:,} ({pct:.1f}%)")
        for s in samples[c]:
            print(f"    {s!r}")
