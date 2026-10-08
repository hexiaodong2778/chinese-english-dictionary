# -*- coding: utf-8 -*-
"""验证 AI 服务列表（剪贴板方案）配置正确。"""
import io
import os
import sys

os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.chdir(r"D:\Dictionary")
sys.path.insert(0, r"D:\Dictionary\build")
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

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

print("== 1. AI_SERVICES 列表 ==")
srv = A.AI_SERVICES
print(f"  共 {len(srv)} 个站点")
for s in srv:
    kind = "预填" if s.get("prefill") else "官网+剪贴板"
    print(f"    {s['label']:12} {s['url']}  [{kind}]")

chk("共 7 个 AI 站点", len(srv) == 7, len(srv))
keys = [s["key"] for s in srv]
chk("含豆包", "doubao" in keys, keys)
labels = [s["label"] for s in srv]
chk("豆包排第一", labels[0] == "豆包", labels)
chk("豆包 URL 正确", any(
    s["key"] == "doubao" and s["url"] == "https://www.doubao.com/chat/"
    for s in srv))
chk("国产站不带 q 字段", all(
    "q" not in s for s in srv if s["key"] != "chatgpt"))
chk("ChatGPT 有 prefill", any(
    s["key"] == "chatgpt" and "{q}" in s.get("prefill", "") for s in srv))
chk("Kimi 用官方域名", any(
    s["key"] == "kimi" and s["url"].startswith("https://www.kimi.com/")
    for s in srv))
chk("所有 URL 都是 https", all(
    s["url"].startswith("https://") for s in srv))

print("\n== 2. 下拉框 ==")
w = A.MainWindow()
chk("下拉框项数 = 7", w.ai_svc_box.count() == 7, w.ai_svc_box.count())
items = [w.ai_svc_box.itemText(i) for i in range(w.ai_svc_box.count())]
chk("下拉框含豆包", "豆包" in items, items)
chk("默认站点=豆包", w.ai_svc_box.currentData() == "doubao",
    w.ai_svc_box.currentData())
print(f"  下拉框项: {items}")

print("\n== 3. 每个站点点击后都复制剪贴板 + 打开 ==")
import PySide6.QtGui as QG
calls = []
orig = QG.QDesktopServices.openUrl
try:
    QG.QDesktopServices.openUrl = staticmethod(
        lambda u: calls.append(u.toString()) or True)
    w.search_edit.setText("beautiful")
    app.processEvents()
    for i in range(w.ai_svc_box.count()):
        w.ai_svc_box.setCurrentIndex(i)
        svc = srv[i]
        if svc.get("internal"):
            print(f"  SKIP  {svc['label']} 为站内模式，需配置 API Key")
            continue
        calls.clear()
        QApplication.clipboard().setText("")
        w.ai_buttons[0].click()          # AI 释义讲解
        name = w.ai_svc_box.itemText(i)
        if calls:
            u = calls[0]
            good = u.startswith("https://")
            chk(f"{name} 生成有效 URL", good, u[:110])
        else:
            chk(f"{name} 生成 URL", False, "未触发")
        clip = QApplication.clipboard().text()
        chk(f"{name} 提问已复制剪贴板", "beautiful" in clip, clip[:60])
finally:
    QG.QDesktopServices.openUrl = orig

print("\n== 4. 剪贴板方案对所有站生效 ==")
chk("点击后提示含粘贴/Ctrl+V 或预填",
    "粘贴" in w.pron_now.text() or "Ctrl+V" in w.pron_now.text()
    or "预填" in w.pron_now.text(), w.pron_now.text())

print(f"\n通过 {ok}，失败 {len(bad)}")
for b in bad:
    print(f"  X {b}")
sys.exit(1 if bad else 0)
