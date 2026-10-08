# -*- coding: utf-8 -*-
import sys, os, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, r"D:\Dictionary\build")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtWidgets import QApplication
app = QApplication(sys.argv)
import app as A

w = A.MainWindow()
con = w.engine.con

# 钱 / money 在库里什么样
for word in ["money", "begin", "start"]:
    r = con.execute("SELECT word,translation,frq,collins,oxford FROM dict "
                    "WHERE lower=? LIMIT 1", (word,)).fetchone()
    if r:
        print(f"{word}: frq={r['frq']} col={r['collins']} ox={r['oxford']}")
        print(f"   senses={A.DictEngine.split_senses(r['translation'])}")
    else:
        print(f"{word}: 不在 dict")
    c = con.execute("SELECT word,zh FROM cn_index WHERE lower=?", (word,)).fetchone()
    print(f"   cn_index: {c['zh'] if c else '无'}")
    print()

print("=== cn_index 中含『钱』且 collins>=4 的词 ===")
for r in con.execute(
        "SELECT c.word, c.zh, d.frq, d.collins, d.oxford FROM cn_index c "
        "JOIN dict d ON d.lower=c.lower WHERE c.zh LIKE '%钱%' "
        "AND d.collins>=4 ORDER BY d.collins DESC, d.frq ASC LIMIT 15"):
    print(f"   {r['word']:<14} col={r['collins']} frq={r['frq']:<7} {r['zh'][:50]}")

print()
print("=== 直接用 search_cn 取到的 pocket / money 得分 ===")
E = A.DictEngine
for i, r in enumerate(w.engine.search_cn("钱", limit=20)):
    if r["word"].lower() in ("pocket", "money"):
        s = E.split_senses(r["zh"])
        sc = E._sense_score(s, "钱")
        sr = E._sense_rank(s, "钱")
        print(f"  {i+1}. {r['word']:<10} sc={sc} rank={sr} frq={r['frq']} "
              f"col={r['collins']} ox={r['oxford']} senses={s[:6]}")
