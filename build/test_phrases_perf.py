# -*- coding: utf-8 -*-
"""验证 phrases() 性能修复：语法 / 等价性 / 速度 / _render 端到端。"""
import os, sys, io, time, sqlite3, py_compile
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.chdir(r"D:\Dictionary\build")
sys.path.insert(0, r"D:\Dictionary\build")

_fh = open(r"D:\Dictionary\build\_fix_verify.txt", "w", encoding="utf-8")
def say(s=""):
    _fh.write(str(s) + "\n"); _fh.flush()

P = 0; F = 0
def chk(label, cond, extra=""):
    global P, F
    if cond: P += 1; say("  PASS  %s %s" % (label, extra))
    else:    F += 1; say("  FAIL  %s %s" % (label, extra))

say("=" * 70)
say("1. 语法检查")
say("=" * 70)
try:
    py_compile.compile(r"D:\Dictionary\build\app.py", doraise=True)
    chk("app.py 编译通过", True)
except Exception as e:
    chk("app.py 编译通过", False, repr(e)[:120])
    _fh.close(); sys.exit(1)

say()
say("=" * 70)
say("2. 等价性 + 速度：新写法 vs 旧写法")
say("=" * 70)

con = sqlite3.connect(r"D:\Dictionary\build\dict.db")
con.row_factory = sqlite3.Row

Q_OLD = ("SELECT word, translation, collins, oxford FROM dict "
         "WHERE lower LIKE ? AND word LIKE '% %' AND translation!='' LIMIT 400")
Q_NEW = ("SELECT word, translation, collins, oxford FROM dict "
         "INDEXED BY idx_dict_lower "
         "WHERE lower >= ? AND lower < ? "
         "AND word LIKE '% %' AND translation!='' LIMIT 400")

WORDS = ["computer", "water", "give", "look", "put", "take", "make", "go",
         "run", "set", "get", "come", "turn", "bring", "call", "break",
         "hold", "keep", "pull", "work", "café", "naïve", "happy", "book",
         "time", "hand", "play", "stand", "cut", "fall"]

say()
say("  逐词对比（行数 + 集合是否完全一致）:")
same_all = True
slow_tot = 0.0; fast_tot = 0.0
for w in WORDS:
    old = con.execute(Q_OLD, (w + " %",)).fetchall()
    new = con.execute(Q_NEW, (w + " ", w + " \uffff")).fetchall()
    so = [r["word"] for r in old]
    sn = [r["word"] for r in new]
    ok = (so == sn)
    if not ok:
        same_all = False
        say("    ✗ %-10s 旧 %d / 新 %d  差异: %s" %
            (w, len(so), len(sn),
             sorted(set(so) ^ set(sn))[:5]))

    # 计时
    n = 5
    t0 = time.perf_counter()
    for _ in range(n): con.execute(Q_OLD, (w + " %",)).fetchall()
    slow_tot += (time.perf_counter() - t0) * 1000 / n
    t0 = time.perf_counter()
    for _ in range(n): con.execute(Q_NEW, (w + " ", w + " \uffff")).fetchall()
    fast_tot += (time.perf_counter() - t0) * 1000 / n

say()
chk("全部 %d 个词结果逐条完全一致（含顺序）" % len(WORDS), same_all)
say("    旧写法合计 %8.1f ms    新写法合计 %8.1f ms    加速 %.1f 倍"
    % (slow_tot, fast_tot, slow_tot / max(fast_tot, 1e-9)))

say()
say("  查询计划（新写法）:")
for p in con.execute("EXPLAIN QUERY PLAN " + Q_NEW, ("computer ", "computer \uffff")):
    say("    %s" % p[-1])
    chk("走索引 idx_dict_lower", "idx_dict_lower" in p[-1])
    chk("不再是 SCAN dict", "SCAN dict" not in p[-1])

say()
say("=" * 70)
say("3. _render 端到端（修复前 134ms）")
say("=" * 70)

import app as A
from PySide6.QtWidgets import QApplication
qapp = QApplication(sys.argv[:1])
w = A.MainWindow()
w._render("water")   # 预热

for word in ("water", "computer", "beautiful", "happy", "give"):
    t0 = time.perf_counter()
    for _ in range(5):
        w._render(word, record=False)
    ms = (time.perf_counter() - t0) * 1000 / 5
    say("  _render(%-10s) %8.1f ms" % (word, ms))
    if word == "computer":
        chk("_render 降到 20ms 以内", ms < 20, "(%.1f ms)" % ms)

say()
say("=" * 70)
say("4. 模拟打字 'water'（修复前每键 ~220ms）")
say("=" * 70)
for i, ch in enumerate("water", 1):
    pre = "water"[:i]
    t0 = time.perf_counter()
    w._on_text_now(pre)
    ms = (time.perf_counter() - t0) * 1000
    say("  输入 '%-6s' _on_text_now %8.1f ms" % (pre, ms))
    if i == 5:
        chk("最后一键 < 30ms", ms < 30, "(%.1f ms)" % ms)

say()
say("=" * 70)
say("5. 短语功能仍然正常（不能修快但修坏）")
say("=" * 70)
ph = w.engine.phrases("give")
chk("phrases('give') 有结果", len(ph) > 0, "(%d 条)" % len(ph))
say("    前 5 条: %s" % [(x[0] if isinstance(x, (list, tuple)) else x) for x in ph[:5]])

# ⚠ 这条断言我之前写错了：phrases('computer') == 0 是**设计如此**。
#   phrases() 的 docstring 明确说「第二词必须是小品词或常用介词 ——
#   这一条过滤掉了 'break address'、'call analyzer' 这类术语」。
#   而 SQL 层确实返回了 193 条（含 'computer address' 等），
#   是后面的评分/过滤把它们全部剔除，属于正确行为。
ph2 = w.engine.phrases("computer")
chk("phrases('computer') 为 0（术语被 docstring 所述规则过滤，属设计行为）",
    len(ph2) == 0, "(%d 条)" % len(ph2))

# 反向确认：SQL 层确实拿得到候选，说明「0 条」是过滤结果而非查询失败
raw = con.execute(
    "SELECT COUNT(*) FROM dict INDEXED BY idx_dict_lower "
    "WHERE lower >= ? AND lower < ? AND word LIKE '% %' AND translation!=''",
    ("computer ", "computer \uffff")).fetchone()[0]
chk("SQL 层对 computer 仍有 %d 条候选（证明 0 条是过滤而非查不到）" % raw, raw > 0)

# 再补一个确实有短语的词，确认通用性
ph3 = w.engine.phrases("look")
chk("phrases('look') 有结果", len(ph3) > 0, "(%d 条)" % len(ph3))
say("    前 5 条: %s" % [(x[0] if isinstance(x, (list, tuple)) else x) for x in ph3[:5]])

say()
say("=" * 70)
say("RESULT  pass=%d  fail=%d" % (P, F))
say("=" * 70)
_fh.close()
print("pass=%d fail=%d" % (P, F))
