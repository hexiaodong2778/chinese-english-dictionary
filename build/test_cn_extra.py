# -*- coding: utf-8 -*-
"""验证联网补义项：开心 → happy 系列能排到前面"""
import sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, r"D:\Dictionary\build")
import app as A

con = A.open_db(A.LANG_DEFS["en"]["db"])
eng = A.DictEngine(con, "en")

print("=== 纯离线（无补充）===")
for kw in ["开心", "高兴", "快乐"]:
    r = eng.search_cn(kw)
    print(f"  {kw}: " + "  ".join(x["word"] for x in r[:6]))

print("\n=== 注入联网补充后 ===")
for kw in ["开心", "高兴", "快乐", "水", "电脑"]:
    items = A.fetch_cn_en(kw)
    A.DictEngine.set_cn_extra(kw, items)
    print(f"\n  「{kw}」联网给出: {items}")
    # 清缓存强制重算
    eng._cache.clear(); eng._cache_order.clear()
    r = eng.search_cn(kw)
    top = [(x["word"], (x.get("zh") or "")[:22]) for x in r[:6]]
    for w, zh in top:
        print(f"     {w:26s} {zh}")

print("\n=== 补充词是否确实排在最前 ===")
A.DictEngine.set_cn_extra("开心", A.fetch_cn_en("开心"))
eng._cache.clear(); eng._cache_order.clear()
r = eng.search_cn("开心")
words = [x["word"].lower() for x in r[:8]]
print("  前 8:", words)
hit = [w for w in words if "happy" in w or "delight" in w or "joyful" in w
       or "rejoice" in w or "glad" in w]
print(f"  含 happy/delight/joyful 系: {hit}")
print("  extra 路径已启用:", eng._cn_extra_used)

print("\n=== 单汉字不受影响（不能因补充而回归）===")
for kw in ["水", "狗", "书", "买", "哭"]:
    eng._cache.clear(); eng._cache_order.clear()
    r = eng.search_cn(kw)
    print(f"  {kw}: {[x['word'] for x in r[:3]]}  extra={eng._cn_extra_used}")
con.close()
