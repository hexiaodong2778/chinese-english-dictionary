# -*- coding: utf-8 -*-
"""把打字耗时按函数拆开 —— 判断多出来的 ~1.6ms 是不是我的改动。

纪律：用户的原始投诉是「每键 220~315ms」，现在 5.5ms 本身不影响手感；
但既然测出比昨天的记录（3.9ms）高了，就不能当作噪声挥手带过，
必须指出钱花在哪个函数上、那个函数是不是本轮动过的。
"""
import cProfile
import io
import os
import pstats
import sys
import time

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, r"D:\Dictionary\build")
os.chdir(r"D:\Dictionary\build")

from PySide6.QtWidgets import QApplication

qapp = QApplication(sys.argv[:1])
import app as A

w = A.MainWindow()

WORDS = ["water", "computer", "beautiful", "environment", "happy", "book",
         "time", "hand", "play", "stand", "give", "look", "put", "take",
         "make", "know", "think", "world", "school", "family"]

print("=" * 74)
print("0. 环境 / 用户数据现状（排查「基线不可比」的可能）")
print("=" * 74)
print("   真实用户库 :", w.store.path)
print("   库大小     :", os.path.getsize(w.store.path),
      "bytes" if os.path.exists(w.store.path) else "")
for t in ("history", "words"):
    try:
        n = w.store.con.execute("SELECT COUNT(*) c FROM %s" % t).fetchone()["c"]
        print("   %-10s : %d 行" % (t, n))
    except Exception as e:
        print("   %-10s : <err %s>" % (t, e))

print()
print("=" * 74)
print("1. 逐函数计时（每个词逐字母输入）")
print("=" * 74)
pr = cProfile.Profile()
t0 = time.perf_counter()
pr.enable()
for wd in WORDS:
    for i in range(1, len(wd) + 1):
        w._on_text_now(wd[:i])
pr.disable()
total = time.perf_counter() - t0
print("   %d 次按键共 %.3f s → 平均 %.2f ms/键（含 profiler 开销）"
      % (sum(len(x) for x in WORDS), total, total * 1000 /
         sum(len(x) for x in WORDS)))

buf = io.StringIO()
st = pstats.Stats(pr, stream=buf)
st.sort_stats("cumtime")
st.print_stats(r"app\.py")
lines = buf.getvalue().splitlines()
print()
print("   app.py 内 cumtime 排行前 18：")
for ln in lines:
    if "app.py:" in ln and "{" not in ln:
        print("   " + ln.strip()[:118])

print()
print("=" * 74)
print("2. 本轮新增/改动的函数，在本轮打字中各自被调多少次、花多久")
print("=" * 74)
WATCH = ["_push_undo", "_do_undo", "_sync_undo_btn", "snapshot_history",
         "snapshot_words", "restore_history", "restore_words", "_clear_history",
         "_clear_wordbook", "translate_text", "_same_sentence", "_sim",
         "_norm_sent", "_has_cjk", "_translate_mymemory",
         "_translate_youdao_phrase", "_translate_youdao_example",
         "count_words", "clear_words_group"]
stats = st.stats
found = False
for key, val in stats.items():
    fn = key[2]
    if fn in WATCH:
        cc, nc, tt, ct = val[0], val[1], val[2], val[3]
        found = True
        print("   %-28s 调用 %-5d 自身 %.4fs 累计 %.4fs" % (fn, nc, tt, ct))
if not found:
    print("   （以上函数在打字过程中**一次都没被调用** —— 本轮改动不在打字路径上）")

print()
print("=" * 74)
print("3. _render 内部拆解（本轮唯一动过的地方）")
print("=" * 74)
for key, val in stats.items():
    if key[2] == "_render":
        print("   _render: 调用 %d 次, 自身 %.4fs, 累计 %.4fs, 均摊 %.3f ms"
              % (val[1], val[2], val[3], val[3] / max(1, val[1]) * 1000))
print()
print("DONE")
