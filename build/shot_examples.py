# -*- coding: utf-8 -*-
"""渲染一张词条页面的截图，展示例句板块的位置和效果。"""
import io
import os
import sys

os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.chdir(r"D:\Dictionary")
sys.path.insert(0, r"D:\Dictionary\build")
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer, QSize

app = QApplication.instance() or QApplication(sys.argv)

import app as A

w = A.MainWindow()
w.resize(1240, 860)
w.show()
app.processEvents()

w.search_edit.setText("dog")
app.processEvents()

# 滚到例句位置
w.detail.verticalScrollBar().setValue(0)
app.processEvents()

# 截整窗
for i in range(6):
    app.processEvents()

pm = w.grab()
OUT = r"D:\Dictionary\build\shot_examples_full.png"
pm.save(OUT, "PNG")
print(f"full -> {OUT}  {os.path.getsize(OUT):,} bytes  {pm.size()}")

# 只截详情区（含例句）
d = w.detail
pm2 = d.grab()
OUT2 = r"D:\Dictionary\build\shot_examples_panel.png"
pm2.save(OUT2, "PNG")
print(f"panel -> {OUT2}  {os.path.getsize(OUT2):,} bytes  {pm2.size()}")
