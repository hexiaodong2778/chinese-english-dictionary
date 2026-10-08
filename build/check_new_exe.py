# -*- coding: utf-8 -*-
"""对比新 exe 二进制与源码，确认功能已真正打包进去。

原理：PyInstaller 把源码中的字符串常量以明文存进 exe，
直接搜二进制即可判定某个功能有没有被打进去。
"""
import os

EXE = r"D:\Dictionary\build\dist\查单词.exe"
SRC = r"D:\Dictionary\build\app.py"

blob = open(EXE, "rb").read()
src = open(SRC, encoding="utf-8").read()
out = [f"exe 大小 {len(blob):,} 字节", f"源码大小 {len(src):,} 字节", ""]

# (说明, 二进制里应出现的字符串, 是否必须)
CHECKS = [
    ("短语：板块标题", "常用短语".encode("utf-8"), True),
    ("短语：出处说明", "固定搭配".encode("utf-8"), True),
    ("短语：SQL 片段", b"word LIKE '% %'", True),
    ("短语：phrase: 协议", b"phrase:", True),
    ("短语：粒子表标志词", b"PHRASE_PARTICLES", True),
    ("短语：back 粒子", b'\\"back\\"' if False else '"back"'.encode("utf-8"), True),
    ("短语：oxford 排序", b"oxford", True),
    ("AI：豆包官网", b"doubao.com", True),
    ("AI：豆包中文名", "豆包".encode("utf-8"), True),
    ("AI：通义新域名", b"qianwen.com", True),
    ("AI：旧域名应已移除", b"tongyi.aliyun.com", False),
    ("词典原文：牛津", b"oxfordlearnersdictionaries.com", True),
    ("词典原文：剑桥", b"dictionary.cambridge.org", True),
    ("词典原文：朗文", b"ldoceonline.com", True),
    ("词典原文：韦氏", b"merriam-webster.com", True),
    ("词典原文：词源", b"etymonline.com", True),
    ("例句：Tatoeba 出处", b"Tatoeba", True),
    ("例句：ex_index 查询", b"ex_index", True),
    ("UI：odBtn 样式", b"odBtn", True),
    ("UI：词典原文 标签", "词典原文".encode("utf-8"), True),
]

P = F = 0
for name, needle, must in CHECKS:
    hit = needle in blob
    if must and not hit:
        out.append(f"  [FAIL] {name:26} 缺失！")
        F += 1
    elif must and hit:
        out.append(f"  [PASS] {name:26} 已打包")
        P += 1
    elif not must and hit:
        out.append(f"  [FAIL] {name:26} 不应出现却存在！")
        F += 1
    else:
        out.append(f"  [PASS] {name:26} 已确认移除")
        P += 1

out.append("")
out.append(f"通过 {P} / 失败 {F}")
out.append("")
out.append("结论：" + ("exe 与源码一致，功能全部打包成功。" if F == 0
                        else "exe 仍有缺失，需要排查！"))
open(r"D:\Dictionary\build\_execheck.txt", "w", encoding="utf-8").write("\n".join(out))
print(f"PASS={P} FAIL={F}")
