# -*- coding: utf-8 -*-
"""直接检查已部署的 dict.db 里例句数据是否可见、可查。

用户说"例句呢"——先确认数据层面到不到位，
再确认程序层面渲染不渲染。
"""
import io
import os
import sqlite3
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

DB = r"D:\Dictionary\dict.db"
print(f"db = {DB}")
print(f"size = {os.path.getsize(DB):,} bytes")
import datetime
print(f"mtime = {datetime.datetime.fromtimestamp(os.path.getmtime(DB))}")

con = sqlite3.connect(DB)
con.row_factory = sqlite3.Row

tables = [r[0] for r in con.execute(
    "SELECT name FROM sqlite_master WHERE type='table'")]
print(f"\n表: {tables}")

for t in ("example", "ex_index"):
    if t in tables:
        n = con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        print(f"  {t}: {n:,} 行")
    else:
        print(f"  {t}: **不存在**")

print("\nmeta:")
for r in con.execute("SELECT k,v FROM meta"):
    print(f"  {r['k']} = {r['v']}")

print("\n=== dog 的例句 ===")
try:
    rs = con.execute(
        "SELECT e.en, e.zh FROM ex_index x JOIN example e ON e.id=x.ex_id "
        "WHERE x.word='dog' ORDER BY e.n_en LIMIT 6").fetchall()
    print(f"共 {len(rs)} 条")
    for r in rs:
        print(f"  {r['en']}")
        print(f"  {r['zh']}")
except Exception as e:
    print("查询失败:", e)

print("\n=== 用 program 里的 examples() 方法查 ===")
sys.path.insert(0, r"D:\Dictionary\build")
import app as A
eng = A.DictEngine(con, "en")
print(f"engine.examples('dog') -> {len(eng.examples('dog'))} 条")
print(f"engine.example_count() -> {eng.example_count():,}")
for en, zh in eng.examples("dog")[:3]:
    print(f"  {en}")
    print(f"  {zh}")

print("\n=== lookup 后拿到的词条里有没有例句 ===")
d = eng.lookup("dog", "simple")
print(f"lookup('dog') -> {'有' if d else '无'} 词条")
if d:
    print(f"  word = {d.get('word')}")
    print(f"  例句数 = {len(eng.examples(d.get('word')))}")
con.close()
