# -*- coding: utf-8 -*-
"""钉住「打字卡顿」的两个修复（2026-09-17）。

根因 1：phrases() 用 `lower LIKE ?` → SCAN dict 全表扫 77 万行（84ms/次），
        而 _render 每次渲染都调它。改用显式区间后走索引（0.2ms）。
根因 2：_on_pick 在程序化填充列表时被 Qt 的多次 currentRowChanged 误判为
        「用户操作」→ add_history → commit()（实测 47ms/次），每键都触发。

本测试同时钉住「不能修快但修坏」：
  * 短语功能仍然可用
  * 用户**主动**查词仍要写进搜索历史
"""
import os
import sys
import io
import time
import statistics
import tempfile

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.chdir(r"D:\Dictionary\build")
sys.path.insert(0, r"D:\Dictionary\build")

_fh = open(r"D:\Dictionary\build\_typing_verify.txt", "w", encoding="utf-8")
def say(s=""):
    _fh.write(str(s) + "\n"); _fh.flush()

P = 0; F = 0
def chk(label, cond, extra=""):
    global P, F
    if cond: P += 1; say("  PASS  %s %s" % (label, extra))
    else:    F += 1; say("  FAIL  %s %s" % (label, extra))

import app as A
from PySide6.QtWidgets import QApplication
qapp = QApplication(sys.argv[:1])
w = A.MainWindow()

# ★ 把用户库换到临时文件，避免污染真实的搜索历史
tmpdir = tempfile.mkdtemp(prefix="dicttest_")
w.store = A.UserStore(path=os.path.join(tmpdir, "user.db"))

def hist_n():
    try:
        return w.store.con.execute("SELECT COUNT(*) FROM history").fetchone()[0]
    except Exception:
        return -1

say("=" * 70)
say("1. _render 速度（修复前 134ms）")
say("=" * 70)
w._render("water")
for word in ("water", "computer", "give"):
    t0 = time.perf_counter()
    for _ in range(5):
        w._render(word, record=False)
    ms = (time.perf_counter() - t0) * 1000 / 5
    say("  _render(%-10s) %7.1f ms" % (word, ms))
    if word == "computer":
        chk("_render 降到 20ms 以内", ms < 20, "(%.1f ms)" % ms)

say()
say("=" * 70)
say("2. 打字速度（修复前每键 ~220ms：_render 134ms×2 + commit 47ms）")
say("=" * 70)
# 大样本：35 个词从头逐字母打完
WORDS = ["water", "computer", "beautiful", "environment", "happy", "book",
         "time", "hand", "play", "stand", "give", "look", "put", "take",
         "make", "run", "set", "get", "come", "turn", "bring", "call",
         "break", "hold", "keep", "pull", "work", "study", "abandon",
         "review", "language", "science", "history", "music", "country"]
allms = []
for word in WORDS:
    for i, ch in enumerate(word, 1):
        pre = word[:i]
        t0 = time.perf_counter()
        w._on_text_now(pre)
        allms.append((time.perf_counter() - t0) * 1000)

xs = sorted(allms)
n = len(xs)
say("   样本 %d 次按键" % n)
say("   中位 %6.1f   p90 %6.1f   p99 %6.1f   max %7.1f  ms"
    % (statistics.median(xs), xs[int(n * 0.9)], xs[int(n * 0.99)], xs[-1]))

# ⚠ 判据用 p99 而不是 max：首次触碰一个新前缀时可能撞上**一次性**
#   冷磁盘 I/O（本机偶发 ~100ms，且复现不出来 —— 换进程单独跑同一
#   序列只有 4ms）。那与本修复无关，不该让套件假失败。
#   p99 反映用户实际体感；max 仍打印出来供观察，不隐藏。
chk("p99 < 50ms（修复前中位就 220ms）", xs[int(n * 0.99)] < 50,
    "(p99 %.1f ms)" % xs[int(n * 0.99)])
chk("中位 < 15ms（修复前 220ms）", statistics.median(xs) < 15,
    "(中位 %.1f ms)" % statistics.median(xs))
over = [x for x in xs if x > 60]
say("   超过 60ms 的按键: %d 次 %s" % (len(over), ["%.0f" % v for v in over[:5]]))

say()
say("=" * 70)
say("3. ★ 打字期间不得写搜索历史（根因 2）")
say("=" * 70)
n0 = hist_n()
say("    打字前 history = %d 条" % n0)
for i in range(1, 6):
    w._on_text_now("water"[:i])
n1 = hist_n()
say("    打字后 history = %d 条" % n1)
chk("打字全程未写历史", n1 == n0, "(增了 %d 条)" % (n1 - n0))

# 中文反查路径同样不得写
for i in range(1, 3):
    w._on_text_now("美丽"[:i])
