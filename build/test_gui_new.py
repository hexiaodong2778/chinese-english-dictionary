# -*- coding: utf-8 -*-
"""在真实 Qt 环境里验证新功能：官方词典按钮行 + 例句板块渲染。

不弹窗（用 offscreen 平台），只检查控件是否建好、HTML 是否含预期内容。
"""
import io
import os
import sys

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
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
import time


def type_and_wait(win, text, rounds=40):
    """输入并等查询完成。

    输入框带 220ms 防抖（避免每键都打数据库导致打字卡顿），
    setText 只登记挂起查询，必须等定时器到期 + 渲染完成才能读结果。
    """
    win.search_edit.setText(text)
    for _ in range(rounds):
        app.processEvents()
        time.sleep(0.02)


w = A.MainWindow()

print("== 1. 官方词典按钮行 ==")
chk("od_buttons 数量 = 6", len(w.od_buttons) == 6, len(w.od_buttons))
labels = [b.text() for b in w.od_buttons]
chk("按钮文字正确", labels == ["牛津", "剑桥", "柯林斯", "朗文", "韦氏", "词源"], labels)
chk("od_host 可见", w.od_host is not None)
chk("每个按钮都有 tooltip", all(b.toolTip() for b in w.od_buttons))

print("\n== 2. 查词后渲染例句 ==")
type_and_wait(w, "dog")
html = w.detail.toHtml()
chk("dog 词条已渲染", "dog" in html.lower())
chk("含例句板块标题", "例句" in html)
chk("含 Tatoeba 出处说明", "Tatoeba" in html)
chk("含真实例句英文", "dog" in html.lower())
# 抓一条例句验证中文译文也进来了
chk("含中文译文（句号/问号等）",
    any(x in html for x in ["。", "？", "！"]), "")

print("\n  当前 dog 页面里出现的例句片段:")
import re
# 从 detail 的纯文本里找英文句子
txt = w.detail.toPlainText()
for line in txt.split("\n"):
    ln = line.strip()
    if len(ln) > 18 and re.match(r"^[A-Z][a-zA-Z' ,\-]+[.!?]?$", ln):
        print(f"      {ln}")

print("\n== 3. 无例句的词不显示板块 ==")
type_and_wait(w, "zzzzqqqq")
chk("生僻词不崩溃", True)
t2 = w.detail.toPlainText()
chk("生僻词无例句板块", "Tatoeba" not in t2)

print("\n== 4. 有例句的词逐个验证 ==")
for word in ("water", "abandon", "beautiful", "government", "school",
             "environment", "computer", "friend"):
    type_and_wait(w, word)
    t = w.detail.toPlainText()
    has = "Tatoeba" in t
    chk(f"{word} 有例句板块", has)
    if has and word == "water":
        # 打印前几条
        idx = t.find("Tatoeba")
        print("      " + t[idx:idx + 320].replace("\n", "\n      ")[:340])

print("\n== 5. _od_open 不抛异常（不真的开浏览器）==")
import PySide6.QtGui as QG
calls = []
orig = QG.QDesktopServices.openUrl
QG.QDesktopServices.openUrl = staticmethod(lambda u: calls.append(u.toString()) or True)
try:
    type_and_wait(w, "beautiful")
    for b in w.od_buttons:
        b.click()
    chk("6 个按钮都触发了打开", len(calls) == 6, len(calls))
    for u in calls:
        print(f"      {u}")
    chk("URL 里带上了词", all("beautiful" in u for u in calls), calls[:1])
    chk("URL 都是 https", all(u.startswith("https://") for u in calls))
finally:
    QG.QDesktopServices.openUrl = orig

print("\n== 6. 中译英时官方词典按钮仍可用 ==")
w.cn_btn.setChecked(True)
w._on_cn_toggle()
type_and_wait(w, "美丽")
calls.clear()
QG.QDesktopServices.openUrl = staticmethod(lambda u: calls.append(u.toString()) or True)
try:
    w.od_buttons[0].click()
    chk("中译英模式下可打开官方词典", len(calls) == 1, calls)
    print(f"      {calls[0] if calls else ''}")
finally:
    QG.QDesktopServices.openUrl = orig

print(f"\n通过 {ok}，失败 {len(bad)}")
for b in bad:
    print(f"  X {b}")
sys.exit(1 if bad else 0)
