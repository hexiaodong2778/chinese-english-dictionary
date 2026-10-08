# -*- coding: utf-8 -*-
"""决定性测量：test_edge_tts.py 到底是「慢」还是「跑完不退出」。

背景：全量回归里 test_edge_tts.py 恒被标「真失败(超时)」，
但单独跑时输出文件里明明写着 PASS=60 FAIL=0 ——
所以要么它很慢，要么它跑完卡在退出阶段。两者修法完全不同，
不能猜，必须量：
  · 脚本正文用 -u（无缓冲）→ 能看出**最后一次进度**停在哪个环节
  · 外层 wait(timeout=N) → 能分出「N 秒内退出」vs「仍在跑」
  · 退出后再确认 os._exit 是否真的生效

★ 关键设计：stdout 走**文件**而不是管道。
   管道会引入「孙子进程持有管道导致 communicate() 等不到 EOF」的
   经典假死；走文件就排除了这个变量，测的是脚本自己的退出行为。
"""
import os
import subprocess
import sys
import time

BUILD = r"D:\Dictionary\build"
PY = r"D:\hclaw\python\python.exe"
OUT = os.path.join(BUILD, "_edge_hang.txt")
LIMIT = 420          # 给足 7 分钟：够它跑完，又不至于陪着挂到天亮


def say(s):
    print(s)
    with open(OUT, "a", encoding="utf-8") as f:
        f.write(str(s) + "\n")


open(OUT, "w", encoding="utf-8").close()

env = dict(os.environ)
env["QT_QPA_PLATFORM"] = "offscreen"
env["PYTHONIOENCODING"] = "utf-8"

say("=" * 66)
say("测 test_edge_tts.py：慢 还是 卡在退出？（上限 %ds）" % LIMIT)
say("=" * 66)

t0 = time.perf_counter()
with open(os.path.join(BUILD, "_edge_progress.txt"), "wb") as wf:
    p = subprocess.Popen([PY, "-u", "test_edge_tts.py"], cwd=BUILD,
                         env=env, stdout=wf, stderr=subprocess.STDOUT)
    try:
        rc = p.wait(timeout=LIMIT)
        el = time.perf_counter() - t0
        say("★ 结果：**正常退出** rc=%s，耗时 %.1fs" % (rc, el))
        verdict = "慢但会退出"
    except subprocess.TimeoutExpired:
        el = time.perf_counter() - t0
        say("★ 结果：**仍存活**，%.1fs 内没退出 → 卡住" % el)
        alive = p.poll() is None
        say("   poll()=%r（None 表示进程还在）" % p.poll())
        p.kill()
        p.wait(timeout=30)
        say("   已 kill，kill 后 rc=%r" % p.returncode)
        verdict = "跑完/跑到某处后不退出"

say("")
say("--- 进度文件最后一次输出（-u 无缓冲，末行=真正停住的地方）---")
try:
    s = open(os.path.join(BUILD, "_edge_progress.txt"),
             encoding="utf-8", errors="replace").read()
    ls = [l for l in s.splitlines() if l.strip()]
    say("   共 %d 行，末 12 行：" % len(ls))
    for l in ls[-12:]:
        say("     " + l[:150])
except OSError as e:
    say("   读不到进度文件: %r" % (e,))

say("")
say("判定：%s" % verdict)
say("RESULT OK")
