# -*- coding: utf-8 -*-
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

P = r"D:\Dictionary\build\anki_cmn\cmn.txt"
rows = []
with open(P, "r", encoding="utf-8", errors="replace") as f:
    for line in f:
        line = line.rstrip("\n")
        if not line.strip():
            continue
        parts = line.split("\t")
        rows.append(parts)

print(f"总行数: {len(rows):,}")
print(f"列数分布: {sorted(set(len(r) for r in rows))}")
print("\n=== 前 8 行 ===")
for r in rows[:8]:
    print("  ", r)

print("\n=== 随机 15 行 ===")
import random
random.seed(42)
for r in random.sample(rows, 15):
    en = r[0] if len(r) > 0 else ""
    zh = r[1] if len(r) > 1 else ""
    print(f"  EN: {en}")
    print(f"  ZH: {zh}")
    print()

# 看常用词的句子有多少
print("=== 常用词在例句里出现次数（作为单词，不区分大小写）===")
import re
from collections import Counter
cnt = Counter()
WORDS = ["dog", "water", "book", "study", "beautiful", "computer", "money",
         "eat", "drink", "sleep", "open", "close", "begin", "friend",
         "environment", "abandon", "time", "house", "car", "student"]
for r in rows:
    if len(r) < 2:
        continue
    en = " " + re.sub(r"[^A-Za-z' ]", " ", r[0]).lower() + " "
    for w in WORDS:
        if f" {w} " in en or f" {w}s " in en or f" {w}ed " in en or f" {w}ing " in en:
            cnt[w] += 1
for w in WORDS:
    print(f"   {w:<14} {cnt[w]:>5}")

# 长度分布
lens = [len(r[0]) for r in rows if len(r) > 0]
lens.sort()
print(f"\n英文句长: 最短={lens[0]} 中位={lens[len(lens)//2]} 最长={lens[-1]}")
