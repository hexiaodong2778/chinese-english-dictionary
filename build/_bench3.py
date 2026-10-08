# -*- coding: utf-8 -*-
"""连跑 3 次打字基准，看分布波动 —— 判断 5.2ms 是「我的改动」还是噪声。

背景：用户明确警告「别又让它变卡了」。结构上打字路径没动过
（已用插桩证明 snapshot/undo 零调用），但「结构上没动」不等于
「实测没变」，所以必须用重复测量把噪声区间量出来。
"""
import io
import os
import re
import shutil
import subprocess
import sys
import time

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
PY = r"D:\hclaw\python\python.exe"
D = r"D:\Dictionary\build"
BENCH = os.path.join(D, "_trash_20260917", "_bench.py")
OUT = os.path.join(D, "_bench.txt")

rows = []
for i in range(3):
    t0 = time.perf_counter()
    subprocess.run([PY, BENCH], cwd=D, capture_output=True, timeout=900)
    dur = time.perf_counter() - t0
    if not os.path.exists(OUT):
        print("run %d: 没有产出" % (i + 1))
        continue
    txt = open(OUT, encoding="utf-8", errors="replace").read()
    shutil.copy2(OUT, os.path.join(D, "_bench_run%d.txt" % (i + 1)))

    def grab(pat):
        m = re.search(pat, txt)
        return tuple(float(x) for x in m.groups()) if m else (None,) * 4

    a = grab(r"all keystrokes\s+n=\d+\s+中位\s+([\d.]+)\s+p90\s+([\d.]+)\s+"
             r"p99\s+([\d.]+)\s+max\s+([\d.]+)")
    b = grab(r"second pass\s+n=\d+\s+中位\s+([\d.]+)\s+p90\s+([\d.]+)\s+"
             r"p99\s+([\d.]+)\s+max\s+([\d.]+)")
    over = re.search(r"超过 30ms 的按键:\s*\n(.*?)(?:\n\n|$)", txt, re.S)
    ov = (over.group(1).strip().replace("\n", " | ") if over else "?")
    rows.append((a, b))
    print("run %d (%.0fs)  全部: 中位%-5s p90%-5s p99%-5s max%-6s" % (
        i + 1, dur, *["%.1f" % x if x else "-" for x in a]))
    print("           热第二轮: 中位%-5s p90%-5s p99%-5s max%-5s"
          % tuple(["%.1f" % x if x else "-" for x in b]))
    print("           >30ms: %s" % ov[:120])

if rows:
    meds = [r[0][0] for r in rows if r[0][0]]
    hot = [r[1][0] for r in rows if r[1][0]]
    print()
    if meds:
        print("全部按键 中位: 各次 %s" % ["%.1f" % x for x in meds])
        print("  → 最小值 %.1f  最大值 %.1f  极差 %.1f ms"
              % (min(meds), max(meds), max(meds) - min(meds)))
    if hot:
        print("热第二轮 中位: 各次 %s" % ["%.1f" % x for x in hot])
        print("  → 最小值 %.1f  最大值 %.1f" % (min(hot), max(hot)))
    print()
    print("上一版基线（2026-09-17 记录）：全部中位 3.9 / 热第二轮中位 3.0")

print()
print("DONE")
