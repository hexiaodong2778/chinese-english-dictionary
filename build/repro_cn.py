"""复现「狗/猫」等最基础中文词查不到的问题。

检查 dict.db 里：
  1. 英文 dog 的词条是什么样（translation 里有没有「狗」）
  2. search_cn('狗') 的匹配逻辑为什么命中不了
"""
import sqlite3
import sys
import os

sys.path.insert(0, r"D:\Dictionary\build")

DB = r"D:\Dictionary\build\dict.db"
con = sqlite3.connect(DB)
con.row_factory = sqlite3.Row

print("=== 1. dog 词条 ===")
row = con.execute("SELECT * FROM dict WHERE lower='dog'").fetchone()
if row:
    for k in row.keys():
        v = row[k]
        if v not in (None, "", 0):
            print(f"  {k:14s} = {str(v)[:160]}")
else:
    print("  没找到 dog")

print("\n=== 2. translation 里含『狗』的词条（前 20）===")
rows = con.execute(
    "SELECT word, translation, tag FROM dict WHERE translation LIKE '%狗%' "
    "ORDER BY frq DESC LIMIT 20").fetchall()
for r in rows:
    t = (r["translation"] or "").replace("\n", " / ")
    print(f"  {r['word']:20s} | {t[:80]}")

print("\n=== 3. 词条总数 & 有 translation 的数量 ===")
tot = con.execute("SELECT COUNT(*) FROM dict").fetchone()[0]
wz = con.execute(
    "SELECT COUNT(*) FROM dict WHERE translation IS NOT NULL "
    "AND translation<>''").fetchone()[0]
print(f"  总 {tot:,}  有中文释义 {wz:,}")

print("\n=== 4. 精确以『狗』开头的释义 ===")
rows = con.execute(
    "SELECT word, translation FROM dict "
    "WHERE translation LIKE '狗%' OR translation LIKE 'n. 狗%' "
    "ORDER BY frq DESC LIMIT 15").fetchall()
for r in rows:
    t = (r["translation"] or "").replace("\n", " / ")
    print(f"  {r['word']:20s} | {t[:80]}")

con.close()
