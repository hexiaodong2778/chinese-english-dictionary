# -*- coding: utf-8 -*-
"""跑一批指定测试并汇总 PASS/FAIL（避免本机 Bash 管道不可用）。

用法：python _quick.py test_a.py test_b.py ...
"""
import io
import os
import re
import subprocess
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
# 路径自适应：本脚本所在目录即测试根目录；默认用当前解释器
PY = sys.executable or r"D:\hclaw\python\python.exe"
D = os.path.dirname(os.path.abspath(__file__))

PATS = [
    r"pass(?:ed)?\s*[=:]\s*(\d+)\s*[,;/]?\s*fail(?:ed)?\s*[=:]\s*(\d+)",
    r"RESULT\s+pass\s*=\s*(\d+)\s+fail\s*=\s*(\d+)",
    r"PASS\s*=\s*(\d+)\s+FAIL\s*=\s*(\d+)",
]


def parse(text):
    for p in PATS:
        m = re.search(p, text, re.I)
        if m:
            return int(m.group(1)), int(m.group(2))
    return None, None


names = sys.argv[1:]
tot_p = tot_f = 0
bad = []
for n in names:
    path = os.path.join(D, n)
    if not os.path.exists(path):
        print("%-28s MISSING" % n)
        bad.append(n)
        continue
    try:
        r = subprocess.run([PY, path], cwd=D, capture_output=True,
                           timeout=900)
        out = (r.stdout or b"").decode("utf-8", "replace") + \
              (r.stderr or b"").decode("utf-8", "replace")
    except subprocess.TimeoutExpired:
        print("%-28s TIMEOUT" % n)
        bad.append(n)
        continue
    p, f = parse(out)
    if p is None:
        tb = "Traceback" in out
        print("%-28s rc=%s %s" % (n, r.returncode,
                                  "TRACEBACK!" if tb else "(无计数)"))
        if tb:
            bad.append(n)
            i = out.find("Traceback")
            print("      " + out[i:i + 400].replace("\n", "\n      "))
        continue
    tot_p += p
    tot_f += f
    flag = "" if f == 0 else "   <== 有失败"
    print("%-28s pass=%-5d fail=%-3d%s" % (n, p, f, flag))
    if f:
        bad.append(n)
        for ln in out.splitlines():
            if "FAIL" in ln:
                print("      " + ln.strip()[:120])

print()
print("合计 pass=%d fail=%d   问题脚本=%s" % (tot_p, tot_f, bad or "无"))
with open(os.path.join(D, "_quick_result.txt"), "w", encoding="utf-8") as fh:
    fh.write("pass=%d fail=%d bad=%s\n" % (tot_p, tot_f, bad))
