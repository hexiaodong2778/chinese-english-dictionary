# -*- coding: utf-8 -*-
"""短语功能回归测试：语法 / phrases() 输出 / 译文清洗 / 渲染链路。"""
import ast
import os
import re
import sqlite3
import sys

sys.path.insert(0, r"D:\Dictionary\build")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

out = []
P = F = 0


def ck(name, cond, extra=""):
    global P, F
    if cond:
        P += 1
        out.append(f"  [PASS] {name}")
    else:
        F += 1
        out.append(f"  [FAIL] {name} {extra}")


src = open(r"D:\Dictionary\build\app.py", encoding="utf-8").read()
try:
    ast.parse(src)
    out.append("[OK] app.py 语法通过\n")
except SyntaxError as e:
    out.append(f"[FAIL] 语法 line {e.lineno}: {e.msg}")
    open(r"D:\Dictionary\build\_regress.txt", "w", encoding="utf-8").write("\n".join(out))
    raise SystemExit(1)

from app import (DictEngine, PHRASE_PARTICLES, PHRASE_SOURCE_NOTE,
                 _clean_phrase_tr)

con = sqlite3.connect(r"D:\Dictionary\dict.db", check_same_thread=False)
con.row_factory = sqlite3.Row
eng = DictEngine(con)

out.append("=== 1. 结构与常量 ===")
ck("PHRASE_PARTICLES 存在且够用", len(PHRASE_PARTICLES) >= 40,
   f"({len(PHRASE_PARTICLES)})")
for p in ("up", "off", "on", "out", "away", "back", "after", "forward"):
    ck(f"粒子表含 {p}", p in PHRASE_PARTICLES)
ck("有出处说明文案", bool(PHRASE_SOURCE_NOTE))
ck("DictEngine 有 phrases 方法", hasattr(eng, "phrases"))
import inspect
sig = inspect.signature(eng.phrases)
ck("phrases 签名为 (word, limit=8)",
   list(sig.parameters) == ["word", "limit"] and sig.parameters["limit"].default == 8,
   str(sig))

out.append("\n=== 2. phrases() 结果质量 ===")
exp = {
    "give": ["give in", "give off", "give out", "give away", "give back"],
    "look": ["look at", "look for", "look after", "look up"],
    "take": ["take in", "take on", "take off", "take away", "take back", "take down"],
    "put": ["put out", "put in", "put on", "put off", "put away", "put down"],
    "come": ["come in", "come on", "come to", "come up"],
    "turn": ["turn on", "turn to", "turn up", "turn off", "turn out"],
    "break": ["break down", "break in", "break up", "break off", "break out"],
    "bring": ["bring in", "bring on", "bring up", "bring out", "bring down"],
    "call": ["call on", "call up", "call for", "call off", "call out"],
    "carry": ["carry on", "carry out", "carry off", "carry over"],
    "keep": ["keep on", "keep up", "keep off", "keep out"],
}
for w, must in exp.items():
    got = [p for p, _ in eng.phrases(w, limit=8)]
    miss = [m for m in must if m not in got]
    ck(f"{w} 命中核心短语", not miss, f"缺 {miss}; 实得 {got}")

out.append("\n=== 3. 默认条数与上限 ===")
for w in ("give", "look", "take", "put", "come"):
    n_def = len(eng.phrases(w))
    ck(f"{w} 默认 <=8 条", n_def <= 8, f"({n_def})")
n3 = eng.phrases("look", limit=3)
ck("limit=3 生效", len(n3) == 3, f"({len(n3)})")
n1 = eng.phrases("look", limit=1)
ck("limit=1 生效", len(n1) == 1, f"({len(n1)})")

out.append("\n=== 4. 垃圾过滤 ===")
bad_flags = []
for w in ("give", "look", "take", "get", "put", "come", "turn", "make", "go",
          "break", "bring", "call", "carry", "hold", "keep", "run", "set"):
    for p, t in eng.phrases(w, limit=8):
        low = p.lower()
        if "..." in p or "\u2026" in p:
            bad_flags.append(f"省略号 {p}")
        if re.search(r"[\u4e00-\u9fff]", p):
            bad_flags.append(f"短语含中文 {p}")
        if len(p) > 26:
            bad_flags.append(f"过长 {p}")
        if len(low.split()) > 3:
            bad_flags.append(f"超3词 {p}")
        if low.split()[0] != w:
            bad_flags.append(f"首词不符 {p} vs {w}")
        if low.split()[1] not in PHRASE_PARTICLES:
            bad_flags.append(f"第二词非粒子 {p}")
        if not re.search(r"[\u4e00-\u9fff]", t):
            bad_flags.append(f"译文无中文 {p}")
        if len(t) > 48:
            bad_flags.append(f"译文过长 {p} ({len(t)})")
        if t != t.strip():
            bad_flags.append(f"译文有首尾空格 {p}")
