# -*- coding: utf-8 -*-
"""第二轮定位：把「QApplication + QMediaPlayer 播放」这一段单独拎出来压。

第一轮已排除：裸 os._exit、import app（拉起 Qt）、真实联网合成
—— 三者都能在 0.2~1.8s 内干净退出。

剩下唯一的差异是**播放**：Pronouncer._ensure_player() 会创建
QMediaPlayer + QAudioOutput，且 Pronouncer 没有任何 teardown 接口。

分四组（都带超时）：
  ⑧ 只有 QApplication                    —— 控制组
  ⑤ QApplication + Pronouncer + speak()   —— 是否一播就卡
  ⑥ 同 ⑤ 但走 sys.exit()                 —— 换退出路径
  ⑦ 同 ⑤ 但退出前显式拆掉播放器           —— 收尾能否救回来

如果 ⑧ 能退 / ⑤ 卡 → 凶手锁定在 QMediaPlayer 的 DLL detach。
这就不只是测试问题：**用户关窗口后进程会残留**（部署时 taskkill
一次杀到两个 PID，与此吻合）。
"""
import io
import os
import subprocess
import time

BUILD = r"D:\Dictionary\build"
PY = r"D:\hclaw\python\python.exe"
OUT = os.path.join(BUILD, "_edge_exit_probe2.txt")
LIMIT = 45

L = []


def say(s=""):
    L.append(str(s))
    print(s)


_PRE = ("import sys; sys.path.insert(0, r'%s')\n"
        "import os\n"
        "from PySide6.QtWidgets import QApplication\n"
        "from PySide6.QtCore import QUrl\n"
        "_app = QApplication.instance() or QApplication([])\n") % BUILD

CASES = [
    ("⑧ 只有 QApplication → os._exit(0)",
     _PRE + "os._exit(0)"),
    ("⑤ QApp + Pronouncer.speak → os._exit(0)",
     _PRE + """
import app as A
pr = A.Pronouncer()
try:
    ok = pr.speak("hello", "edge")
    print("speak ->", ok, "src=", getattr(pr, "_last_source", None), flush=True)
except Exception as e:
    print("speak err:", repr(e), flush=True)
os._exit(0)
"""),
    ("⑥ 同⑤ 但走 sys.exit(0)",
     _PRE + """
import app as A
pr = A.Pronouncer()
try:
    ok = pr.speak("hello", "edge")
    print("speak ->", ok, "src=", getattr(pr, "_last_source", None), flush=True)
except Exception as e:
    print("speak err:", repr(e), flush=True)
sys.exit(0)
"""),
    ("⑦ 同⑤ 但退出前显式拆播放器",
     _PRE + """
import app as A
pr = A.Pronouncer()
try:
    ok = pr.speak("hello", "edge")
    print("speak ->", ok, "src=", getattr(pr, "_last_source", None), flush=True)
except Exception as e:
    print("speak err:", repr(e), flush=True)
try:
    pl = getattr(pr, "_player", None)
    if pl is not None:
        pl.stop()
        pl.setSource(QUrl())
        pl.deleteLater()
        print("player torn down", flush=True)
except Exception as e:
    print("teardown err:", repr(e), flush=True)
try:
    _app.processEvents()
except Exception:
    pass
os._exit(0)
"""),
]

env = dict(os.environ)
env["QT_QPA_PLATFORM"] = "offscreen"
env["PYTHONIOENCODING"] = "utf-8"

say("=" * 70)
say("第二轮：QMediaPlayer 播放是否导致退出挂死（每级 %ds）" % LIMIT)
say("=" * 70)

for title, code in CASES:
    t0 = time.perf_counter()
    p = subprocess.Popen([PY, "-c", code], cwd=BUILD, env=env,
                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    try:
        out, _ = p.communicate(timeout=LIMIT)
        el = time.perf_counter() - t0
        txt = (out or b"").decode("utf-8", "replace").strip().replace("\n", " | ")
        say("%-34s 退出 rc=%-3s %6.2fs  %s" % (title, p.returncode, el, txt[:80]))
    except subprocess.TimeoutExpired:
        el = time.perf_counter() - t0
        p.kill()
        try:
            out, _ = p.communicate(timeout=20)
        except Exception:
            out = b""
        txt = (out or b"").decode("utf-8", "replace").strip().replace("\n", " | ")
        say("%-34s ★卡住  >%.0fs    %s" % (title, el, txt[:80]))

say()
say("=" * 70)
say("RESULT OK")
say("=" * 70)

with io.open(OUT, "w", encoding="utf-8") as f:
    f.write("\n".join(L) + "\n")
