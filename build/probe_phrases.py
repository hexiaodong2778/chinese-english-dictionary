# -*- coding: utf-8 -*-
"""调研：短语数据能从哪里来？

需求：在单词词条里展示该词的常用短语（如 give 的 give up / give in）。

候选来源：
  1. ECDICT 自身有没有短语数据
  2. dict 表里本身就收录了大量多词词条（如 "give up"）—— 可以反过来用：
     对单词 w，找出所有「以 w 开头/包含 w」的多词词条，就是它的短语！
  3. 例句语料里挖 n-gram 搭配
"""
import io
import os
import sqlite3
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

con = sqlite3.connect(r"D:\Dictionary\dict.db")
con.row_factory = sqlite3.Row

print("=" * 72)
print("① 词库里有多少「多词词条」")
print("=" * 72)
n_all = con.execute("SELECT COUNT(*) FROM dict").fetchone()[0]
n_phrase = con.execute(
    "SELECT COUNT(*) FROM dict WHERE word LIKE '% %'").fetchone()[0]
n_hyph = con.execute(
    "SELECT COUNT(*) FROM dict WHERE word LIKE '%-%'").fetchone()[0]
print(f"  总词条 {n_all:,}")
print(f"  含空格的多词条目 {n_phrase:,} ({n_phrase/n_all*100:.1f}%)")
print(f"  含连字符的条目   {n_hyph:,}")

print("\n  多词条目样例：")
for r in con.execute(
        "SELECT word, translation FROM dict WHERE word LIKE '% %' "
        "AND translation!='' ORDER BY bnc LIMIT 12"):
    print(f"    {r['word']:26} {(r['translation'] or '')[:52]}")

print()
print("=" * 72)
print("② 用「前缀匹配」挖某词的短语")
print("=" * 72)
for w in ("give", "look", "take", "get", "put", "come", "turn"):
    rows = con.execute(
        "SELECT word, translation FROM dict "
        "WHERE word LIKE ? AND word LIKE '% %' "
        "ORDER BY CASE WHEN bnc>0 THEN bnc ELSE 999999 END LIMIT 12",
        (w + " %",)).fetchall()
    print(f"\n  [{w}] 以 {w} 开头的多词条目: {len(rows)} 条")
    for r in rows[:8]:
        print(f"      {r['word']:28} {(r['translation'] or '')[:46]}")

print()
print("=" * 72)
print("③ 用「首词匹配」找短语（更准）")
print("=" * 72)
# 短语的第一个词 = 目标词
for w in ("give", "look", "take"):
    rows = con.execute(
        "SELECT word, translation, collins, oxford, bnc FROM dict "
        "WHERE lower LIKE ? AND word LIKE '% %' AND translation!='' "
        "ORDER BY CASE WHEN bnc>0 THEN bnc ELSE 999999 END LIMIT 15",
        (w + " %",)).fetchall()
    print(f"\n  [{w}] 共 {len(rows)} 条")
    for r in rows[:10]:
        stars = "★" * (r["collins"] or 0)
        ox = "牛津" if r["oxford"] else ""
        print(f"      {r['word']:26} {(r['translation'] or '')[:40]:42} {stars}{ox}")

print()
print("=" * 72)
print("④ 短语的释义质量抽样")
print("=" * 72)
for probe in ("give up", "look after", "take off", "come across",
              "put up with", "turn out"):
    r = con.execute("SELECT word,translation,tag,collins,oxford "
                    "FROM dict WHERE lower=?", (probe,)).fetchone()
    if r:
        print(f"  {r['word']:16} | {(r['translation'] or '')[:60]}")
        print(f"  {'':16} | tag={r['tag']!r} collins={r['collins']} "
              f"oxford={r['oxford']}")
    else:
        print(f"  {probe:16} | **词库中没有**")

con.close()