ck("无垃圾条目", not bad_flags, f"{bad_flags[:6]}")

out.append("\n=== 5. 边界与异常 ===")
for bad in ("", None, "   ", "123", "!!!", "\u4e2d\u6587"):
    try:
        r = eng.phrases(bad)
        ck(f"phrases({bad!r}) 安全返回空", r == [], f"({r})")
    except Exception as e:
        ck(f"phrases({bad!r}) 不抛异常", False, repr(e))
ck("超长输入安全", eng.phrases("a" * 300) == [])
ck("带空格的 'put up with' 不报错", isinstance(eng.phrases("put up with"), list))
try:
    eng2 = DictEngine(None)
    ck("无连接时返回空", eng2.phrases("give") == [])
except Exception as e:
    ck("无连接时不抛异常", False, repr(e))

out.append("\n=== 6. 译文清洗 ===")
cases = [
    ("\\n[\u6cd5] \u653e\u5f03, \u505c\u6b62", "\u653e\u5f03, \u505c\u6b62"),
    ("un. \u6253\u91cf\uff1b\u73af\u987e", "\u6253\u91cf\uff1b\u73af\u987e"),
    ("  ", ""),
    ("", ""),
    ("short", "short"),
]
for raw, want in cases:
    got = _clean_phrase_tr(raw)
    ck(f"清洗 {raw[:16]!r}", got == want, f"got {got!r} want {want!r}")
long_tr = _clean_phrase_tr("\u4e00\u4e8c\u4e09\u56db, " * 8)
ck("超长译文被截断", len(long_tr) <= 40, f"({len(long_tr)} {long_tr!r})")
ck("截断不劈开义项", not long_tr.endswith("\u4e00\u4e8c\u4e09"), repr(long_tr[-6:]))

out.append("\n=== 7. 渲染链路（offscreen GUI）===")
from PySide6.QtWidgets import QApplication
app = QApplication.instance() or QApplication([])
try:
    import app as A
    win = A.MainWindow()
    ck("主窗口创建成功", win is not None)
    htmls = {}
    for w in ("give", "look", "take", "put", "beautiful", "abandon"):
        win._render(w)
        htmls[w] = win.detail.toHtml()
    for w in ("give", "look", "take", "put"):
        h = htmls[w]
        ck(f"{w} 词条含「常用短语」板块", "\u5e38\u7528\u77ed\u8bed" in h)
        ck(f"{w} 短语可点击(phrase:)", "phrase:" in h)
    ck("beautiful 无短语时不显示板块",
       "\u5e38\u7528\u77ed\u8bed" not in htmls["beautiful"])
    ck("abandon 无短语时不显示板块",
       "\u5e38\u7528\u77ed\u8bed" not in htmls["abandon"])
    h = htmls["give"]
    ck("板块顺序：常用短语在例句之前",
       h.find("\u5e38\u7528\u77ed\u8bed") <
       (h.find("\u4f8b\u53e5") if "\u4f8b\u53e5" in h else 10**9))
    ck("板块顺序：常用短语在中文释义之后",
       h.find("\u4e2d\u6587\u91ca\u4e49") < h.find("\u5e38\u7528\u77ed\u8bed"))
    ck("含出处说明", A.PHRASE_SOURCE_NOTE in h or "词库自带固定搭配" in h)
    win.close()
except Exception as e:
    import traceback
    ck("GUI 渲染链路", False, traceback.format_exc()[-500:])

con.close()
s = f"\n{'='*60}\n通过 {P} / 失败 {F}\n{'='*60}\n" + "\n".join(out)
open(r"D:\Dictionary\build\_regress.txt", "w", encoding="utf-8").write(s)
print(f"PASS={P} FAIL={F}")
