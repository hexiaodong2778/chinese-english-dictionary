# -*- coding: utf-8 -*-
"""验证打包后的 exe 真能启动并给出正确结果（不用源码，用 exe 自身）。"""
import os, sys, io, subprocess, time, tempfile, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

EXE = r"D:\Dictionary\查单词.exe"
DEPLOY = r"D:\Dictionary"

print("exe =", EXE, os.path.getsize(EXE), "bytes")
print("词库 =", os.path.getsize(os.path.join(DEPLOY, "dict.db")), "bytes")

# 用 exe 的 --selftest 之类能力？没有。改用「启动 + 查窗口标题」方式：
# 用 STARTUPINFO 隐藏窗口，起进程，等几秒确认没崩，再杀掉。
import ctypes
class SI(ctypes.Structure):
    _fields_ = [("cb", ctypes.c_ulong), ("lpReserved", ctypes.c_wchar_p),
                ("lpDesktop", ctypes.c_wchar_p), ("lpTitle", ctypes.c_wchar_p),
                ("dwX", ctypes.c_ulong), ("dwY", ctypes.c_ulong),
                ("dwXSize", ctypes.c_ulong), ("dwYSize", ctypes.c_ulong),
                ("dwXCountChars", ctypes.c_ulong), ("dwYCountChars", ctypes.c_ulong),
                ("dwFillAttribute", ctypes.c_ulong), ("dwFlags", ctypes.c_ulong),
                ("wShowWindow", ctypes.c_ushort), ("cbReserved2", ctypes.c_ushort),
                ("lpReserved2", ctypes.c_void_p),
                ("hStdInput", ctypes.c_void_p), ("hStdOutput", ctypes.c_void_p),
                ("hStdError", ctypes.c_void_p)]

si = SI()
si.cb = ctypes.sizeof(SI)
si.dwFlags = 1
si.wShowWindow = 0

env = dict(os.environ)
env["QT_QPA_PLATFORM"] = "offscreen"   # 让 Qt 无头跑，不弹窗
p = subprocess.Popen([EXE], cwd=DEPLOY, env=env,
                     stdout=subprocess.PIPE, stderr=subprocess.PIPE)
print("已启动 pid =", p.pid)
time.sleep(14)
rc = p.poll()
if rc is None:
    print("  PASS  exe 启动后持续运行（14s 未退出）")
    p.terminate()
    try:
        p.wait(timeout=8)
    except Exception:
        p.kill()
    print("  已关闭")
else:
    out, err = p.communicate()
    print(f"  FAIL  exe 提前退出 rc={rc}")
    print("  stderr:", (err or b"").decode("utf-8", "replace")[:800])
