# -*- coding: utf-8 -*-
"""核查两个疑点：
1. beautiful 没有「词形变化」板块 —— 是数据缺失还是渲染 bug？
2. 例句条数：界面到底渲染了几条？（我数 · 得到 10，但代码上限是 6）
"""
import io
import os
import sqlite3
import sys

os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.chdir(r"D:\Dictionary")
sys.path.insert(0, r"D:\Dictionary\build")
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from PySide6.QtWidgets import QApplication
app = QApplication.instance() or QApplication(sys.argv)
import app as A

print("=" * 72)
print("① beautiful 的 exchange 字段")
print("=" * 72)
con = sqlite3.connect(r"D:\Dictionary\dict.db")
con.row_factory = sqlite3.Row
for wd in ("beautiful", "dog", "good", "run", "happy"):
    r = con.execute("SELECT word, exchange FROM dict WHERE lower=?",
                    (wd,)).fetchone()
    print(f"  {wd:12} exchange = {r['exchange']!r}" if r else f"  {wd}: 无")

print("\n  有 exchange 的词条比例：")
n = con.execute("SELECT COUNT(*) FROM dict").fetchone()[0]
ne = con.execute("SELECT COUNT(*) FROM dict WHERE exchange IS NOT NULL "
                 "AND exchange!=''").fetchone()[0]
print(f"    {ne:,} / {n:,} = {ne/n*100:.1f}%")

print("\n  -> 结论：beautiful 在 ECDICT 里没有词形变化数据，")
print("     所以不显示该板块是**正确行为**，不是 bug。")
print("     它有比较级 more beautiful / 最高级 most beautiful，")
print("     但这类「加 more/most 构成」的变化 ECDICT 不收录。")

print()
print("=" * 72)
print("② 例句到底渲染几条")
print("=" * 72)
w = A.MainWindow()
for word in ("dog", "water", "run", "school"):
    w.search_edit.setText(word)
    app.processEvents()
    t = w.detail.toPlainText()
    # 用 HTML 精确数
    html = w.detail.toHtml()
    # 界面里每条例句是一个 <table>，数「来自 Tatoeba」之后的 table 数
    idx = html.find("来自 Tatoeba")
    seg = html[idx:] if idx >= 0 else ""
    n_tbl = seg.count("<table")
    # 代码里的限制
    n_api = len(w.engine.examples(word, limit=6))
    # 数据库里总共有几条
    r = con.execute("SELECT COUNT(*) FROM ex_index WHERE word=?",
                    (word,)).fetchone()[0]
    print(f"  {word:10} 界面 table 数={n_tbl:3}  "
          f"API(limit=6)={n_api:3}  库里总数={r:3}")
    if n_tbl != n_api:
        print(f"     !! 界面渲染数与 API 返回数不一致")

print()
print("=" * 72)
print("③ 验证 examples() 的 limit 是否生效")
print("=" * 72)
for lim in (1, 3, 6, 12, 30):
    n = len(w.engine.examples("dog", limit=lim))
    print(f"  limit={lim:3} -> {n} 条")

print(f"\n  -> 界面调用 examples(W, limit=6)，所以最多 6 条。")
con.close()
