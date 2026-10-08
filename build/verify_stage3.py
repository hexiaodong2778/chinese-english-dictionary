# -*- coding: utf-8 -*-
"""阶段三：联网词典增强（有道 jsonapi）测试。"""
import io, os, sys
sys.path.insert(0, r"D:\Dictionary\build")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

log = io.StringIO()
def say(s=""): log.write(str(s) + "\n")
ok = fail = 0
def chk(c, label, extra=""):
    global ok, fail
    if c: ok += 1; say(f"  PASS  {label}")
    else: fail += 1; say(f"  FAIL  {label}  {extra}")

import app as A

say("== fetch_online_def ==")
d = A.fetch_online_def("water")
say(f"  keys: {list(d.keys())}")
say(f"  english: {d.get('english')}")
say(f"  collins: {d.get('collins')[:1]}")
say(f"  synos: {d.get('synos')}")
say(f"  examples: {d.get('examples')[:2]}")
chk(bool(d.get("english")), "拿到英英释义")
chk(bool(d.get("collins")), "拿到柯林斯释义")
chk(bool(d.get("synos")), "拿到同义词")

say("\n== 无网/失败回退 ==")
d2 = A.fetch_online_def("zzzznonexistentword9999")
say(f"  english: {d2.get('english')}")
chk(d2 == {} or not d2.get("english"), "无结果安全返回")

say("\n== 渲染集成 ==")
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer, QEventLoop
qapp = QApplication.instance() or QApplication(sys.argv)

w = A.MainWindow()
w._online_cache["water"] = A.fetch_online_def("water")
w._render("water", record=False)
html = w.detail.toHtml()
chk("英英释义" in html, "渲染含英英释义区块")
chk("柯林斯" in html, "渲染含柯林斯区块")
chk("同义词" in html, "渲染含同义词区块")

say("\n== 异步获取流程 ==")
w2 = A.MainWindow()
w2._online_cache.clear()
w2._render("apple", record=False)
chk("apple" in w2._online_fetching or "apple" in w2._online_cache,
    "已触发异步获取", str(w2._online_fetching))
# 跑事件循环等异步完成
loop = QEventLoop()
QTimer.singleShot(4000, loop.quit)
loop.exec()
chk("apple" in w2._online_cache, "异步获取后写入缓存",
    f"cache keys={list(w2._online_cache.keys())}")
if "apple" in w2._online_cache:
    html2 = w2.detail.toHtml()
    chk("英英释义" in html2, "异步后重渲染含英英释义")

say(f"\nRESULT  ok={ok} fail={fail}")
open(r"D:\Dictionary\build\_stage3.txt", "w", encoding="utf-8").write(log.getvalue())
print("done")
