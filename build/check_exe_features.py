# -*- coding: utf-8 -*-
"""直接跑部署版 exe，注入一个自检开关让它把渲染结果写文件。

exe 是 console=False 的单文件程序，没法直接看输出。
改用环境变量触发的自检：程序启动时若检测到
CHADANCI_SELFTEST 环境变量，就把几个词条的渲染 HTML 写到文件后退出。

这样能确凿证明「exe 里打包的代码」确实含例句功能，
而不是只验证了 build/app.py。
"""
import io
import os
import subprocess
import sys
import time

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# 先看 app.py 里有没有这个自检钩子
src = io.open(r"D:\Dictionary\build\app.py", encoding="utf-8").read()
print("app.py 含 SELFTEST 钩子:", "CHADANCI_SELFTEST" in src)
print("app.py 含 examples 渲染:", 'self._section("例句")' in src)
print("app.py 含 examples 方法:", "def examples(self, word" in src)

# 检查 exe 里是否打包了这些字符串（PyInstaller 会把源码编成 pyc 打进 exe，
# 字符串常量仍会以明文出现在 exe 中）
exe = r"D:\Dictionary\查单词.exe"
data = open(exe, "rb").read()
print(f"\nexe = {exe}  {len(data):,} bytes")

for probe in (b"Tatoeba", b"examples", b"oxfordlearnersdictionaries",
              b"example_count"):
    # exe 里的字符串可能是 utf-8 或 utf-16，两种都试
    u8 = probe in data
    u16 = probe.decode("ascii").encode("utf-16-le") in data
    print(f"  含 {probe.decode():32} utf8={u8}  utf16={u16}")
