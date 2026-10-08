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

for word in ["drink", "close", "begin", "sleep", "look", "money",
             "open", "walk", "go", "eat"]:
    r = con.execute(
        "SELECT word, translation, frq, collins, oxford FROM dict "
        "WHERE lower=? LIMIT 1", (word,)).fetchone()
    if r:
        t = (r["translation"] or "").replace("\\n", " | ")
        print(f"{word:<8} frq={r['frq']:<8} col={r['collins']} ox={r['oxford']}")
        print(f"         {t[:130]}")
    else:
        print(f"{word:<8} ** 不在 dict 表 **")
    # cn_index 里这个词有几条
    n = con.execute("SELECT COUNT(*) FROM cn_index WHERE lower=?",
                    (word,)).fetchone()[0]
    print(f"         cn_index 条数={n}")
    print()

print("=== cn_index 里 drink 的 zh ===")
for r in con.execute("SELECT word, zh FROM cn_index WHERE lower='drink'"):
    print(f"   {r['word']!r}  zh={r['zh']!r}")
print()
print("=== cn_index 里 close 的 zh ===")
for r in con.execute("SELECT word, zh FROM cn_index WHERE lower='close'"):
    print(f"   {r['word']!r}  zh={r['zh']!r}")
print()
print("=== 直接 SQL：zh 含『喝』的前 20 条 ===")
for r in con.execute(
        "SELECT word, zh, frq FROM cn_index WHERE zh LIKE '%喝%' LIMIT 20"):
    print(f"   {r['word']:<16} frq={r['frq']:<8} {r['zh'][:45]}")
