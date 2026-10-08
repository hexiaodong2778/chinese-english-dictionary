# -*- coding: utf-8 -*-
import sys, os, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, r"D:\Dictionary\build")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtWidgets import QApplication
app = QApplication(sys.argv)
import app as A
E = A.DictEngine
w = A.MainWindow()

for kw in ["环境", "打开", "关闭"]:
    print(f"=========== {kw} ===========")
    for i, r in enumerate(w.engine.search_cn(kw, limit=10)):
        s = E.split_senses(r["zh"])
        cand = {x["word"].lower() for x in w.engine.search_cn(kw, limit=200)}
        print(f"  {i+1:2d}. {r['word']:<16} sc={E._sense_score(s,kw)} "
              f"rank={E._sense_rank(s,kw)} frq={r['frq']} col={r['collins']} "
              f"ox={r['oxford']} infl={int(E._is_infl_of_existing(r['word'], cand))}")
    print()

# environment 的 senses
for word in ("environment", "environmental"):
    r = w.engine.con.execute("SELECT zh FROM cn_index WHERE lower=?", (word,)).fetchone()
    if r:
        s = E.split_senses(r["zh"])
        print(f"{word}: senses={s}  sc={E._sense_score(s,'环境')} rank={E._sense_rank(s,'环境')}")
    else:
        print(f"{word}: 无 cn_index")
