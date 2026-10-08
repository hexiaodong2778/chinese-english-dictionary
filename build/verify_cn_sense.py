# -*- coding: utf-8 -*-
"""验证倒排索引：速度 + 准确性（与旧 LIKE 路径对比）。"""
import io, os, sys, time, sqlite3
sys.path.insert(0, r"D:\Dictionary\build")
os.chdir(r"D:\Dictionary")

out = []
con = sqlite3.connect(r"D:\Dictionary\dict.db", check_same_thread=False)
con.row_factory = sqlite3.Row
import app as A
eng = A.DictEngine(con, "en")

out.append("has_cn_sense = " + str(eng._has_cn_sense()))

out.append("\n===== 速度对比（新索引路径）=====")
for q in ["开心", "高兴", "快乐", "水", "狗", "跑", "吃", "环境",
          "漂亮", "勇敢", "a", "wo"]:
    t0 = time.time()
    r = eng.search_cn(q, limit=30)
    dt = (time.time() - t0) * 1000
    names = [x["word"] for x in (r or [])][:6]
    out.append(f"  {q:<8} {dt:7.1f} ms  n={len(r or []):3d}  {names}")

out.append("\n===== 旧的 LIKE 路径对比（强制回退）=====")
A.DictEngine._cn_sense_ok = False
for q in ["开心", "水", "狗"]:
    t0 = time.time()
    r = eng.search_cn(q, limit=30)
    dt = (time.time() - t0) * 1000
    names = [x["word"] for x in (r or [])][:6]
    out.append(f"  {q:<8} {dt:7.1f} ms  n={len(r or []):3d}  {names}")
A.DictEngine._cn_sense_ok = None

out.append("\n===== 准确性：核心词是否仍排第一 =====")
CASES = [
    ("狗", "dog"), ("猫", "cat"), ("书", "book"), ("水", "water"),
    ("学习", "study"), ("跑", "run"), ("电脑", "computer"),
    ("美丽", "beautiful"), ("环境", "environment"), ("放弃", "abandon"),
    ("高兴", "glad"), ("快乐", "happy"), ("愉快", "happy"),
    ("幸福", "happy"), ("喝", "drink"), ("吃", "eat"),
    ("笑", "laugh"), ("哭", "cry"), ("睡", "sleep"), ("买", "buy"),
    ("卖", "sell"), ("说", "say"), ("看", "look"), ("听", "listen"),
]
good = bad = 0
for q, want in CASES:
    r = eng.search_cn(q, limit=30)
    got = [x["word"] for x in (r or [])]
    hit = want in got
    rank = got.index(want) + 1 if hit else -1
    mark = "OK " if hit else "MISS"
    if hit: good += 1
    else: bad += 1
    out.append(f"  {mark} {q:<8} → {want:<14} rank={rank:<3} "
               f"top3={got[:3]}")

out.append(f"\n核心词命中 {good}/{good+bad}")

open(r"D:\Dictionary\build\_sense_verify.txt", "w", encoding="utf-8").write(
    "\n".join(out))
print("ok")
