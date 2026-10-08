# -*- coding: utf-8 -*-
"""截图：验证侧栏撤销条 / 单词本清空按钮 / 词头「返回」胶囊按钮。"""
import io
import os
import sys

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, r"D:\Dictionary\build")

from PySide6.QtWidgets import QApplication

qapp = QApplication(sys.argv)
import app as A

import tempfile
_TMP = tempfile.mkdtemp(prefix="shot_")
_o = A.UserStore.__init__
A.UserStore.__init__ = lambda self, path=None: _o(
    self, os.path.join(_TMP, "user_data.db"))

w = A.MainWindow()
w.resize(1080, 720)
w.show()
qapp.processEvents()

# 造点数据，让三个 UI 都有内容可显示
for x in ["happy", "computer", "environment", "abandon", "beautiful"]:
    w.store.add_history(x)
w.store.add_word("happy", 0)
w.store.add_word("computer", 0)
w.store.add_word("environment", 0)
w._refresh_history()

w.search_edit.setText("happy")
w._flush_query()
for _ in range(6):
    qapp.processEvents()

# 造一次可撤销的操作，让撤销按钮从置灰变可用
snap = w.store.snapshot_words(0)
w.store.clear_words_group(0)
w._push_undo("清空分组「默认分组」（3 词）",
             lambda: w.store.restore_words(snap, 0))
w._reload_wb_list()
w._sync_undo_btn()
w.pron_now.setText("已清空默认分组的 3 个单词 · 可撤销（Ctrl+Z）")
for _ in range(4):
    qapp.processEvents()

print("undo_btn enabled =", w.undo_btn.isEnabled())
print("undo_btn text    =", repr(w.undo_btn.text()))
print("undo_hint text   =", repr(w.undo_hint.text()))
print("undo_btn size    =", w.undo_btn.width(), "x", w.undo_btn.height())

# ① 历史 Tab（能看到撤销条）
w.side_tabs.setCurrentIndex(1)
for _ in range(4):
    qapp.processEvents()
w.grab().save(r"D:\Dictionary\build\_shot_undo.png")
print("saved _shot_undo.png")

# ② 单词本 Tab（能看到「清空」按钮 + 撤销条）
w.side_tabs.setCurrentIndex(2)
for _ in range(4):
    qapp.processEvents()
w.grab().save(r"D:\Dictionary\build\_shot_wordbook.png")
print("saved _shot_wordbook.png")

# ③ 词头「返回」胶囊（先跳一个词制造返回栈）
w._render("computer", record=True)
w._render("happy", record=True)
for _ in range(4):
    qapp.processEvents()
print("nav_stack =", w._nav_stack)
print("返回按钮出现在词头 =", "nav:back" in w.detail.toHtml()
      or "返回" in w.detail.toPlainText())
w.grab().save(r"D:\Dictionary\build\_shot_back.png")
print("saved _shot_back.png")

# ④ 翻译对话框
dlg = A.TranslateDialog()
dlg.resize(620, 580)
dlg.in_edit.setPlainText("一举两得")
dlg._do_translate()
import time
for _ in range(80):
    qapp.processEvents()
    if not dlg._busy:
        break
    time.sleep(0.05)
print("translate status =", repr(dlg.status.text()))
print("translate out    =", repr(dlg.out_view.toPlainText()[:80]))
dlg.show()
for _ in range(6):
    qapp.processEvents()
dlg.grab().save(r"D:\Dictionary\build\_shot_trans.png")
print("saved _shot_trans.png")

print("DONE")
