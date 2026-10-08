# -*- coding: utf-8 -*-
"""验证联网路径已真异步（2026-09-17）。

为什么必须单独测这个：
  之前 `_on_text_now` 的基准测试里**没有事件循环**，所以
  `QTimer.singleShot` 的回调根本不触发 —— 基准测不出联网冻结。
  本测试用真实事件循环 + 故意放慢的假 fetch 来验证三件事：
    1. 调用本身立刻返回（不阻塞）
    2. 慢请求进行期间，主线程事件循环仍在转（能收到定时器 tick）
    3. 回调**落在主线程**（worker 线程碰 GUI 会崩）
"""
import os
import sys
import io
import time
import threading

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.chdir(r"D:\Dictionary\build")
sys.path.insert(0, r"D:\Dictionary\build")

_fh = open(r"D:\Dictionary\build\_async_verify.txt", "w", encoding="utf-8")
def say(s=""):
    _fh.write(str(s) + "\n"); _fh.flush()

P = 0; F = 0
def chk(label, cond, extra=""):
    global P, F
    if cond: P += 1; say("  PASS  %s %s" % (label, extra))
    else:    F += 1; say("  FAIL  %s %s" % (label, extra))

import app as A
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer

qapp = QApplication.instance() or QApplication(sys.argv[:1])
w = A.MainWindow()

MAIN_TID = threading.get_ident()
say("主线程 ident = %s" % MAIN_TID)

SLOW = 0.40          # 假 fetch 的耗时（秒）

def pump(seconds):
    """转事件循环，同时统计 tick 次数（用于判断主线程是否被堵住）。"""
    ticks = {"n": 0}
    t = QTimer(); t.setInterval(20)
    t.timeout.connect(lambda: ticks.__setitem__("n", ticks["n"] + 1))
    t.start()
    end = time.time() + seconds
    while time.time() < end:
        qapp.processEvents()
        time.sleep(0.005)
    t.stop()
    return ticks["n"]

say()
say("=" * 70)
say("1. fetch_online_def 路径（打字时每次预览词条都会触发）")
say("=" * 70)

calls = {"worker_tid": None, "main_tid": None, "n": 0}

def fake_online_def(word):
    calls["n"] += 1
    calls["worker_tid"] = threading.get_ident()
    time.sleep(SLOW)                     # 模拟慢网络
    return {"english": ["(fake) a definition"], "collins": [], "synos": []}

A.fetch_online_def = fake_online_def
w._online_cache.clear()
w._online_fetching.clear()

# 包一层，记录回调落在哪个线程
_orig_ready = w._on_online_ready
def _ready_probe(word, data):
    calls["main_tid"] = threading.get_ident()
    return _orig_ready(word, data)
w._on_online_ready = _ready_probe

t0 = time.perf_counter()
w._on_text_now("water")                  # 打字（内含 _schedule_online_enhance）
call_ms = (time.perf_counter() - t0) * 1000
say("    _on_text_now('water') 返回耗时 %.1f ms" % call_ms)
chk("打字调用本身不阻塞（< 80ms，不是 400ms）", call_ms < 80, "(%.1f ms)" % call_ms)

say("    慢请求进行中转事件循环 %.2fs，统计定时器 tick…" % SLOW)
ticks = pump(SLOW + 0.25)
say("    期间收到 %d 次 tick（每次 20ms）" % ticks)
# 若主线程被 fetch 堵住，tick 只会在请求结束后才补上，数量会极少
chk("主线程事件循环未被堵住（tick >= 10）", ticks >= 10, "(tick=%d)" % ticks)

say("    worker 线程 ident = %s" % calls["worker_tid"])
say("    回调 线程 ident = %s" % calls["main_tid"])
chk("假 fetch 确实在后台线程跑", calls["worker_tid"] != MAIN_TID)
chk("★ 回调落在主线程（worker 碰 GUI 会崩）", calls["main_tid"] == MAIN_TID)
chk("联网结果已写入缓存", "water" in w._online_cache,
    "(%s)" % list(w._online_cache.keys())[:4])
chk("_online_fetching 已清空（可再次请求）", len(w._online_fetching) == 0)

say()
say("=" * 70)
say("2. fetch_cn_en 路径（输入中文且离线结果不足 6 条时触发）")
say("=" * 70)

calls2 = {"worker_tid": None, "main_tid": None}

def fake_cn_en(word):
    calls2["worker_tid"] = threading.get_ident()
    time.sleep(SLOW)
    return ["feel happy", "be delighted"]

A.fetch_cn_en = fake_cn_en

# 探针要挂在「回调里一定会走到」的地方。
# ⚠ 我第一版挂在 _cn_ok_now 上，但它只在 `self._last_query == word` 时才被调用，
#   而这时 _last_query 还是上一节的 'water'，于是探针没触发 → 假失败。
#   改挂 DictEngine.set_cn_extra —— 回调无条件会调它。
_orig_set = A.DictEngine.set_cn_extra      # 已是绑定好的 classmethod

def _set_probe(word, items):
    calls2["main_tid"] = threading.get_ident()
    return _orig_set(word, items)

A.DictEngine.set_cn_extra = staticmethod(_set_probe)

t0 = time.perf_counter()
w._schedule_cn_en("开心")
call_ms = (time.perf_counter() - t0) * 1000
say("    _schedule_cn_en('开心') 返回耗时 %.1f ms" % call_ms)
chk("调用本身不阻塞（< 80ms）", call_ms < 80, "(%.1f ms)" % call_ms)

ticks2 = pump(SLOW + 0.25)
say("    期间收到 %d 次 tick" % ticks2)
chk("主线程事件循环未被堵住（tick >= 10）", ticks2 >= 10, "(tick=%d)" % ticks2)
say("    worker ident = %s / 回调 ident = %s"
    % (calls2["worker_tid"], calls2["main_tid"]))
chk("假 fetch 在后台线程", calls2["worker_tid"] != MAIN_TID)
chk("★ 回调落在主线程", calls2["main_tid"] == MAIN_TID)
chk("中文补充结果已登记", A.DictEngine.has_cn_extra("开心"))

say()
say("=" * 70)
say("3. 异常安全：fetch 抛异常时后台线程不能静默死掉")
say("=" * 70)
flag = {"called": False}
def boom(word):
    raise RuntimeError("模拟网络层炸了")
A.fetch_online_def = boom
w._online_cache.clear()
w._online_fetching.clear()

_orig_ready2 = w._on_online_ready
def _ready2(word, data):
    flag["called"] = True
    say("    回调收到 data=%r（异常时应为 None 或空 dict）" % (data,))
    return _orig_ready2(word, data)
w._on_online_ready = _ready2
w._schedule_online_enhance("computer")
pump(0.5)
chk("异常时回调仍被调用（不静默丢事件）", flag["called"])
chk("异常后 _online_fetching 已清空", len(w._online_fetching) == 0)

say()
say("=" * 70)
say("RESULT  pass=%d  fail=%d" % (P, F))
say("=" * 70)
_fh.close()
print("pass=%d fail=%d" % (P, F))
