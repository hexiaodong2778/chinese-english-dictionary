# -*- coding: utf-8 -*-
"""定位「跑完不退出」的真凶：是 os._exit 卡在 Windows 的 DLL detach，
还是联网合成留下了某个资源。

分四个子进程逐个逼近（每个都带超时，谁能退出、谁卡住，一目了然）：
  ① 什么都不做，直接 os._exit(0)                 —— 基线
  ② import app（拉起 Qt）后 os._exit(0)          —— 是不是 Qt 的锅
  ③ import app + 真实联网合成后 os._exit(0)      —— 是不是 edge 联网的锅
  ④ import app + 联网合成后走正常 sys.exit()     —— 换一条退出路径是否也卡

判读：
  · ① 能退 ② 卡    → Qt 的 DLL detach 死锁（import 就够了）
  · ② 能退 ③ 卡    → 联网合成留下的东西（ws/ssl/线程）
  · ③ 卡 ④ 也卡    → 两条退出路径都卡 → 只能在测试侧收尾资源
"""
import io
import os
import subprocess
import sys
import time

BUILD = r"D:\Dictionary\build"
PY = r"D:\hclaw\python\python.exe"
OUT = os.path.join(BUILD, "_edge_exit_probe.txt")
LIMIT = 60

L = []


def say(s=""):
    L.append(str(s))
    print(s)


# ⚠ `-c` 模式下 sys.path[0] 是 ''（取决于 safe-path 设置），
#   实测 import app 会 ModuleNotFoundError —— 每个片段都必须自己插路径。
_PRE = "import sys; sys.path.insert(0, r'%s')\n" % BUILD

CASES = [
    ("① 裸 os._exit(0)",
     "import os; os._exit(0)"),
    ("② import app 后 os._exit(0)",
     _PRE + "import os; import app; os._exit(0)"),
    ("③ import app + 联网合成 后 os._exit(0)",
     _PRE + """
import os, io
import app as A
try:
    r = A.edge_tts_synth("hello", "en-US-AvaNeural")
    print("synth ok:", len(r) if r else r, flush=True)
except Exception as e:
    print("synth err:", repr(e), flush=True)
os._exit(0)
"""),
    ("④ import app + 联网合成 后正常退出",
     _PRE + """
import os, sys
import app as A
try:
    r = A.edge_tts_synth("hello", "en-US-AvaNeural")
    print("synth ok:", len(r) if r else r, flush=True)
except Exception as e:
    print("synth err:", repr(e), flush=True)
sys.exit(0)
"""),
]

env = dict(os.environ)
env["QT_QPA_PLATFORM"] = "offscreen"
env["PYTHONIOENCODING"] = "utf-8"

say("=" * 70)
say("定位「跑完不退出」：逐级逼近（每级超时 %ds）" % LIMIT)
say("=" * 70)

for title, code in CASES:
    t0 = time.perf_counter()
    p = subprocess.Popen([PY, "-c", code], cwd=BUILD, env=env,
                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    try:
        out, _ = p.communicate(timeout=LIMIT)
        el = time.perf_counter() - t0
        txt = (out or b"").decode("utf-8", "replace").strip().replace("\n", " | ")
        say("%-38s 退出 rc=%-3s %6.2fs   %s" % (title, p.returncode, el, txt[:90]))
    except subprocess.TimeoutExpired:
        el = time.perf_counter() - t0
        p.kill()
        try:
            out, _ = p.communicate(timeout=20)
        except Exception:
            out = b""
        txt = (out or b"").decode("utf-8", "replace").strip().replace("\n", " | ")
        say("%-38s ★卡住   >%.0fs     %s" % (title, el, txt[:90]))

say()
say("=" * 70)
say("RESULT OK")
say("=" * 70)

with io.open(OUT, "w", encoding="utf-8") as f:
    f.write("\n".join(L) + "\n")
