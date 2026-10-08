# -*- coding: utf-8 -*-
"""验证部署版 exe 真能渲染例句 —— 关键是不用 build 目录的 app.py，
而是直接跑 exe，或至少确保用的是部署目录的路径解析。

这里用 offscreen 模式加载 build/app.py，但把工作目录设为 D:\Dictionary，
模拟 exe 运行时的 resource_path 解析，确认读到的是部署版 dict.db。
"""
import io
import os
import sys

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# 关键：模拟 exe 环境 —— 切到部署目录
os.chdir(r"D:\Dictionary")
sys.path.insert(0, r"D:\Dictionary\build")

ok = 0
bad = []


def chk(name, cond, extra=""):
    global ok
    if cond:
        ok += 1
        print(f"  PASS  {name}")
    else:
        bad.append(name)
        print(f"  FAIL  {name}  {extra}")


from PySide6.QtWidgets import QApplication
app = QApplication.instance() or QApplication(sys.argv)

import app as A


def type_and_wait(win, text, rounds=40):
    """输入并等查询完成。

    输入框带 220ms 防抖：setText 只是设置了挂起查询，必须等定时器
    到期并渲染完毕才能读结果。早期测试直接 setText + processEvents
    就读 detail，会因为「还没查」而误判成功能坏了。
    """
    import time
    win.search_edit.setText(text)
    for _ in range(rounds):
        app.processEvents()
        time.sleep(0.02)


print("== 0. 确认读到的是部署版词库 ==")
print(f"  cwd = {os.getcwd()}")
w = A.MainWindow()
if w.engine and w.engine.con:
    import sqlite3
    con = w.engine.con
    tabs = [r[0] for r in con.execute(
        "SELECT name FROM sqlite_master WHERE type='table'")]
    print(f"  词库表: {tabs}")
    chk("词库含 example 表", "example" in tabs, tabs)
    chk("词库含 ex_index 表", "ex_index" in tabs, tabs)
    n = con.execute("SELECT COUNT(*) FROM example").fetchone()[0]
    chk("例句数 > 5万", n > 50000, f"{n:,}")
else:
    chk("词库已加载", False, "engine 为空")

print("\n== 1. 查词渲染例句 ==")
for word in ("dog", "water", "abandon", "beautiful", "government"):
    type_and_wait(w, word)
    txt = w.detail.toPlainText()
    has = "Tatoeba" in txt
    chk(f"{word} 渲染出例句板块", has)
    if not has:
        print(f"    >>> 实际内容前 200 字: {txt[:200]!r}")

print("\n== 2. dog 页面里的例句原文 ==")
type_and_wait(w, "dog")
txt = w.detail.toPlainText()
idx = txt.find("例句")
if idx >= 0:
    print(txt[idx:idx + 500].replace("\n", "\n      "))
else:
    print("  **未找到「例句」标题**")
    print("  全文前 600 字:")
    print(txt[:600].replace("\n", "\n      "))

print("\n== 3. 例句数量符合预期（上限 6）==")
n = len(w.engine.examples("dog", limit=6))
chk("dog 取到 6 条", n == 6, n)

print(f"\n通过 {ok}，失败 {len(bad)}")
for b in bad:
    print(f"  X {b}")
sys.exit(1 if bad else 0)
