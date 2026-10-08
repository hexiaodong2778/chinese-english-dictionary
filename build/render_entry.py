# -*- coding: utf-8 -*-
"""把 dog 词条的渲染 HTML 导出为一张可读的预览图。

用 Qt 的富文本引擎把 detail 的 HTML 渲染到一张图上，
这样能直观看到「例句板块」在词条里的实际位置与样式。
"""
import io
import os
import sys

os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.chdir(r"D:\Dictionary")
sys.path.insert(0, r"D:\Dictionary\build")
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QTextDocument, QPainter, QImage, QColor
from PySide6.QtCore import QSizeF, Qt

app = QApplication.instance() or QApplication(sys.argv)

import app as A

w = A.MainWindow()
w.search_edit.setText("dog")
app.processEvents()

html = w.detail.toHtml()
raw = w.detail.toPlainText()
print(f"HTML 长度 = {len(html)}")
print(f"纯文本长度 = {len(raw)}")
print(f"含『例句』 = {'例句' in raw}")
print(f"含『Tatoeba』 = {'Tatoeba' in raw}")

# 渲染成图
doc = QTextDocument()
doc.setHtml(html)
doc.setTextWidth(720)
h = int(doc.size().height()) + 40
OUT = r"D:\Dictionary\build\dog_entry_render.png"
img = QImage(760, min(h, 4000), QImage.Format_RGB32)
img.fill(QColor("#fdfcf9"))
p = QPainter(img)
p.translate(20, 20)
doc.drawContents(p, __import__("PySide6.QtCore", fromlist=["QRectF"]).QRectF(0, 0, 720, min(h, 4000)))
p.end()
img.save(OUT, "PNG")
print(f"\nrender -> {OUT}  {os.path.getsize(OUT):,} bytes  {img.size()}")

# 同时导出纯文本，便于直接看内容
txt_out = r"D:\Dictionary\build\dog_entry_text.txt"
io.open(txt_out, "w", encoding="utf-8").write(raw)
print(f"text   -> {txt_out}")
print("\n--- 纯文本内容 ---")
print(raw)
