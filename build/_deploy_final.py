# -*- coding: utf-8 -*-
"""打包 → 部署 → 自检 一条龙。

顺序很讲究：
  1. 先 taskkill —— 否则 exe 被占用，shutil.copy2 会抛 WinError 32
  2. 逐字节校验 —— copy 完必须 sha256 比对，不能假定成功
  3. 在**部署目录**跑自检 —— resource_path 相对 exe 所在目录找词库，
     在 dist/ 下会报「词库不存在」（那是正确行为），必须到部署目录验
"""
import os
import sys
import io
import time
import shutil
import hashlib
import subprocess

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

BUILD = r"D:\Dictionary\build"
DIST = os.path.join(BUILD, "dist", "查单词.exe")
DEP = r"D:\Dictionary"
TARGET = os.path.join(DEP, "查单词.exe")

L = []
def say(s=""):
    L.append(str(s)); print(s)

def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()

say("=" * 70)
say("1. 杀掉可能占用 exe 的进程")
say("=" * 70)
r = subprocess.run(["taskkill", "/F", "/IM", "查单词.exe"],
                   capture_output=True)
# ⚠ taskkill 在中文 Windows 上输出的是 GBK，不是 UTF-8 ——
#   用 text=True 会在解码时抛 UnicodeDecodeError，必须自己带 errors 解码。
_msg = (r.stdout or r.stderr or b"").decode("utf-8", "replace").strip()
say("   rc=%s %s" % (r.returncode, _msg[:120]))
time.sleep(0.6)

say()
say("=" * 70)
say("2. 部署 dist -> D:\\Dictionary")
say("=" * 70)
say("   源: %s" % DIST)
say("   目标: %s" % TARGET)
if not os.path.exists(DIST):
    say("   ✗ 源文件不存在，中止"); sys.exit(1)

src_sha = sha(DIST)
say("   源  size=%d  sha256=%s" % (os.path.getsize(DIST), src_sha[:16]))
shutil.copy2(DIST, TARGET)

dst_sha = sha(TARGET)
say("   目标 size=%d  sha256=%s" % (os.path.getsize(TARGET), dst_sha[:16]))
ok = (src_sha == dst_sha)
say("   %s 逐字节一致" % ("✓" if ok else "✗"))

say()
say("=" * 70)
say("3. 部署版自检")
say("=" * 70)
# ⚠ 2026-09-18：本轮新增 --selftest-v2（difflib 是否打进 exe / 原句闸门 /
#   撤销快照还原 / 单词本分组清空 / 翻译通道常量 / 真实翻译）。
#   它必须**在部署目录**跑：里面走的是 exe 内真实代码路径，
#   difflib 若没打包会在这里露馅。
for flag, out in (("--selftest-v2", "_d_v2.txt"),
                  ("--selftest-ai", "_d_ai.txt"),
                  ("--selftest-cn", "_d_cn.txt"),
                  ("--selftest-edge", "_d_edge.txt")):
    outp = os.path.join(DEP, out)
    try:
        if os.path.exists(outp):
            os.remove(outp)
    except Exception:
        pass
    t0 = time.perf_counter()
    r = subprocess.run([TARGET, flag, outp], capture_output=True,
                       cwd=DEP, timeout=180)
    ms = (time.perf_counter() - t0) * 1000
    say()
    say("   --- %s (rc=%s, %.0f ms) ---" % (flag, r.returncode, ms))
    if os.path.exists(outp):
        txt = open(outp, encoding="utf-8", errors="replace").read()
        for ln in txt.splitlines():
            say("     " + ln)
    else:
        say("     <没有产出 %s>" % out)
        if r.stdout:
            say("     stdout: " + r.stdout.decode("utf-8", "replace")[:200])
        if r.stderr:
            say("     stderr: " + r.stderr.decode("utf-8", "replace")[:200])

say()
say("=" * 70)
say("DONE")
say("=" * 70)

with open(os.path.join(BUILD, "_deploy_final.txt"), "w", encoding="utf-8") as f:
    f.write("\n".join(L) + "\n")
print("\nlog -> build/_deploy_final.txt")
