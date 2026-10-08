# -*- coding: utf-8 -*-
"""联网同义词补充的排序与渲染回归测试。

── 本轮（2026-09-17）修的两个 bug ──

【bug 1】列表重复渲染
  `_show_cn_results()` 没有自己 `clear()`，而是假定调用方已经清过。
  初次输入那条路径没问题（`_on_text_now` 里 clear 过），
  但**联网补充回来后的重渲染**是在一个已填满的列表上再 addItem 一遍。
  实测查「开心」列表变成 7 条（引擎只返回 6 条），chuffed 重复出现：
      ['chuffed','rejoice','joyful','chuffed','happy','grand','delighted']
  修法：把 clear() 放进 _show_cn_results 内部，两条路径都自洽。

【bug 2】短语末词被误降档
  `_rows_for_english()` 把「从多词短语里提取出来的词」一律标记为非
  direct，排序时降一档（weak_extra）。这个降档本身是对的 ——
  它防止 have a grand time → grand 这种「成分」抢到前面。
  但它同时误伤了 feel happy → happy、be delighted → delighted：
  这两个短语里 feel / be 只是功能词，**末词才是译法主体**。
  结果查「开心」时 happy 被降到第 5 位，前面是 rejoice / joyful / chuffed
  这些生僻词 —— 而 happy 才是用户真正想要的答案。
  修法：加「末词豁免」—— 命中的词若是该短语的最后一个词，就不降档。
        这恰好把「功能动词+形容词」与「动词+宾语」两种短语分开，
        无需引入词性分析。
"""
import os
import sys
import time

sys.path.insert(0, r"D:\Dictionary\build")
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.chdir(r"D:\Dictionary\build")

from PySide6.QtWidgets import QApplication

qapp = QApplication(sys.argv)
import app as A

PASS, FAIL = [], []


def chk(name, cond, detail=""):
    if cond:
        PASS.append(name + ("  [%s]" % detail if detail else ""))
    else:
        FAIL.append(name + ("  → %s" % detail if detail else ""))


con = A.open_db(r"D:\Dictionary\dict.db")
eng = A.DictEngine(con, "en")

# 模拟有道的 ce 词表对「开心」的返回（实测值）
SYN = ["feel happy", "be delighted", "have a grand time", "joyful", "rejoice"]

# ── 1. 末词豁免：正确的词进 direct，短语成分不进 ────────────────────────
rows, direct = eng._rows_for_english(SYN)
words = [r["word"] for r in rows]
chk("extra 行含 happy / delighted / grand / joyful / rejoice",
    {"happy", "delighted", "grand", "joyful", "rejoice"} <= set(words),
    str(words))

chk("feel happy → happy 是末词，进 direct（不降档）", "happy" in direct,
    "direct=%s" % sorted(direct))
chk("be delighted → delighted 是末词，进 direct", "delighted" in direct)
chk("have a grand time → grand 不是末词，**不**进 direct",
    "grand" not in direct, "direct=%s" % sorted(direct))
chk("整串命中的 joyful / rejoice 仍在 direct",
    {"joyful", "rejoice"} <= direct)

# ── 2. 「开心」的引擎层排序：happy 必须第一 ────────────────────────────
A.DictEngine._cn_extra["开心"] = SYN
eng._cache.clear()
rows = eng.search_cn("开心")
order = [r["word"] for r in rows]
chk("查「开心」首条是 happy", order and order[0] == "happy", order)
chk("happy 在 delighted 之前（两者都是末词豁免）",
    "happy" in order and "delighted" in order
    and order.index("happy") < order.index("delighted"), order)
chk("grand（短语成分）没有排到前列",
    "grand" not in order[:2], order)
chk("结果无重复词", len(order) == len(set(order)), order)

# ── 3. GUI 层：列表不重复渲染 ──────────────────────────────────────────
w = A.MainWindow()
w.resize(1080, 720)
w.show()
qapp.processEvents()
A.DictEngine._cn_extra.clear()
w.search_edit.setText("开心")
w._flush_query()

t0 = time.time()
while time.time() - t0 < 15:
    qapp.processEvents()
    if A.DictEngine.has_cn_extra("开心"):
        break
    time.sleep(0.1)
for _ in range(25):
    qapp.processEvents()
    time.sleep(0.05)

gui = [w.result_list.item(i).data(A.Qt.UserRole)
       for i in range(w.result_list.count())]
chk("GUI 列表无重复项", len(gui) == len(set(gui)),
    "重复: %s" % [x for x in set(gui) if gui.count(x) > 1])
chk("GUI 列表条数 == 引擎返回条数",
    len(gui) == len(eng.search_cn("开心")),
    "GUI=%d 引擎=%d" % (len(gui), len(eng.search_cn("开心"))))
chk("GUI 首条是 happy", gui and gui[0] == "happy", gui[:4])
chk("list_hint 条数与列表一致",
    str(len(gui)) in w.list_hint.text(), w.list_hint.text())

# 再触发一次重渲染（模拟联网回调再次刷新）—— 仍不应重复
w._show_cn_results("开心")
qapp.processEvents()
again = [w.result_list.item(i).data(A.Qt.UserRole)
         for i in range(w.result_list.count())]
chk("重复调用 _show_cn_results 不叠加（幂等）",
    len(again) == len(gui), "首次 %d → 再次 %d" % (len(gui), len(again)))

# ── 4. 无回归：其它中文词仍正确 ────────────────────────────────────────
for zh, want in (("狗", "dog"), ("水", "water"), ("书", "book"),
                 ("美丽", "beautiful"), ("漂亮", "pretty"),
                 ("电脑", "computer"), ("学习", "study"),
                 ("环境", "environment"), ("放弃", "abandon")):
    r = eng.search_cn(zh)
    got = r[0]["word"] if r else None
    chk("回归：查「%s」首条 = %s" % (zh, want), got == want, got)

# ── 5. 无回归：英文查词不受影响 ────────────────────────────────────────
for kw in ("happy", "water", "dog"):
    sug = [x["word"] if isinstance(x, dict) else x
           for x in eng.suggest(kw, 3)]
    chk("回归：suggest(%r) 首项是自己" % kw,
        sug and sug[0].lower() == kw, str(sug[:3]))

w.close()

print("PASS=%d FAIL=%d" % (len(PASS), len(FAIL)))
for x in PASS:
    print("  PASS ", x)
for x in FAIL:
    print("  FAIL ", x)
sys.exit(1 if FAIL else 0)
