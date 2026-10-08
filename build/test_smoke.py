# -*- coding: utf-8 -*-
"""部署前冒烟测试：源码版各关键路径自检。"""
import sys, os, io, re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, r"D:\Dictionary\build")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
app = QApplication(sys.argv)
import app as A

ok = fail = 0
def chk(n, c, e=""):
    global ok, fail
    if c: ok += 1; print(f"  PASS  {n}")
    else: fail += 1; print(f"  FAIL  {n}  {e}")

w = A.MainWindow()

print("== 汉译英：核心词都要排第一 ==")
# ⚠ 这几个词覆盖了一个曾经真实存在的 bug（2026-09-17 修复）：
#   cn_sense.sense 存的是释义原样切分结果，beautiful 被索引到「美丽的」
#   名下，等值查询 `sense='美丽'` 直接把它漏掉，于是查「美丽」出来的
#   全是 fairness / loveliness 这类生僻词。全表 9.3% 的义项以「的」结尾。
#   修法：查询时把「去后缀变体」一并查（走 IN，仍是索引等值查询）。
#   加 "美丽" 与 "漂亮" 就是为了钉住这个修复 —— 它们曾经失败过。
for zh, want in [("狗","dog"),("猫","cat"),("书","book"),("水","water"),
                 ("学习","study"),("跑","run"),("电脑","computer"),
                 ("美丽","beautiful"),("漂亮","pretty"),
                 ("环境","environment"),("放弃","abandon")]:
    rows = w.engine.search_cn(zh)
    got = rows[0]["word"] if rows else None
    chk(f"{zh} → {want}", got == want, f"实际={got}")

print("== 自动方向识别 ==")
chk("中文→cn2en", A.MainWindow.detect_direction("狗") == "cn2en")
chk("英文→en2cn", A.MainWindow.detect_direction("dog") == "en2cn")
chk("中英混合→cn2en", A.MainWindow.detect_direction("dog狗") == "cn2en")
chk("空串→en2cn", A.MainWindow.detect_direction("") == "en2cn")

print("== 输入中文实际走反查 ==")
# ⚠ 坑：_on_text 只更新方向提示，真正的查询丢进 220ms 防抖定时器
#   （为了打字不卡顿）。直接调 _on_text 之后立刻读 result_list 必然是空的
#   —— 这不是 bug，是防抖还没到期。测试要调 _on_text_now（定时器到期后
#   真正执行的那个函数），或把事件循环转够时间。
w.search_edit.setText("狗")
w._on_text_now("狗")
n_cn = w.result_list.count()
chk("中文有反查结果", n_cn > 0, n_cn)
chk("提示为中文反查", "中文反查" in w.list_hint.text(), w.list_hint.text())
first = w.result_list.item(0).data(Qt.UserRole) if n_cn else None
chk("首条是 dog", first == "dog", first)

print("== 防抖：_on_text 应推迟查询而非同步执行 ==")
w.search_edit.setText("")
w._on_text_now("")
w.result_list.clear()
w._on_text("water")
chk("_on_text 后立即读列表为空（防抖未到期）",
    w.result_list.count() == 0, w.result_list.count())
chk("防抖定时器已启动", w._query_timer.isActive())
w._on_text_now("water")          # 手动模拟定时器到期
chk("到期后才有候选", w.result_list.count() > 0, w.result_list.count())

print("== 点击结果渲染完整词条 ==")
w._render("dog")
html = w.detail.toPlainText()
chk("含音标", "/" in html)
chk("含中文释义", len(html) > 100, len(html))
chk("_cur_word=dog", w._cur_word == "dog", w._cur_word)

print("== 输入英文走常规查词 ==")
w.search_edit.setText("water")
w._on_text_now("water")
chk("英文有候选", w.result_list.count() > 0, w.result_list.count())
chk("提示为候选词", "候选词" in w.list_hint.text(), w.list_hint.text())

print("== AI 栏已就位 ==")
chk("4 个 AI 按钮", len(w.ai_buttons) == 4, len(w.ai_buttons))
chk("AI 站点下拉", w.ai_svc_box.count() == len(A.AI_SERVICES), w.ai_svc_box.count())

print("== 发音引擎 ==")
chk("TTS 可用", w.pron._ensure_tts() is not None)
chk("有可用语音", len(w.pron.available_voices()) >= 0)
chk("Edge 口音表非空", len(A.EDGE_ACCENTS) >= 10, len(A.EDGE_ACCENTS))
chk("Edge 音标不再参与合成（_ipa_to_words 已移除）",
    not hasattr(A.Pronouncer, "_ipa_to_words"))

print()
print(f"RESULT  pass={ok}  fail={fail}")
sys.exit(1 if fail else 0)
