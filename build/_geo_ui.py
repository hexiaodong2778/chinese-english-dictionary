# -*- coding: utf-8 -*-
"""几何量测：确认新增控件没有互相压叠、也没把老控件挤坏。"""
import io
import os
import sys
import tempfile

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, r"D:\Dictionary\build")

from PySide6.QtWidgets import QApplication

qapp = QApplication(sys.argv)
import app as A

_TMP = tempfile.mkdtemp(prefix="geo_")
_o = A.UserStore.__init__
A.UserStore.__init__ = lambda self, path=None: _o(
    self, os.path.join(_TMP, "user_data.db"))

w = A.MainWindow()
w.resize(1080, 720)
w.show()
qapp.processEvents()
w.search_edit.setText("happy")
w._flush_query()
for _ in range(6):
    qapp.processEvents()


def geo(name, wdg):
    if not hasattr(wdg, "geometry"):
        print("  %-14s <无 geometry>" % name)
        return None
    g = wdg.geometry()
    tl = wdg.mapTo(w, g.topLeft())
    print("  %-14s x=%-5d y=%-5d w=%-4d h=%-3d  可见=%s 启用=%s"
          % (name, tl.x(), tl.y(), g.width(), g.height(),
             wdg.isVisible(), wdg.isEnabled()))
    return (tl.x(), tl.y(), g.width(), g.height())


def overlap(a, b, n1, n2):
    if not a or not b:
        return
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    inter_w = min(ax + aw, bx + bw) - max(ax, bx)
    inter_h = min(ay + ah, by + bh) - max(ay, by)
    if inter_w > 0 and inter_h > 0:
        print("  ⚠ 重叠 %s × %s → %dx%d" % (n1, n2, inter_w, inter_h))
        return True
    return False


print("=" * 74)
print("窗口 1080x720")
print("=" * 74)
for idx, tab in [(1, "历史"), (2, "单词本")]:
    w.side_tabs.setCurrentIndex(idx)
    for _ in range(4):
        qapp.processEvents()
    print("\n-- 侧栏第 %d 个 Tab（%s）--" % (idx, tab))
    print("  侧栏卡片宽 =", w.side_tabs.parent().width())
    a = geo("undo_btn", w.undo_btn)
    b = geo("undo_hint", w.undo_hint)
    c = geo("wb_export", w.wb_export_btn)
    d = geo("wb_clear", w.wb_clear_btn)
    e = geo("wb_count", w.wb_count)
    g = geo("wb_group", w.wb_group)
    h = geo("wb_newgrp", w.wb_newgrp_btn)
    overlap(a, c, "undo_btn", "wb_export")
    overlap(a, d, "undo_btn", "wb_clear")
    overlap(b, c, "undo_hint", "wb_export")
    overlap(a, b, "undo_btn", "undo_hint")
    overlap(g, h, "wb_group", "wb_newgrp")
    if c and d:
        print("  导出 与 清空 是否分离:", c[0] + c[2] <= d[0] or d[0] + d[2] <= c[0])

print()
print("-- 底部发音栏（确认撤销按钮**不在**这里）--")
p = geo("pron_now", w.pron_now)
geo("fav_btn", w.fav_btn)
geo("accent_box", w.accent_box)
geo("cfg_hint", w.cfg_hint)
print("  ⚠ pron_now 宽度必须 >= 246（否则发音文字被截断）→", p[2] if p else "?")

print()
print("-- 词头返回按钮 --")
w._render("computer", record=True)
w._render("happy", record=True)
for _ in range(4):
    qapp.processEvents()
html = w.detail.toHtml()
print("  nav_stack =", w._nav_stack)
print("  词头含 nav:back 链接 =", "nav:back" in html)
# 抓「返回」与「收藏」两个胶囊的实际渲染位置（按 HTML 表格结构推算）
import re
m = re.search(r"border-radius:11px;padding:2px 10px;'>(.*?)</a>", html)
print("  词头胶囊按钮文字 =", m.group(1) if m else "(未找到)")

print()
print("-- 窗口缩到 980x660（较窄，检查是否溢出）--")
w.resize(980, 660)
for _ in range(6):
    qapp.processEvents()
p2 = geo("pron_now", w.pron_now)
print("  pron_now 宽度 =", p2[2] if p2 else "?")
print("  侧栏宽 =", w.side_tabs.parent().width())
print("  undo_btn 宽 =", w.undo_btn.width(), "(side=%s)" % w.undo_btn.isVisible())

print()
print("-- 撤销按钮状态切换 --")
print("  初始 enabled =", w.undo_btn.isEnabled(), "hint=",
      repr(w.undo_hint.text()))
snap = w.store.snapshot_words(0)
w.store.clear_words_group(0)
w._push_undo("清空分组「默认分组」（3 词）",
             lambda: w.store.restore_words(snap, 0))
for _ in range(3):
    qapp.processEvents()
print("  压栈后 enabled =", w.undo_btn.isEnabled(), "hint=",
      repr(w.undo_hint.text()))
print("  hint 宽度 =", w.undo_hint.width(), " 需 =", w.undo_hint.sizeHint().width())
w._do_undo()
for _ in range(3):
    qapp.processEvents()
print("  撤销后 enabled =", w.undo_btn.isEnabled(), "hint=",
      repr(w.undo_hint.text()))
print("DONE")
