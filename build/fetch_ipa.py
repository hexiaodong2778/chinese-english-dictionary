# -*- coding: utf-8 -*-
"""下载 ipa-dict 英美音标，统计能为本词库补上多少缺失音标。

ipa-dict 格式：每行  "word\\t/phonetic/"
许可：MIT（open-dict-data/ipa-dict）
"""
import os
import re
import sqlite3
import urllib.request

OUTDIR = r"D:\Dictionary\build\ipa_src"
os.makedirs(OUTDIR, exist_ok=True)

SRC = {
    "us": "https://cdn.jsdelivr.net/gh/open-dict-data/ipa-dict@master/data/en_US.txt",
    "uk": "https://cdn.jsdelivr.net/gh/open-dict-data/ipa-dict@master/data/en_UK.txt",
}

out = []

# ---------- ① 下载 ----------
out.append("=" * 70)
out.append("① 下载 ipa-dict")
out.append("=" * 70)
paths = {}
for key, url in SRC.items():
    dst = os.path.join(OUTDIR, f"en_{key}.txt")
    if os.path.exists(dst) and os.path.getsize(dst) > 100000:
        out.append(f"  {key}: 已存在 {os.path.getsize(dst):,} B")
        paths[key] = dst
        continue
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=60) as r:
            data = r.read()
        with open(dst, "wb") as f:
            f.write(data)
        out.append(f"  {key}: 下载完成 {len(data):,} B")
        paths[key] = dst
    except Exception as e:
        out.append(f"  {key}: 下载失败 {type(e).__name__}: {e}")

# ---------- ② 解析 ----------
out.append("")
out.append("=" * 70)
out.append("② 解析音标表")
out.append("=" * 70)
ipa = {"us": {}, "uk": {}}
for key, path in paths.items():
    n = 0
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if not line or "\t" not in line:
                continue
            w, ph = line.split("\t", 1)
            w = w.strip().lower()
            ph = ph.strip()
            if not w or not ph:
                continue
            # 只取第一个音标（有的词是 "w1,w2" 多个读音）
            ph = ph.split(",")[0].strip()
            # ipa-dict 的音标带 /.../ 斜杠，去掉
            ph = ph.strip("/")
            if w not in ipa[key]:
                ipa[key][w] = ph
                n += 1
    out.append(f"  en_{key}: {len(ipa[key]):,} 个词条  （新增 {n:,}）")

out.append("")
out.append("抽样看格式：")
for w in ["water", "tomato", "record", "schedule", "thought", "world"]:
    out.append(f"    {w:<10} US={ipa['us'].get(w, '-'):<18} "
               f"UK={ipa['uk'].get(w, '-'):<18}")

# ---------- ③ 与词库比对，算覆盖率提升 ----------
out.append("")
out.append("=" * 70)
out.append("③ 对词库的覆盖率提升（模拟）")
out.append("=" * 70)
con = sqlite3.connect(r"D:\Dictionary\dict.db")
con.row_factory = sqlite3.Row

tot = con.execute("SELECT COUNT(*) FROM dict").fetchone()[0]
has = con.execute("SELECT COUNT(*) FROM dict "
                  "WHERE phonetic IS NOT NULL AND phonetic!=''").fetchone()[0]
out.append(f"  词库总量      : {tot:,}")
out.append(f"  当前有音标    : {has:,}  ({has/tot*100:.1f}%)")

# 取所有缺失音标的纯字母单词
rows = con.execute(
    "SELECT word FROM dict WHERE (phonetic IS NULL OR phonetic='') "
    "AND lower GLOB '[a-z]*' AND word NOT LIKE '% %'").fetchall()
out.append(f"  缺失音标的单词: {len(rows):,}")

hit = 0
miss_sample = []
for r in rows:
    w = (r["word"] or "").strip().lower()
    if w in ipa["us"] or w in ipa["uk"]:
        hit += 1
    elif len(miss_sample) < 10:
        miss_sample.append(w)

out.append(f"  能被 ipa-dict 补上: {hit:,}  "
           f"({hit/max(len(rows),1)*100:.1f}% 的缺口)")
newtot = has + hit
out.append(f"  补后覆盖率    : {newtot:,} / {tot:,} = {newtot/tot*100:.1f}%")

out.append("")
out.append(f"  补不上的示例（前 10 个）: {miss_sample}")

# 短语情况
prow = con.execute("SELECT COUNT(*) FROM dict WHERE word LIKE '% %'").fetchone()[0]
phit = 0
for r in con.execute("SELECT word FROM dict WHERE word LIKE '% %' "
                     "AND (phonetic IS NULL OR phonetic='')"):
    w = (r[0] or "").strip().lower()
    if w in ipa["us"] or w in ipa["uk"]:
        phit += 1
out.append("")
out.append(f"  短语（多词）共 {prow:,}，ipa-dict 能补 {phit:,}")

con.close()
open(r"D:\Dictionary\build\_ipa_stat.txt", "w", encoding="utf-8").write(
    "\n".join(out))
print("ok")
