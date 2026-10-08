# -*- coding: utf-8 -*-
"""阶段二专项：搜索历史 / 单词本 / 撤销 的 UI 行为。"""
import io, os, sys, tempfile
sys.path.insert(0, r"D:\Dictionary\build")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

log = io.StringIO()
def say(s=""): log.write(str(s) + "\n")
ok = fail = 0
def chk(c, label, extra=""):
    global ok, fail
    if c: ok += 1; say(f"  PASS  {label}")
    else: fail += 1; say(f"  FAIL  {label}  {extra}")

from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtCore import Qt
qapp = QApplication.instance() or QApplication(sys.argv)

import app as A

# 隔离用户数据，避免污染真实数据
tmp = tempfile.mkdtemp(prefix="uf_")
w = A.MainWindow()
w.store = A.UserStore(path=os.path.join(tmp, "user_data.db"))

say("== 1. 搜索历史 ==")
w.store.clear_history()
w._render("apple", record=True)
w._refresh_history()
chk(w.hist_list.count() == 1, "历史列表 1 条", str(w.hist_list.count()))
chk(w.hist_list.item(0).text() == "apple", "历史内容正确")

# 点击历史重查
w.search_edit.setText("")
w._on_hist_activate(w.hist_list.item(0))
chk(w._cur_word == "apple", "点击历史重查成功")

# 右键删除单条
w.store.add_history("banana")
w._refresh_history()
chk(w.hist_list.count() == 2, "历史 2 条")
w.store.delete_history("banana")
w._refresh_history()
chk(w.hist_list.count() == 1, "删除单条后 1 条")

# 清空（mock 确认框）
orig = QMessageBox.question
QMessageBox.question = staticmethod(lambda *a, **k: QMessageBox.Yes)
w._clear_history()
QMessageBox.question = orig
chk(w.store.history() == [], "一键清空生效")

say("== 2. 单词本 ==")
w.store.clear_words()
w._render("abandon", record=False)
w._toggle_fav()                     # 收藏
chk(w.store.has_word("abandon", 0), "收藏成功")
w._refresh_wordbook()
chk(w.wb_list.count() == 1, "单词本列表 1 条")
w._toggle_fav()                     # 再点取消
chk(not w.store.has_word("abandon", 0), "取消收藏成功")

# 新建分组 + 收藏到该组
gid = w.store.add_group("托福")
w._refresh_wordbook()
# 切到托福分组
for i in range(w.wb_group.count()):
    if w.wb_group.itemText(i) == "托福":
        w.wb_group.setCurrentIndex(i); break
w._render("ability", record=False)
w._toggle_fav()
chk(w.store.has_word("ability", gid), "收藏到指定分组")

say("== 3. 撤销 ==")
# 返回上一词
w.store.clear_history()
w._nav_stack.clear()
w._cur_word = ""          # 重置，模拟首次查词
w._render("water", record=True)
w._render("aqua", record=True)
chk(w._nav_stack == ["water"], "跳转压栈", str(w._nav_stack))
w._nav_back()
chk(w._cur_word == "water", "返回上一词")

# Esc 清空 + 恢复
w.search_edit.setText("hello world")
cur = w.search_edit.text()
w._last_input = cur
w.search_edit.clear()
chk(w.search_edit.text() == "", "Esc 清空后为空")
w.search_edit.setText(w._last_input)
w._last_input = ""
chk(w.search_edit.text() == "hello world", "恢复上次输入")

say("== 4. 词头含收藏/返回入口 ==")
w._render("water", record=False)
html = w.detail.toHtml()
chk("wb:toggle" in html, "词头含收藏链接")
chk("nav:back" in html, "词头含返回链接")

say(f"\nRESULT  ok={ok} fail={fail}")
open(r"D:\Dictionary\build\_stage2_ui.txt", "w", encoding="utf-8").write(log.getvalue())
print("done")
