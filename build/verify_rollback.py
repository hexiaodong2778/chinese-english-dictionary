# -*- coding: utf-8 -*-
"""回滚终检：源码 == 原版行为，常量已就位。"""
import io, os, sys
sys.path.insert(0, r"D:\Dictionary\build")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

log = io.StringIO()
def say(s=""): log.write(str(s) + "\n")

import app
from PySide6.QtWidgets import QApplication

ok, fail = 0, []
def chk(c, l):
    global ok
    if c: ok += 1
    else: fail.append(l)

say("=== 常量 ===")
for k, v in {"APP_NAME": "查单词", "APP_NAME_EN": "MinimalDict",
             "APP_SUBTITLE": "离线词典 · 发音需联网", "APP_SEAL_CHAR": "典"}.items():
    g = getattr(app, k, None)
    say(f"  {k:16s} = {g!r}")
    chk(g == v, k)

say("\n=== 关键源码行 ===")
src = open(r"D:\Dictionary\build\app.py", encoding="utf-8").read()
checks = [
    ('p.drawText(58, 34, self.name)', "书名绘制（坐标 58,34）"),
    ('p.drawText(59, 50, self.subtitle)', "副标题绘制（坐标 59,50）"),
    ('p.drawLine(200, 33, w - 24, 33)', "装饰线（硬编码 200）"),
    ('self.setWindowTitle(f"{APP_NAME} · {APP_NAME_EN}")', "窗口标题"),
    ('app.setApplicationName(APP_NAME)', "应用名"),
    ('app.setApplicationDisplayName(APP_NAME)', "显示名"),
    ('return os.path.join(base, APP_NAME, "audio")', "缓存目录"),
    ('f"{APP_NAME}_错误日志.txt"', "错误日志名"),
    ('f"{APP_NAME}_启动日志.txt"', "启动日志名"),
    ('os.environ.get(f"{APP_NAME}_调试")', "调试环境变量"),
    ('self.subtitle = APP_SUBTITLE', "字标副标题"),
    ('self.name = APP_NAME', "字标书名"),
]
for pat, label in checks:
    hit = pat in src
    say(f"  {'OK ' if hit else 'MISS'}  {label}")
    chk(hit, label)

say("\n=== 确认没有遗留的 _tx / _rule_x ===")
chk("_rule_x" not in src, "无 _rule_x 残留")
chk("_tx" not in src, "无 _tx 残留")

say("\n=== 字标运行时 ===")
qapp = QApplication.instance() or QApplication(sys.argv)
wm = app.Wordmark()
say(f"  name={wm.name!r} subtitle={wm.subtitle!r} NAME_PT={wm.NAME_PT}")
chk(wm.name == "查单词" and wm.NAME_PT == 17, "字标参数与原版一致")

say("\n=== 窗口 ===")
w = app.MainWindow()
say(f"  title = {w.windowTitle()!r}")
chk(w.windowTitle() == "查单词 · MinimalDict", "窗口标题原文")

say(f"\nRESULT: {ok} passed, {len(fail)} failed")
for f_ in fail: say("  FAIL: " + f_)
open(r"D:\Dictionary\build\_verify_rollback.txt", "w", encoding="utf-8").write(log.getvalue())
print("done")
