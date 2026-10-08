import sys, os
sys.path.insert(0, r"D:\Dictionary\build")
import app as A

print("=== LANG_DEFS ===")
for i, (k, v) in enumerate(A.LANG_DEFS.items()):
    p = os.path.join(r"D:\Dictionary\build", v["db"])
    print(f"  [{i}] {k:4s} {v['label']:4s} {v['db']:14s} exists={os.path.exists(p)} size={os.path.getsize(p)//1024 if os.path.exists(p) else 0}KB")

print("\n=== 逐语言打开与查询 ===")
for k, v in A.LANG_DEFS.items():
    con = A.open_db(v["db"])
    if not con:
        print(f"  {k}: 打不开 {v['db']}")
        continue
    eng = A.DictEngine(con)
    n = eng.stats().get("total", 0)
    print(f"  {k:4s} {v['label']:4s} kind={eng.kind:6s} total={n:,}")
    con.close()

print("\n=== 粤语库抽查 ===")
con = A.open_db("dict_yue.db")
eng = A.DictEngine(con)
for probe in ["nei", "ngo", "lei"]:
    rows = eng.suggest(probe, 5)
    print(f"  [{probe}] -> {[r['word'] for r in rows]}")
d = eng.lookup("nei", "all")
print("  lookup nei:", d)
con.close()

print("\n=== 日语库抽查 ===")
con = A.open_db("dict_ja.db")
eng = A.DictEngine(con)
for probe in ["gak", "nihon", "tab"]:
    rows = eng.suggest(probe, 5)
    print(f"  [{probe}] -> {[(r['word'], r['phonetic']) for r in rows]}")
con.close()

print("\n=== 法语库抽查 ===")
con = A.open_db("dict_fr.db")
eng = A.DictEngine(con)
for probe in ["bonj", "merc", "chat"]:
    rows = eng.suggest(probe, 5)
    print(f"  [{probe}] -> {[(r['word'], r['phonetic']) for r in rows]}")
con.close()
