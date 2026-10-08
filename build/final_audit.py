# -*- coding: utf-8 -*-
"""最终交付审计：文件完整性 + 数据 + exe 功能 + 文档一致性。"""
import hashlib
import os
import sqlite3

DEPLOY = r"D:\Dictionary"
BUILD = r"D:\Dictionary\build"
out = []
P = F = 0


def ck(name, cond, extra=""):
    global P, F
    if cond:
        P += 1
        out.append(f"  [PASS] {name}")
    else:
        F += 1
        out.append(f"  [FAIL] {name} {extra}")


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


out.append("=== 1. 部署文件 ===")
need = ["查单词.exe", "dict.db", "dict_ja.db", "dict_fr.db", "dict_yue.db",
        "使用说明.txt"]
files = {f: os.path.join(DEPLOY, f) for f in need}
for f, p in files.items():
    ck(f"{f} 存在", os.path.exists(p))
    if os.path.exists(p):
        out.append(f"         {os.path.getsize(p):>13,} 字节")

extra = [f for f in os.listdir(DEPLOY)
         if os.path.isfile(os.path.join(DEPLOY, f)) and f not in need]
ck("部署目录无多余文件", not extra, str(extra))

ck("exe 与 dist 一致",
   sha(files["查单词.exe"]) == sha(os.path.join(BUILD, "dist", "查单词.exe")))
ck("dict.db 与 build 一致",
   sha(files["dict.db"]) == sha(os.path.join(BUILD, "dict.db")))

out.append("\n=== 2. 词库数据 ===")
con = sqlite3.connect(files["dict.db"])
con.row_factory = sqlite3.Row
tabs = [r[0] for r in con.execute(
    "SELECT name FROM sqlite_master WHERE type='table'")]
for t in ("dict", "cn_index", "lemma", "example", "ex_index", "meta"):
    ck(f"表 {t} 存在", t in tabs)
n = {t: con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
     for t in ("dict", "example", "ex_index", "lemma")}
ck("dict 词条 77 万", n["dict"] > 770000, str(n["dict"]))
ck("example 句对 7.7 万", n["example"] > 77000, str(n["example"]))
ck("ex_index 索引 6.8 万", n["ex_index"] > 68000, str(n["ex_index"]))
ck("lemma 词形 18 万", n["lemma"] > 187000, str(n["lemma"]))
nph = con.execute("SELECT COUNT(*) FROM dict WHERE word LIKE '% %' "
                  "AND translation!=''").fetchone()[0]
ck("短语来源多词条目 36 万", nph > 360000, str(nph))
for w, must in (("give up", "放弃"), ("look after", "照顾"),
                ("take off", "起飞"), ("put up with", "忍受")):
    r = con.execute("SELECT translation FROM dict WHERE lower=?", (w,)).fetchone()
    ck(f"短语 {w} 有中文", bool(r) and must in (r["translation"] or ""))
con.close()

out.append("\n=== 3. exe 功能（二进制探针）===")
blob = open(files["查单词.exe"], "rb").read()
for name, needle in [
    ("常用短语板块", "常用短语".encode()),
    ("phrase 协议", b"phrase:"),
    ("粒子过滤 SQL", b"word LIKE '% %'"),
    ("豆包", "豆包".encode()),
    ("doubao.com", b"doubao.com"),
    ("qianwen.com", b"qianwen.com"),
    ("牛津官网", b"oxfordlearnersdictionaries.com"),
    ("剑桥官网", b"dictionary.cambridge.org"),
    ("朗文官网", b"ldoceonline.com"),
    ("韦氏官网", b"merriam-webster.com"),
    ("词源官网", b"etymonline.com"),
    ("Tatoeba", b"Tatoeba"),
    ("ex_index", b"ex_index"),
    ("odBtn", b"odBtn"),
]:
    ck(f"含 {name}", needle in blob)
ck("已移除旧通义域名", b"tongyi.aliyun.com" not in blob)

out.append("\n=== 4. 文档一致性 ===")
doc = open(files["使用说明.txt"], encoding="utf-8").read()
for name, kw in [("含常用短语章节", "常用短语"),
                 ("含词典原文章节", "词典原文"),
                 ("含真实例句章节", "真实例句"),
                 ("AI 列 6 家含豆包", "豆包"),
                 ("AI 列出全部 6 家",
                  all(x in doc for x in ("豆包", "DeepSeek", "腾讯元宝",
                                         "Kimi", "通义千问", "ChatGPT"))),
                 ("功能介绍含短语", "固定搭配"),
                 ("FAQ 含短语", "没有「常用短语」板块"),
                 ("图标描述已更新", "16/24/32/48"),
                 ("不再写旧图标描述", "32/48 像素用书本剪影" not in doc),
                 ("词库规模含短语", "36.6 万"),
                 ("操作方式含短语点击", "点击「常用短语」")]:
    ck(name, kw if isinstance(kw, bool) else (kw in doc))

out.append("\n=== 5. 源码状态 ===")
src = open(os.path.join(BUILD, "app.py"), encoding="utf-8").read()
ck("app.py 有 phrases 方法", "def phrases(self, word, limit=8)" in src)
ck("app.py 有 PHRASE_PARTICLES", "PHRASE_PARTICLES = {" in src)
ck("app.py 有 _clean_phrase_tr", "def _clean_phrase_tr" in src)
ck("app.py 有 phrase: 处理", 'startswith("phrase:")' in src)
ck("app.py 含豆包", "doubao" in src)
ck("app.py 含 qianwen", "qianwen.com" in src)

out.append("\n" + "=" * 56)
out.append(f"通过 {P} / 失败 {F}")
out.append("=" * 56)
open(os.path.join(BUILD, "_final_audit.txt"), "w", encoding="utf-8").write("\n".join(out))
print(f"PASS={P} FAIL={F}")
