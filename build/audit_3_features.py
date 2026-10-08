# -*- coding: utf-8 -*-
"""全方位检查 ③：逐项验证全部功能的渲染结果。

模拟 exe 环境（cwd = 部署目录），把每个功能都点一遍，
确认渲染内容正确、不报错。
"""
import io
import os
import sys

os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.chdir(r"D:\Dictionary")
sys.path.insert(0, r"D:\Dictionary\build")
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from PySide6.QtWidgets import QApplication
import PySide6.QtGui as QG

app = QApplication.instance() or QApplication(sys.argv)
import app as A

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


w = A.MainWindow()
w.resize(1280, 880)
app.processEvents()

print("=" * 72)
print("① 查英文词 —— 词条结构完整")
print("=" * 72)
w.search_edit.setText("beautiful")
app.processEvents()
t = w.detail.toPlainText()
for part in ("beautiful", "美", "英", "中文释义", "英文释义", "例句", "词形变化"):
    chk(f"含「{part}」", part in t)
print(f"\n  渲染长度: {len(t)}")
print("  内容预览:")
for ln in t.split("\n")[:22]:
    if ln.strip():
        print(f"    {ln[:88]}")

print()
print("=" * 72)
print("② 中译英")
print("=" * 72)
for cn, expect in (("狗", "dog"), ("放弃", "abandon"), ("美丽", "beautiful"),
                   ("环境", "environment"), ("钱", "money")):
    w.search_edit.setText(cn)
    app.processEvents()
    first = ""
    if w.result_list.count():
        first = (w.result_list.item(0).text() or "").split("\n")[0].strip()
    hit = expect.lower() in first.lower()
    chk(f"{cn} → {expect}", hit, f"实际第一: {first}")
    print(f"      {cn} -> {first}")

print()
print("=" * 72)
print("③ 词形还原")
print("=" * 72)
for form, lemma in (("went", "go"), ("apples", "apple"), ("running", "run"),
                    ("better", "good"), ("children", "child")):
    w.search_edit.setText(form)
    app.processEvents()
    t = w.detail.toPlainText()
    head = t.split("\n")[0] if t else ""
    restored = lemma in head.lower() or "还原" in t
    chk(f"{form} → {lemma}", restored, f"首行: {head[:50]}")
    print(f"      {form} -> 首行 '{head[:40]}'  含还原提示={'还原' in t}")

print()
print("=" * 72)
print("④ 五部词典切换")
print("=" * 72)
for i, d in enumerate(A.DICTS):
    w.cur_dict_idx = i
    w._refresh_dict_buttons()
    w.search_edit.setText("beautiful")
    app.processEvents()
    t = w.detail.toPlainText()
    has_note = "不在" in t
    chk(f"{d['label']} 能渲染", len(t) > 10, len(t))
    print(f"      {d['label']:6} len={len(t):5}  词表提示={'有' if has_note else '无'}")

print()
print("=" * 72)
print("⑤ 官方词典按钮（6 部）")
print("=" * 72)
calls = []
orig = QG.QDesktopServices.openUrl
QG.QDesktopServices.openUrl = staticmethod(
    lambda u: calls.append(u.toString()) or True)
try:
    w.cur_dict_idx = 0
    w.search_edit.setText("beautiful")
    app.processEvents()
    for b in w.od_buttons:
        calls.clear()
        b.click()
        okk = len(calls) == 1 and "beautiful" in calls[0]
        chk(f"{b.text()} 打开正确 URL", okk, calls)
    print(f"\n  共 {len(w.od_buttons)} 个按钮全部工作")
finally:
    QG.QDesktopServices.openUrl = orig

print()
print("=" * 72)
print("⑥ 例句板块")
print("=" * 72)
for word in ("dog", "water", "abandon", "beautiful", "government",
             "school", "environment", "computer", "friend", "run"):
    w.search_edit.setText(word)
    app.processEvents()
    t = w.detail.toPlainText()
    has = "Tatoeba" in t
    chk(f"{word} 有例句", has)
    if has:
        # 数一下有几个例句
        idx = t.find("来自 Tatoeba")
        seg = t[idx:]
        cnt = seg.count("·")
        print(f"      {word}: {cnt} 条例句")

print()
print("=" * 72)
print("⑦ AI 按钮与站点选择")
print("=" * 72)
chk(f"AI 按钮 {len(w.ai_buttons)} 个", len(w.ai_buttons) == 4)
chk(f"AI 站点 {w.ai_svc_box.count()} 个", w.ai_svc_box.count() == 7)
names = [w.ai_buttons[i].text() for i in range(len(w.ai_buttons))]
print(f"  按钮: {names}")
svcs = [w.ai_svc_box.itemText(i) for i in range(w.ai_svc_box.count())]
print(f"  站点: {svcs}")
chk("站点含豆包", "豆包" in svcs, svcs)

print()
print("=" * 72)
print("⑧ 空状态与边界")
print("=" * 72)
w.search_edit.setText("")
app.processEvents()
t = w.detail.toPlainText()
chk("空输入显示欢迎页", "开始查词" in t, t[:40])

w.search_edit.setText("zzzzqqqxxx")
app.processEvents()
t = w.detail.toPlainText()
chk("生僻词显示未找到", "未找到" in t or "没有匹配" in t, t[:40])

w.search_edit.setText("a")
app.processEvents()
chk("单字母查询不崩", True)
print(f"      单字母 'a' 候选数: {w.result_list.count()}")

print()
print("=" * 72)
print("⑨ 语言切换")
print("=" * 72)
for i in range(w.lang_box.count()):
    key = w.lang_box.itemData(i)
    label = w.lang_box.itemText(i)
    w.lang_box.setCurrentIndex(i)
    app.processEvents()
    loaded = w.engine is not None and w.engine.con is not None
    chk(f"{label} 词库加载", loaded)
    if loaded:
        probe = {"en": "dog", "ja": "日本", "fr": "bonjour",
                 "yue": "你"}.get(key, "a")
        w.search_edit.setText(probe)
        app.processEvents()
        t = w.detail.toPlainText()
        chk(f"{label} 查询 '{probe}' 有结果", len(t) > 3, len(t))
        print(f"      渲染: {t[:70]!r}")

print()
print("=" * 72)
print("⑩ 字母索引条")
print("=" * 72)
w.lang_box.setCurrentIndex(0)
app.processEvents()
for ch in ("a", "s", "z"):
    w._on_letter(ch)
    app.processEvents()
    n = w.result_list.count()
    chk(f"字母 {ch} 有候选", n > 0, n)
    print(f"      {ch}: {n} 个候选")

print()
print("=" * 72)
print(f"结论：通过 {ok}，失败 {len(bad)}")
for b in bad:
    print(f"  X {b}")
sys.exit(1 if bad else 0)
