# -*- coding: utf-8 -*-
"""中译英排名回归测试：既有的 10 个核心词 + 新修的义项位置问题。"""
import sys, os, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, r"D:\Dictionary\build")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtWidgets import QApplication
app = QApplication(sys.argv)
import app as A

w = A.MainWindow()

# (中文, 期望排第一, 允许在 top5 内也算通过)
CASES = [
    ("狗", "dog"), ("猫", "cat"), ("书", "book"), ("水", "water"),
    ("学习", "study"), ("跑", "run"), ("电脑", "computer"),
    ("美丽", "beautiful"), ("环境", "environment"), ("放弃", "abandon"),
    ("朋友", "friend"), ("老师", "teacher"), ("吃", "eat"), ("喝", "drink"),
    ("睡觉", "sleep"), ("工作", "work"), ("钱", "money"), ("时间", "time"),
    ("房子", "house"), ("汽车", "car"), ("学生", "student"), ("医生", "doctor"),
    ("说", "say"), ("看", "look"), ("走", "walk"), ("买", "buy"),
    ("卖", "sell"), ("打开", "open"), ("关闭", "close"), ("开始", "begin"),
]

top1 = top5 = miss = 0
fails = []
for zh, want in CASES:
    rows = w.engine.search_cn(zh, limit=30)
    words = [r["word"].lower() for r in rows]
    if words and words[0] == want:
        top1 += 1
        print(f"  TOP1  {zh} → {want}")
    elif want in words[:5]:
        top5 += 1
        pos = words.index(want) + 1
        print(f"  TOP{pos}  {zh} → {want}   (第一是 {words[0]})")
        fails.append(f"{zh}: {want} 排第{pos}，第一是 {words[0]}")
    elif want in words:
        pos = words.index(want) + 1
        print(f"  TOP{pos}  {zh} → {want}   (第一是 {words[0]})")
        fails.append(f"{zh}: {want} 排第{pos}，第一是 {words[0]}")
    else:
        miss += 1
        print(f"  MISS  {zh} → {want} 不在前 30（第一是 {words[0] if words else None}）")
        fails.append(f"{zh}: {want} 完全未出现")

print()
print(f"排第一 {top1}/{len(CASES)}   top5内 {top5}   缺席 {miss}")
if fails:
    print("未达第一的：")
    for f in fails:
        print("   -", f)
