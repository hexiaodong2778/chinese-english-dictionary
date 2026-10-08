# -*- coding: utf-8 -*-
"""GUI 冒烟测试：确认改动后 app.py 仍能正常加载和渲染。"""
import os
import sys

sys.path.insert(0, r"D:\Dictionary\build")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.chdir(r"D:\Dictionary")

out = []
from PySide6.QtWidgets import QApplication
app = QApplication.instance() or QApplication([])

import app as A

w = A.MainWindow()
w.resize(1200, 800)
w.show()
out.append("✓ MainWindow 构造成功")

# 查几个词，确认渲染不炸
for word in ["water", "abbreviation", "record", "a priori", "abandon"]:
    try:
        w._render(word)
        txt = w.detail.toPlainText()
        ok = word.lower() in txt.lower() or len(txt) > 50
        out.append(f"  _render({word!r}) -> {len(txt)} 字符  "
                   f"{'✓' if ok else '⚠内容异常'}")
    except Exception as e:
        out.append(f"  _render({word!r}) -> ✗ {type(e).__name__}: {e}")

# 检查音标是否正常显示（新音标带 U+02C8 重音符）
w._render("abbreviation")
txt = w.detail.toPlainText()
out.append("")
out.append("abbreviation 渲染内容片段：")
for line in txt.split("\n")[:8]:
    if line.strip():
        out.append(f"    {line.strip()[:80]}")

# 发音按钮
out.append("")
out.append("发音按钮测试：")
try:
    w._cur_word = "water"
    w._cur_ph_uk = "ˈwɒ:tә"
    w._cur_ph_us = "ˈwætә"
    for acc in ("us", "uk", "global"):
        w._speak(acc)
        out.append(f"  _speak({acc!r}) -> {w.pron_now.text()}")
except Exception as e:
    out.append(f"  ✗ {type(e).__name__}: {e}")

# 欢迎页
try:
    w._show_welcome()
    out.append("")
    out.append("✓ 欢迎页渲染成功")
except Exception as e:
    out.append(f"✗ 欢迎页: {e}")

# 音标字段检查
out.append("")
out.append("音标数据检查（通过 app 的 engine）：")
try:
    d = w.engine.lookup("abbreviation", w._dict_key())
    out.append(f"  abbreviation: 英={d.get('phonetic')!r} 美={d.get('phonetic_us')!r}")
    d = w.engine.lookup("water", w._dict_key())
    out.append(f"  water:        英={d.get('phonetic')!r} 美={d.get('phonetic_us')!r}")
    d = w.engine.lookup("abandon", w._dict_key())
    out.append(f"  abandon:      英={d.get('phonetic')!r} 美={d.get('phonetic_us')!r}")
except Exception as e:
    out.append(f"  ✗ {type(e).__name__}: {e}")

open(r"D:\Dictionary\build\_gui_smoke2.txt", "w", encoding="utf-8").write(
    "\n".join(out))
print("ok")
