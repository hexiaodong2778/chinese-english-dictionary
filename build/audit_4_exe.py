# -*- coding: utf-8 -*-
"""核查 ④：exe 里打包的代码 vs 最新 app.py 是否一致。

重点：我在打包后又改了 AI_SERVICES（加豆包、改通义千问），
      所以部署版 exe 很可能不含这个改动 -> 需要重新打包。
"""
import io
import os
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

EXE = r"D:\Dictionary\查单词.exe"
SRC = r"D:\Dictionary\build\app.py"

data = open(EXE, "rb").read()
src = io.open(SRC, encoding="utf-8").read()

print(f"exe  = {EXE}  {len(data):,} bytes")
import datetime
print(f"       {datetime.datetime.fromtimestamp(os.path.getmtime(EXE))}")
print(f"app.py {len(src):,} chars")
print(f"       {datetime.datetime.fromtimestamp(os.path.getmtime(SRC))}")

print()
print("=" * 72)
print("检查源码里的新功能是否已在 exe 中")
print("=" * 72)


def in_exe(s):
    b = s.encode("utf-8")
    return b in data


CHECKS = [
    ("官方词典：牛津网址", "oxfordlearnersdictionaries"),
    ("官方词典：剑桥网址", "dictionary.cambridge.org"),
    ("官方词典：柯林斯网址", "collinsdictionary.com"),
    ("官方词典：朗文网址", "ldoceonline.com"),
    ("官方词典：韦氏网址", "merriam-webster.com"),
    ("官方词典：词源网址", "etymonline.com"),
    ("例句：数据来源标注", "Tatoeba"),
    ("例句：查询方法", "def examples"),
    ("例句：板块标题", "来自 Tatoeba"),
    ("界面：词典原文行", "词典原文"),
    ("AI：豆包（新增）", "doubao.com"),
    ("AI：通义千问新域名", "qianwen.com"),
    ("AI：DeepSeek", "chat.deepseek.com"),
    ("AI：腾讯元宝", "yuanbao.tencent.com"),
]

allok = True
for name, token in CHECKS:
    present = in_exe(token)
    if not present:
        allok = False
    print(f"  [{'OK' if present else 'XX'}] {name:22} '{token}'")

print()
print("=" * 72)
if allok:
    print("结论：exe 与最新源码一致，无需重新打包。")
else:
    print("结论：exe **落后于** 源码，有功能没打进去 -> 必须重新打包！")
    print()
    print("缺失项对应的改动：")
    for name, token in CHECKS:
        if not in_exe(token):
            print(f"  - {name}  ({token})")
sys.exit(0 if allok else 2)
