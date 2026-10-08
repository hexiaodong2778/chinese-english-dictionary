"""无界面测试词典引擎逻辑。"""
import sys, os, io
sys.path.insert(0, r"D:\Dictionary\build")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import app as A

con = A.open_db("dict.db")
assert con is not None, "dict.db 打不开"
eng = A.DictEngine(con)

print("=== 词表统计 ===")
s = eng.stats()
for k in ["total", "gk", "zk", "cet4", "cet6", "ky", "toefl", "ielts", "gre", "oxford"]:
    print(f"  {k:8s} = {s.get(k,0):,}")

print("\n=== 高考词典过滤（关键修复点）===")
for w in ["achieve", "beautiful", "computer", "abandon", "photosynthesis"]:
    d = eng.lookup(w, "gk")
    if d:
        print(f"  {w:16s} tag={d.get('tag','')!r:40s} note={d.get('_note','-')}")
    else:
        print(f"  {w:16s} NOT FOUND")

print("\n=== 变形还原 ===")
for w in ["went", "apples", "taken", "teeth", "studies", "running"]:
    d = eng.lookup(w, "all")
    if d:
        print(f"  {w:12s} -> {d.get('word'):14s} (from {d.get('_from')})")
    else:
        print(f"  {w:12s} -> NOT FOUND")

print("\n=== 候选建议 ===")
for p in ["app", "beaut", "go"]:
    rows = eng.suggest(p, 5, "gk")
    print(f"  [{p}] -> {[r['word'] for r in rows]}")

print("\n=== 中译英 ===")
for kw in ["放弃", "美丽", "环境", "学习"]:
    rows = eng.search_cn(kw, 5)
    print(f"  [{kw}] -> {[(r['word'], r['zh'][:16]) for r in rows]}")

print("\n=== 音标英美对比 ===")
for w in ["go", "hot", "water", "teacher", "student"]:
    d = eng.lookup(w, "all")
    if d:
        print(f"  {w:10s} UK=/{d.get('phonetic','')}/  US=/{d.get('phonetic_us','')}/")

print("\nALL ENGINE TESTS DONE")
con.close()
