# -*- coding: utf-8 -*-
"""端到端启动验证（结果自己写文件，避免管道转码问题）。"""
import os
import subprocess
import time

EXE = r"D:\Dictionary\查单词.exe"
LOGDIR = r"D:\Dictionary"
out = []

out.append(f"exe  = {EXE}")
out.append(f"size = {os.path.getsize(EXE):,} bytes")

before = set(os.listdir(LOGDIR))
out.append(f"启动前文件数: {len(before)}")

p = subprocess.Popen([EXE], cwd=LOGDIR,
                     stdout=subprocess.PIPE, stderr=subprocess.PIPE)
out.append(f"已启动 PID = {p.pid}")
time.sleep(8)

alive = p.poll() is None
out.append(f"8 秒后仍在运行: {alive}")
if not alive:
    try:
        o, e = p.communicate(timeout=5)
        out.append(f"退出码: {p.returncode}")
        out.append("stdout: " + o.decode("utf-8", "replace")[:1500])
        out.append("stderr: " + e.decode("utf-8", "replace")[:1500])
    except Exception as ex:
        out.append(f"取输出失败: {ex}")

new = set(os.listdir(LOGDIR)) - before
out.append(f"新增文件: {sorted(new)}")
for f in sorted(new):
    fp = os.path.join(LOGDIR, f)
    if os.path.isfile(fp) and os.path.getsize(fp) < 200000:
        out.append(f"--- {f} ---")
        try:
            out.append(open(fp, encoding="utf-8",
                            errors="replace").read()[:2000])
        except Exception as ex:
            out.append(f"读取失败: {ex}")

out.append("")
out.append("RESULT: " + ("OK" if alive else "CRASHED"))

if alive:
    p.terminate()
    try:
        p.wait(timeout=8)
        out.append("已正常退出")
    except Exception:
        p.kill()
        out.append("已强制结束")

open(r"D:\Dictionary\build\_launch4.txt", "w", encoding="utf-8").write(
    "\n".join(out))
print("ok")
