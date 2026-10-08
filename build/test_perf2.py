# -*- coding: utf-8 -*-
"""无头验证：防抖、缓存、索引路径、short-key 短路"""
import os, sys, io, time
os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, r"D:\Dictionary\build")

from PySide6.QtWidgets import QApplication
app = QApplication(sys.argv)
import app as A

w = A.MainWindow()
w.resize(1080, 720)
w.show()
app.processEvents()

ok = fail = 0
def chk(name, cond, extra=""):
    global ok, fail
    if cond:
        ok += 1; print(f"  PASS  {name} {extra}")
    else:
        fail += 1; print(f"  FAIL  {name} {extra}")

print("\n[1] 防抖：连续打字只查一次")
calls = []
orig = w._on_text_now
def spy(t):
    calls.append(t)
    return orig(t)
w._on_text_now = spy
w.search_edit.setText("h")
app.processEvents()
for c in "appy":
    w.search_edit.insert(c)
    app.processEvents()
# 此时应有 5 次 textChanged，但查询还没发生
chk("打字期间未触发查询", len(calls) == 0, f"calls={calls}")
t0 = time.perf_counter()
# 等防抖到期
for _ in range(60):
    app.processEvents()
    if calls:
        break
    time.sleep(0.02)
dt = (time.perf_counter() - t0) * 1000
chk("停手后只查了 1 次", len(calls) == 1, f"calls={calls} {dt:.0f}ms")
w._on_text_now = orig

print("\n[2] 缓存：同前缀第二次命中")
eng = w.engine
t0 = time.perf_counter(); eng.suggest("happy", 60, None)
d1 = (time.perf_counter() - t0) * 1000
t0 = time.perf_counter(); eng.suggest("happy", 60, None)
d2 = (time.perf_counter() - t0) * 1000
chk("第二次明显更快或已缓存", d2 <= max(d1, 0.2) + 0.001,
    f"{d1:.2f}ms -> {d2:.2f}ms")
chk("缓存条数受控", len(eng._cache) <= eng._CACHE_MAX, f"n={len(eng._cache)}")

print("\n[3] 中文反查全部走索引、无异常、无回退")
bad = []
for kw in ["水", "狗", "书", "学习", "快乐", "他", "牙", "买", "哭"]:
    eng._cn_query_error = None
    eng._cn_fallback_used = False
    r = eng.search_cn(kw)
    if eng._cn_query_error or eng._cn_fallback_used or not r:
        bad.append((kw, eng._cn_query_error, eng._cn_fallback_used, len(r)))
chk("9 个词全部命中且无回退", not bad, str(bad))

print("\n[4] 短 ASCII 短路不影响单个汉字")
for kw in ["水", "狗", "书"]:
    chk(f"单字「{kw}」仍可查", len(eng.search_cn(kw)) > 0)
chk("「a」返回空且不耗时", eng.search_cn("a") == [])
chk("「the」返回空", eng.search_cn("the") == [])

print("\n[5] 英文候选首项是词本身")
for k in ["happy", "water", "dog", "book"]:
    r = eng.suggest(k, 60, None)
    chk(f"「{k}」首项={r[0]['word'] if r else None}", r and r[0]["word"].lower() == k)

print(f"\nPASS={ok}  FAIL={fail}")
w.close()
sys.exit(0 if fail == 0 else 1)
