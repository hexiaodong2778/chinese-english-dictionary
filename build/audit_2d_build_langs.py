# -*- coding: utf-8 -*-
"""核查多语言词库的设计意图：是否本来就没有释义。

查 build_langs.py 看当初是怎么建的库，
并从 ipa-dict 原始数据确认数据源本身有没有释义。
"""
import io
import os
import re
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

p = r"D:\Dictionary\build\build_langs.py"
src = io.open(p, encoding="utf-8").read()
print(f"build_langs.py 共 {len(src)} 行\n")

# 打印前 90 行看设计说明
lines = src.split("\n")
print("=" * 72)
print("build_langs.py 前 80 行")
print("=" * 72)
for i, ln in enumerate(lines[:80], 1):
    print(f"{i:4} {ln}")

print()
print("=" * 72)
print("搜索关键字段写入逻辑")
print("=" * 72)
for kw in ("translation", "definition", "INSERT", "CREATE TABLE", "sw",
           "phonetic", "ipa", "yue", "ja", "fr"):
    hits = [(i, l) for i, l in enumerate(lines, 1)
            if kw in l and not l.strip().startswith("#")]
    if hits:
        print(f"\n  [{kw}] {len(hits)} 处:")
        for i, l in hits[:6]:
            print(f"    {i:4}: {l.strip()[:100]}")
