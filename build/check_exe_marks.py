# -*- coding: utf-8 -*-
"""在 exe 二进制里搜索新功能的关键字符串，确认已打包。"""
import io

log = io.StringIO()
def say(s=""): log.write(str(s) + "\n")

exe = r"D:\Dictionary\查单词.exe"
data = open(exe, "rb").read()

marks = {
    "UserStore / 用户数据": b"user_data.db",
    "搜索历史": b"search history",
    "英英释义（联网）": "英英释义（联网）".encode("utf-8"),
    "柯林斯释义（联网）": "柯林斯释义（联网）".encode("utf-8"),
    "同义词（联网）": "同义词（联网）".encode("utf-8"),
    "翻译对话框": "翻译".encode("utf-8"),
    "有道 jsonapi 词典增强": b"dict.youdao.com/jsonapi",
    "有道翻译 API": b"openapi.youdao.com/api",
    "Forvo 全球发音": b"apifree.forvo.com",
    "返回上一词": "没有上一步了".encode("utf-8"),
    "单词本分组": "默认分组".encode("utf-8"),
    "收藏": "已收藏".encode("utf-8"),
    "一键清空历史": "清空全部搜索历史".encode("utf-8"),
    "AI 剪贴板提示": "粘贴(Ctrl+V)发送".encode("utf-8"),
}

for name, mark in marks.items():
    hit = mark in data
    say(f"  {'OK ' if hit else 'MISS'}  {name}")
    if not hit:
        say(f"       未找到: {mark!r}")

open(r"D:\Dictionary\build\_exe_marks.txt", "w", encoding="utf-8").write(log.getvalue())
print("done")
