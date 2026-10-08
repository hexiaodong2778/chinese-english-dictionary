# -*- coding: utf-8 -*-
"""启动部署后的 exe，确认能正常运行不崩溃。"""
import os
import subprocess
import sys
import time

EXE = r"D:\Dictionary\查单词.exe"
out = []

p = subprocess.Popen([EXE], cwd=r"D:\Dictionary")
out.append(f"已启动 pid={p.pid}")
time.sleep(9)

rc = p.poll()
if rc is None:
    out.append("[PASS] 9 秒后仍在运行，未崩溃")
    p.terminate()
    try:
        p.wait(timeout=8)
    except Exception:
        p.kill()
    out.append("已关闭")
else:
    out.append(f"[FAIL] 进程已退出，返回码 {rc}")

open(r"D:\Dictionary\build\_launch.txt", "w", encoding="utf-8").write("\n".join(out))
print("ok")
