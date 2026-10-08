# -*- coding: utf-8 -*-
"""把仓库脚本里写死的开发机路径改写成当前机器的实际路径。

------------------------------------------------------------------
为什么需要它
------------------------------------------------------------------
本仓库的 100 多个测试 / 工具脚本原先都是为**一台特定开发机**写的，
里面带着这些绝对路径：

    D:\\Dictionary\\build               开发机的源码目录
    D:\\Dictionary                      开发机的部署目录（exe 与词库）
    D:\\hclaw\\python\\python.exe        开发机用的 Python

代码逻辑本身没有问题，但换台机器这些路径就不存在了 ——
测试会因为 import 不到 app 而直接报错。

本脚本把这些路径就地改写成**当前机器的实际位置**：

    D:\\Dictionary\\build   →  本脚本所在目录（即 build/）
    D:\\Dictionary          →  本脚本所在目录的上一级（仓库根）
    D:\\hclaw\\python\\python.exe  →  当前解释器 sys.executable

------------------------------------------------------------------
用法
------------------------------------------------------------------
    cd build
    python _relocate.py

会被改动的文件会先备份到 build/_relocate_backup/，可随时还原。
不改动的文件不做任何处理。

注意：app.py 本身**不含**任何硬编码路径（词库按 exe / 脚本所在目录查找），
所以「下载 exe 直接用」和「clone 后 python app.py」都不受本脚本影响 ——
它只服务于「想跑测试套件」的场景。
"""
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PARENT = os.path.dirname(HERE)
PYTHON = sys.executable or r"D:\hclaw\python\python.exe"
BACKUP = os.path.join(HERE, "_relocate_backup")

# 顺序要紧：先长后短，否则 D:\Dictionary\build 会被 D:\Dictionary 先吃掉
RULES = [
    (r"D:\Dictionary\build", HERE),
    (r"D:\Dictionary", PARENT),
    (r"D:\hclaw\python\python.exe", PYTHON),
]

SELF = os.path.basename(os.path.abspath(__file__))


def main():
    print("=" * 66)
    print("  把脚本里的开发机绝对路径改写为当前机器路径")
    print("=" * 66)
    print("  本机 build 目录 : %s" % HERE)
    print("  本机仓库根目录  : %s" % PARENT)
    print("  本机解释器      : %s" % PYTHON)
    print()

    changed = []
    scanned = 0
    for fn in sorted(os.listdir(HERE)):
        if not fn.endswith(".py") or fn == SELF:
            continue
        p = os.path.join(HERE, fn)
        try:
            s = open(p, encoding="utf-8", errors="replace").read()
        except OSError:
            continue
        scanned += 1
        orig = s
        for old, new in RULES:
            if old in s:
                s = s.replace(old, new)
        if s != orig:
            os.makedirs(BACKUP, exist_ok=True)
            shutil.copy2(p, os.path.join(BACKUP, fn))
            open(p, "w", encoding="utf-8", newline="\n").write(s)
            changed.append(fn)

    print("  扫描 %d 个 .py 文件" % scanned)
    print()
    if not changed:
        print("  ✅ 没有发现需要改写的路径 —— 本机已经就绪，可以直接跑测试：")
        print("       python _run_all2.py")
        return

    print("  ✅ 改写了 %d 个文件（原文件已备份到 build/_relocate_backup/）" % len(changed))
    print()
    for fn in changed[:60]:
        print("     %s" % fn)
    if len(changed) > 60:
        print("     ... 另有 %d 个" % (len(changed) - 60))
    print()
    print("  现在可以跑测试了：")
    print("     python _run_all2.py          # 全量（55 个脚本，约 9 分钟）")
    print("     python _quick.py test_engine.py test_smoke.py   # 只跑指定脚本")
    print()
    print("  想还原：把 build/_relocate_backup/ 里的文件拷回上一级目录即可。")


if __name__ == "__main__":
    main()
