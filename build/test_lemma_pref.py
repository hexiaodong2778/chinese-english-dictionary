# -*- coding: utf-8 -*-
"""变形词跳转策略回归（2026-10-08 用户反馈）。

反馈原文：搜 chipped，它本身有「有缺口的」的意思、可以作单独词汇使用，
但程序自动跳到了 chip —— 变形还原过于固执。

策略：
  · 变形词本身有独立释义（chipped/saw/running…）→ 展示自己的词条，
    附「原形」提示链接，不再硬跳。
  · 变形词只是「变形指针」（went = go的过去式，没有独立内容）
    → 照旧跳原形拿完整词条。
"""
import os
import sqlite3
import sys
import time

sys.path.insert(0, r"D:\Dictionary\build")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.chdir(r"D:\Dictionary\build")

import app as A

P = F = 0


def chk(name, cond):
    global P, F
    if cond:
        P += 1
        print("PASS", name)
    else:
        F += 1
        print("FAIL", name)


con = A.open_db("dict.db")
assert con is not None, "dict.db 打不开"
eng = A.DictEngine(con)

print("== 1) 有独立释义的变形词：展示自己的词条，不跳原形 ==")
OWN = {
    "chipped": "chip", "running": "run", "better": "well", "best": "good",
    "saw": "see", "thought": "think", "geese": "goose", "happier": "happy",
    "making": "make", "worst": "bad", "gone": "go", "said": "say",
}
for wd, lm in OWN.items():
    d = eng.lookup(wd, "all")
    chk("%-8s 展示自己的词条" % wd,
        d is not None and (d.get("word") or "").lower() == wd)
    chk("%-8s 不带 _from" % wd, d is not None and not d.get("_from"))
    chk("%-8s 带 _lemma=%s 提示" % (wd, lm),
        d is not None and d.get("_lemma") == lm)

print("== 2) 纯变形指针（释义只有「xx的过去式」）：仍跳原形 ==")
JUMP = {
    "went": "go", "took": "take", "ate": "eat", "got": "get",
    "gotten": "get", "been": "be", "was": "be", "mice": "mouse",
    "children": "child", "leaves": "leave",
}
for wd, lm in JUMP.items():
    d = eng.lookup(wd, "all")
    chk("%-8s 跳到 %s" % (wd, lm),
        d is not None and (d.get("word") or "").lower() == lm
        and d.get("_from") == lm)

print("== 3) 普通原形词：不受影响、不带 _lemma ==")
for wd in ["chip", "water", "abandon"]:
    d = eng.lookup(wd, "all")
    chk("%-8s 正常命中" % wd,
        d is not None and (d.get("word") or "").lower() == wd)
    chk("%-8s 不带 _from/_lemma" % wd,
        d is not None and not d.get("_from") and not d.get("_lemma"))

print("== 4) _is_inflect_stub 边界（合成词条，不依赖词库）==")
CASES = [
    ("有独立释义", {"translation": "a. 有缺口的", "definition": ""}, False),
    ("纯过去式指针", {"translation": "go的过去式", "definition": "v ..."}, True),
    ("过去式和过去分词+学科行",
     {"translation": "get的过去式和过去分词\\n[化] 谷草转氨酶", "definition": ""},
     True),
    ("pl. 复数说明", {"translation": "pl. 老鼠", "definition": ""}, True),
    ("真实释义在前指针在后",
     {"translation": "n. 锯子, 谚语\\nsee的过去式", "definition": ""}, False),
    ("空释义空定义", {"translation": "", "definition": ""}, True),
    ("空释义但有定义", {"translation": "", "definition": "n something"}, False),
    ("括号型比较级有真实释义",
     {"translation": "a. 更大的（big的比较级）", "definition": ""}, False),
    ("字面 \\n 两字符也要正确切行",
     {"translation": "eat的过去式\\n[计] 自动测试设备", "definition": ""}, True),
]
for name, row, want in CASES:
    chk("stub 判定：%s" % name, eng._is_inflect_stub(row) is want)

print("== 5) 原形查不到时退回变形词自己的词条（内存库）==")
mem = sqlite3.connect(":memory:")
mem.row_factory = sqlite3.Row
mem.execute("CREATE TABLE dict (word TEXT, lower TEXT, sw TEXT,"
            " translation TEXT, definition TEXT)")
mem.execute("CREATE TABLE lemma (form TEXT, lemma TEXT)")
mem.execute("INSERT INTO dict VALUES ('fooed','fooed','fooed','foo的过去式','')")
mem.execute("INSERT INTO lemma VALUES ('fooed','foo')")  # foo 在 dict 里不存在
e2 = A.DictEngine(mem)
d = e2.lookup("fooed", "all")
chk("退回 stub 词条", d is not None and d.get("word") == "fooed")
chk("不标 _from", d is not None and not d.get("_from"))
mem.close()

print("== 6) 性能：lookup 仍是索引级耗时 ==")
ts = []
WORDS = list(OWN) + list(JUMP)
for _ in range(3):
    t0 = time.perf_counter()
    for wd in WORDS:
        eng.lookup(wd, "all")
    ts.append((time.perf_counter() - t0) * 1000)
med = sorted(ts)[1]
print("  %d 词 x 3 轮，单轮中位 %.1f ms" % (len(WORDS), med))
chk("单轮 < 100ms（每词 < 5ms）", med < 100)

print("== 7) 词条页提示：chipped 给「查看原形」链接，went 给「变形还原」==")
from PySide6.QtWidgets import QApplication
qapp = QApplication.instance() or QApplication([])
w = A.MainWindow()
w._render("chipped", record=False)
html = w.detail.toHtml()
chk("chipped 出现原形提示", "点这里查看原形" in html)
chk("链接指向 word:chip", "word:chip" in html)
chk("chipped 释义在页面上", "有缺口" in html)
w._render("went", record=False)
html = w.detail.toHtml()
chk("went 仍显示变形还原", "变形还原" in html)
chk("went 页面落在 go", ">go</b>" in html or "go" in w.detail.toPlainText().split("\n")[0].lower())

print()
print("RESULT pass=%d fail=%d" % (P, F))
open(r"D:\Dictionary\build\test_lemma_pref.txt", "w", encoding="utf-8").write(
    "pass=%d fail=%d\n" % (P, F))
con.close()
