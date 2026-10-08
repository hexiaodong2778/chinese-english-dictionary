"""测试改造后的 search_cn：中文反查是否能把核心词排到第一。"""
import sys
sys.path.insert(0, r"D:\Dictionary\build")
import app as A

con = A.open_db("dict.db")
eng = A.DictEngine(con, "en")

cases = [
    ("狗", "dog"),
    ("猫", "cat"),
    ("书", "book"),
    ("水", "water"),
    ("学习", "study"),
    ("跑", "run"),
    ("电脑", "computer"),
    ("美丽", "beautiful"),
    ("美丽", "fairness"),   # 也接受
    ("朋友", "friend"),
    ("吃", "eat"),
    ("爱", "love"),
    ("说话", "speak"),
    ("医生", "doctor"),
    ("孩子", "child"),
]

print("查询词   期望首选      实际前 5 结果")
print("-" * 78)
ok = 0
for kw, expect in cases:
    rows = eng.search_cn(kw, 8)
    words = [r["word"] for r in rows]
    hit = expect in words
    first = words[0] if words else "-"
    if first == expect or (hit and first == expect):
        ok += 1
        mark = "OK "
    elif hit:
        mark = "~  "
    else:
        mark = "XX "
    print(f"{mark}{kw:6s} 期望={expect:12s} 实际={words[:5]}")

print("-" * 78)
print(f"首选即正确: {ok} / {len(cases)}")

print("\n=== 「狗」的完整前 10 结果 ===")
for r in eng.search_cn("狗", 10):
    print(f"  {r['word']:18s} frq={r['frq'] or 0:6d} | {r['zh'][:46]}")

print("\n=== 「美丽」的完整前 10 结果 ===")
for r in eng.search_cn("美丽", 10):
    print(f"  {r['word']:18s} frq={r['frq'] or 0:6d} | {r['zh'][:46]}")

con.close()