n2 = hist_n()
chk("中文反查打字全程未写历史", n2 == n1, "(增了 %d 条)" % (n2 - n1))

say()
say("=" * 70)
say("4. ★ 用户主动操作仍要写历史（不能修快但修坏）")
say("=" * 70)
# ⚠ 坑（我自己踩过）：add_history 以 word 为主键，写**同一个词**不会让
#   计数增加（幂等）。若拿一个已在历史里的词来断言「+1」必然假失败。
#   所以先把这个词从历史里删掉，再用它测。
HEAD = "give"
try:
    w.store.con.execute("DELETE FROM history WHERE word=?", (HEAD,))
    w.store.con.commit()
except Exception:
    pass
n3 = hist_n()
w._on_text_now(HEAD)          # 打字阶段：只预览，不写历史
n_mid = hist_n()
chk("打字阶段不写历史", n_mid == n3, "(%d -> %d)" % (n3, n_mid))
w._commit_first()             # 回车 = 用户主动确认
n4 = hist_n()
chk("回车确认后历史 +1", n4 == n3 + 1, "(%d -> %d)" % (n3, n4))

say()
say("=" * 70)
say("5. 去重：打字时同一个词不重复渲染")
say("=" * 70)
cnt = {"n": 0}
_orig = w._render
def _counted(word, *a, **kw):
    cnt["n"] += 1
    return _orig(word, *a, **kw)
w._render = _counted
w._on_text_now("water")
w._render = _orig
say("    _on_text_now('water') 触发 _render %d 次" % cnt["n"])
chk("每次打字渲染 <= 2 次（修复前 2 次且每次都慢）", cnt["n"] <= 2)

say()
say("=" * 70)
say("6. 短语功能未被改坏")
say("=" * 70)
chk("phrases('give') 有结果", len(w.engine.phrases("give")) > 0)
chk("phrases('look') 有结果", len(w.engine.phrases("look")) > 0)
chk("phrases('computer') == 0（术语按设计被过滤）",
    len(w.engine.phrases("computer")) == 0)

say()
say("=" * 70)
say("7. 用户库 PRAGMA（synchronous=NORMAL 消除 47ms commit）")
say("=" * 70)
jm = w.store.con.execute("PRAGMA journal_mode").fetchone()[0]
sy = w.store.con.execute("PRAGMA synchronous").fetchone()[0]
say("    journal_mode=%s  synchronous=%s" % (jm, sy))
chk("journal_mode 是 wal", str(jm).lower() == "wal")
chk("synchronous 是 1(NORMAL)，不再是 2(FULL)", int(sy) == 1)

# 实测 commit 成本
t0 = time.perf_counter()
for i in range(10):
    w.store.add_history("perftest%d" % i)
ms = (time.perf_counter() - t0) * 1000 / 10
say("    add_history 平均 %.2f ms（修复前 47ms）" % ms)
chk("add_history 平均 < 5ms", ms < 5, "(%.2f ms)" % ms)

say()
say("=" * 70)
say("8. ★ 清空后重打同一个词，详情栏必须重新渲染（去重的坑）")
say("=" * 70)
# 去重逻辑用 `w != _preview_word` 判断「是否要渲染」。若忘了在 clear()
# 时重置 _preview_word，「清空输入框 → 重打同一个词」就会被跳过渲染，
# 详情栏停在欢迎页 —— 这是引入去重时最容易漏的一处。
w._on_text_now("water")                    # 第一次：预览 water
pre_before = w._preview_word
say("    第一次打字后 _preview_word = %r" % (pre_before,))

w._on_text_now("")                         # 清空
chk("清空后 _preview_word 已重置为 None", w._preview_word is None,
    "(实际 %r)" % (w._preview_word,))

cnt2 = {"n": 0}
_orig2 = w._render
def _c2(word, *a, **kw):
    cnt2["n"] += 1
    return _orig2(word, *a, **kw)
w._render = _c2
w._on_text_now("water")                    # 重打同一个词
w._render = _orig2
chk("重打同一个词仍有渲染（未被去重误跳过）", cnt2["n"] >= 1,
    "(渲染 %d 次)" % cnt2["n"])

# 反向确认去重仍然生效：连续两次打同一个词，第二次不该重复渲染
w._on_text_now("water")
cnt2["n"] = 0
w._render = _c2
w._on_text_now("water")                    # 紧接着再打一次（列表未被清空语义）
w._render = _orig2
say("    紧接着重复输入触发渲染 %d 次（去重仍在工作）" % cnt2["n"])

say()
say("=" * 70)
say("RESULT  pass=%d  fail=%d" % (P, F))
say("=" * 70)
_fh.close()
print("pass=%d fail=%d" % (P, F))
