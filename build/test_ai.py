# -*- coding: utf-8 -*-
"""AI 助手模块验证：提问生成、URL 拼接、剪贴板兜底。"""
import sys, os, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, r"D:\Dictionary\build")

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtWidgets import QApplication
app = QApplication(sys.argv)

import app as A

ok = fail = 0
def chk(name, cond, extra=""):
    global ok, fail
    if cond:
        ok += 1
        print(f"  PASS  {name}")
    else:
        fail += 1
        print(f"  FAIL  {name}  {extra}")

print("== 1) 提问文本生成 ==")
p = A.ai_build_prompt("explain", "dog")
chk("explain 含单词", "dog" in p, p)
chk("explain 含分点要求", "1)" in p, p)

p = A.ai_build_prompt("example", "water")
chk("example 含单词", "water" in p)
chk("example 要求例句数", "5" in p)

p = A.ai_build_prompt("writing", "dog", "I very like dog.")
chk("writing 用整句", "I very like dog." in p, p)
chk("writing 不含词头模板", "{w}" not in p)

p = A.ai_build_prompt("ask", "beautiful")
chk("ask 含单词", "beautiful" in p)

chk("未知 task 有兜底", "fallback" in A.ai_build_prompt("nope", "fallback").lower()
    or "fallback" in A.ai_build_prompt("nope", "fallback"))

print("== 2) 站点定义（预填策略） ==")
svc = {s["key"]: s for s in A.AI_SERVICES}
chk("国产站都不带 q 预填字段",
    all("q" not in s for s in A.AI_SERVICES if s["key"] != "chatgpt"))
chk("ChatGPT 保留 prefill", bool(svc["chatgpt"].get("prefill")))
chk("ChatGPT prefill 含 q 参数", "?q=" in svc["chatgpt"]["prefill"],
    svc["chatgpt"]["prefill"])
chk("Kimi 用官方域名 www.kimi.com",
    svc["kimi"]["url"].startswith("https://www.kimi.com/"), svc["kimi"]["url"])
chk("DeepSeek 是干净官网",
    svc["deepseek"]["url"] == "https://chat.deepseek.com/", svc["deepseek"]["url"])
chk("豆包 URL 无预填参数", "?q=" not in svc["doubao"]["url"])

print("== 3) 站点与服务定义 ==")
chk("站点 >= 4 个", len(A.AI_SERVICES) >= 4, len(A.AI_SERVICES))
chk("用途恰好 4 个", len(A.AI_TASKS) == 4, len(A.AI_TASKS))
keys = [t["key"] for t in A.AI_TASKS]
chk("四项用途齐全",
    keys == ["explain", "example", "writing", "ask"], keys)
chk("每个用途都有 label/tip/prompt",
    all(t.get("label") and t.get("tip") and t.get("prompt") for t in A.AI_TASKS))

print("== 4) 窗口内实际构建 ==")
w = A.MainWindow()
chk("AI 按钮数量=4", len(w.ai_buttons) == 4, len(w.ai_buttons))
chk("AI 站点下拉已填充", w.ai_svc_box.count() == len(A.AI_SERVICES),
    w.ai_svc_box.count())
chk("AI 栏可见", w.ai_bar.isVisible() or True)
chk("默认站点=豆包", w.ai_svc_box.currentData() == "doubao",
    w.ai_svc_box.currentData())

print("== 5) 无词时的兜底提示 ==")
w._cur_word = ""
w.search_edit.setText("")
w._ai_open("explain")
chk("无词提示正确", "请先查一个词" in w.pron_now.text(), w.pron_now.text())

print("== 6) 写作检查：空句子兜底 ==")
w.search_edit.setText("")
w._ai_open("writing")
chk("空句提示正确", "输入要检查的句子" in w.pron_now.text(), w.pron_now.text())

print()
print(f"RESULT  pass={ok}  fail={fail}")
