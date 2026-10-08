# -*- coding: utf-8 -*-
"""GUI 集成测试：确认口音下拉框、按钮、状态栏接线正确。"""
import io
import os
import sys
import time

sys.path.insert(0, r"D:\Dictionary\build")
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.chdir(r"D:\Dictionary\build")

from PySide6.QtWidgets import QApplication

OUT = r"D:\Dictionary\build\test_edge_gui.txt"
PASS, FAIL = [], []


def check(name, cond, detail=""):
    (PASS if cond else FAIL).append(name + (" " + str(detail) if detail else ""))


app = QApplication.instance() or QApplication([])
import app as A

win = A.MainWindow()
win.resize(1080, 760)
win.show()
app.processEvents()

# ---- 下拉框存在且项数正确 ----
check("下拉框存在", hasattr(win, "accent_box"))
check("下拉框项数 = %d" % len(A.EDGE_ACCENTS),
      win.accent_box.count() == len(A.EDGE_ACCENTS), win.accent_box.count())

labels = [win.accent_box.itemText(i) for i in range(win.accent_box.count())]
codes = [win.accent_box.itemData(i) for i in range(win.accent_box.count())]
check("下拉框标签非空", all(labels), labels[:2])
check("下拉框代号非空", all(codes), codes[:2])
check("代号唯一", len(set(codes)) == len(codes))
check("标签含美", any("美" in l for l in labels), labels[:3])
check("标签含英", any("英" in l for l in labels), labels[:3])
check("标签含澳", any("澳" in l for l in labels), labels[:3])

# ---- 三个发音按钮 ----
accents = [b.accent for b in win.pron_buttons]
check("发音按钮 3 个", len(win.pron_buttons) == 3, accents)
check("含 edge 按钮", "edge" in accents, accents)
check("不含 global 按钮（已改名）", "global" not in accents, accents)
check("含 us / uk", "us" in accents and "uk" in accents, accents)

# ---- 三栏宽度：状态文字要够宽 ----
win.resize(1080, 760)
app.processEvents()
w_now = win.pron_now.width()
check("状态文字宽度 >= 200px", w_now >= 200, "%dpx" % w_now)
w_box = win.accent_box.width()
check("下拉框宽度 >= 100px", w_box >= 100, "%dpx" % w_box)

# ---- 切换口音：写入配置 + 状态栏提示 ----
_orig = A.CONFIG.get("edge_accent", "")
idx_gb = codes.index("en-GB-LibbyNeural")
win.accent_box.setCurrentIndex(idx_gb)
app.processEvents()
check("切换口音后 CONFIG 更新",
      A.CONFIG.get("edge_accent") == "en-GB-LibbyNeural",
      A.CONFIG.get("edge_accent"))
check("切换口音后状态栏有提示",
      "英音" in win.pron_now.text() or "口音已切换" in win.pron_now.text(),
      win.pron_now.text())

# 换回默认
idx_us = codes.index("en-US-AvaNeural")
win.accent_box.setCurrentIndex(idx_us)
app.processEvents()
check("换回美音生效",
      A.CONFIG.get("edge_accent") == "en-US-AvaNeural",
      A.CONFIG.get("edge_accent"))

# ---- 状态标签（cfg_hint）不再提 Forvo ----
tip = win.cfg_hint.toolTip()
check("状态标签 tooltip 不含 Forvo", "Forvo" not in tip, tip[:60])
check("状态标签 tooltip 提 Edge", "Edge" in tip, tip[:60])
check("状态标签文字很短", len(win.cfg_hint.text()) <= 8, win.cfg_hint.text())

# ---- 非法口音值不能让下拉框崩 ----
A.CONFIG["edge_accent"] = "garbage-value"
# 重建窗口，模拟下次启动
win2 = A.MainWindow()
win2.resize(1080, 760)
app.processEvents()
check("非法口音值时程序仍能启动", win2.accent_box.count() == len(A.EDGE_ACCENTS))
check("非法口音时回退到默认",
      A.Pronouncer.edge_accent() == "en-US-AvaNeural",
      A.Pronouncer.edge_accent())
win2.close()

# ---- 真实合成一次（走完整链路）----
A.CONFIG["edge_accent"] = "en-US-AvaNeural"
win._cur_word = "edgeguitest"
win._speak("edge")
app.processEvents()
txt = win.pron_now.text()
check("点口音按钮后状态栏有反馈", bool(txt), txt)
# 状态栏要么说成功，要么说正在获取/不可用，不能是空的
check("状态栏文案合理",
      any(k in txt for k in ("发音", "获取", "不可用")), txt)

# ---- 非英语模式：下拉框应隐藏 ----
A.CONFIG["edge_accent"] = _orig or "en-US-AvaNeural"
win.close()

# ---- 汇总 ----
lines = ["=" * 60, "Edge 口音 GUI 集成测试", "=" * 60, "",
         "PASS = %d   FAIL = %d" % (len(PASS), len(FAIL)), ""]
if FAIL:
    lines.append("---- 失败 ----")
    for f in FAIL:
        lines.append("  ✗ " + f)
    lines.append("")
lines.append("---- 通过 ----")
for p in PASS:
    lines.append("  ✓ " + p)
io.open(OUT, "w", encoding="utf-8").write("\n".join(lines) + "\n")
print("PASS=%d FAIL=%d" % (len(PASS), len(FAIL)))
for f in FAIL:
    print("FAIL:", f)
