# -*- coding: utf-8 -*-
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
from opencc import OpenCC
cc = OpenCC("t2s")
tests = [
    "這個男人談了一整個小時的話。",
    "湯姆令人難以忍受。",
    "我是新來的。",
    "他們被母親拋棄了。",
    "我明天能見你嗎？",
    "我的公寓在四樓。",
]
for t in tests:
    print(f"  {t}  ->  {cc.convert(t)}")
