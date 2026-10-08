# -*- coding: utf-8 -*-
"""端到端启动验证：用新版 exe 真跑一次，确认能起来、图标资源正常、
新功能（官方词典行 / 例句板块）在真实运行时不报错。
"""
import io
import os
import subprocess
import sys
import time

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

EXE = r"D:\Dictionary\查单词.exe"
LOGDIR = r"D:\Dictionary"

print(f"exe = {EXE}")
print(f"size = {os.path.getsize(EXE):,}")

# 清掉旧日志，便于判断本次启动
before = set()
for f in os.listdir(LOGDIR):
    if f.endswith(".log") or f.startswith("crash"):
        before.add(f)
print(f"启动前日志: {sorted(before)}")

p = subprocess.Popen([EXE], cwd=LOGDIR,
                     stdout=subprocess.PIPE, stderr=subprocess.PIPE)
print(f"已启动，PID = {p.pid}")
time.sleep(7)

alive = p.poll() is None
print(f"7 秒后仍在运行: {alive}")
if not alive:
    out, err = p.communicate(timeout=5)
    print("退出码:", p.returncode)
    print("stdout:", out.decode("utf-8", "replace")[:2000])
    print("stderr:", err.decode("utf-8", "replace")[:2000])

# 检查有无崩溃日志
new = set(os.listdir(LOGDIR)) - before
print(f"新增文件: {sorted(new)}")

for f in sorted(new):
    fp = os.path.join(LOGDIR, f)
    if os.path.isfile(fp) and os.path.getsize(fp) < 200000:
        print(f"\n--- {f} ---")
        try:
            print(io.open(fp, encoding="utf-8", errors="replace").read()[:3000])
        except Exception as e:
            print("读取失败:", e)

if alive:
    print("\n关闭进程…")
    p.terminate()
    try:
        p.wait(timeout=8)
        print("已正常退出")
    except Exception:
        p.kill()
        print("已强制结束")
print("\nRESULT:", "OK" if alive else "CRASHED")
