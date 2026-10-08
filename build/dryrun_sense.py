# -*- coding: utf-8 -*-
"""dry-run：检查义项拆分质量，确认落库前无灾难。"""
import io, sqlite3, sys, random
sys.path.insert(0, r"D:\Dictionary\build")
from build_cn_sense import split_senses

out = []
con = sqlite3.connect(r"D:\Dictionary\dict.db")
con.row_factory = sqlite3.Row
cur = con.cursor()

out.append("===== 1. 关注词的拆分结果 =====")
for w in ["happy", "glad", "joy", "water", "dog", "run", "environment",
          "chuffed", "delight", "merry"]:
    r = cur.execute("SELECT word, zh FROM cn_index WHERE lower=? LIMIT 1",
                    (w,)).fetchone()
    if r:
        out.append(f"  {w:<12} zh={r['zh'][:60]}")
        out.append(f"    -> {split_senses(r['zh'])}")
    else:
        out.append(f"  {w}: (无)")

out.append("\n===== 2. 随机抽样 15 条看有没有垃圾 =====")
rows = cur.execute(
    "SELECT word, zh FROM cn_index WHERE zh IS NOT NULL AND zh<>'' "
    "ORDER BY RANDOM() LIMIT 15").fetchall()
for r in rows:
    ss = split_senses(r["zh"])
    out.append(f"  {r['word'][:18]:<18} | {r['zh'][:52]}")
    out.append(f"      -> {ss}")

out.append("\n===== 3. 统计：每条的义项数分布 =====")
dist = {}
empty = 0
total = 0
for r in cur.execute("SELECT zh FROM cn_index"):
    ss = split_senses(r["zh"])
    total += 1
    n = len(ss)
    if n == 0:
        empty += 1
    dist[n] = dist.get(n, 0) + 1
out.append(f"  总条数 {total:,}，拆不出义项 {empty:,} 条 "
           f"({empty/max(total,1)*100:.2f}%)")
for k in sorted(dist)[:12]:
    out.append(f"    {k:2d} 个义项: {dist[k]:,}")

out.append("\n===== 4. 关键义项是否覆盖 =====")
KEY = ["开心", "高兴", "快乐", "愉快", "幸福", "难过", "生气", "害怕",
       "漂亮", "聪明", "勇敢", "水", "狗", "书", "跑", "吃"]
for k in KEY:
    # 用临时表算：有多少词的义项里精确含有 k
    cnt = 0
    for r in cur.execute("SELECT zh FROM cn_index WHERE zh LIKE ? LIMIT 400",
                         (f"%{k}%",)):
        if k in split_senses(r["zh"]):
            cnt += 1
    out.append(f"  {k:<8} 精确义项命中(前400候选内) {cnt:4d}")

open(r"D:\Dictionary\build\_sense_dryrun.txt", "w", encoding="utf-8").write(
    "\n".join(out))
print("ok")
