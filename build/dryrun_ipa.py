# -*- coding: utf-8 -*-
"""只做 dry-run：把清洗逻辑跑在真实数据上，看结果合不合理，不改库。"""
import sqlite3
import sys

sys.path.insert(0, r"D:\Dictionary\build")
from clean_ipa import clean_ipa

con = sqlite3.connect(r"D:\Dictionary\dict.db")
con.row_factory = sqlite3.Row
out = []

out.append("=" * 78)
out.append("重点样本（旧代码处理不好的那些）")
out.append("=" * 78)
tests = ["a priori", "ab initio", "abaca", "abandon", "abortion", "abuse",
         "acceleration", "-lived", "addicting", "advisee", "aftermarket",
         "desalinization", "directionality", "disaggregate", "empathetic",
         "karaoke", "okey", "water", "record", "tomato", "bath", "dance",
         "'s Gravenhage", "abbreviation", "aboveboard", "absorbability",
         "cup", "world", "girl", "hot", "thought", "this", "sing"]

out.append(f"{'word':<20} {'旧英式':<26} {'新英式':<24} {'旧美式':<24} {'新美式'}")
out.append("-" * 110)
for w in tests:
    r = con.execute("SELECT word, phonetic, phonetic_us FROM dict "
                    "WHERE lower=? LIMIT 1", (w.lower(),)).fetchone()
    if not r:
        out.append(f"{w:<20} <库里没有>")
        continue
    o1 = r["phonetic"] or ""
    o2 = r["phonetic_us"] or ""
    n1 = clean_ipa(o1)
    n2 = clean_ipa(o2)
    mark = ""
    if not n1 and o1:
        mark += " ⚠清洗后变空"
    out.append(f"{w:<20} {o1!r:<26} {n1!r:<24} {o2!r:<24} {n2!r}{mark}")

out.append("")
out.append("=" * 78)
out.append("全库抽样：清洗后变空的（需要警惕，会丢数据）")
out.append("=" * 78)
rows = con.execute(
    "SELECT word, phonetic, phonetic_us FROM dict "
    "WHERE (phonetic!='' OR phonetic_us!='') "
    "AND (phonetic LIKE '.%' OR phonetic LIKE '%.' OR phonetic LIKE '%(%' "
    "     OR phonetic LIKE '%;%') LIMIT 40").fetchall()
n_empty = 0
for r in rows:
    o1 = r["phonetic"] or ""
    n1 = clean_ipa(o1)
    if o1 and not n1:
        n_empty += 1
        out.append(f"  ⚠ {r['word']!r:<22} {o1!r}  → 空")
out.append(f"  抽查 {len(rows)} 条，变空 {n_empty} 条")

out.append("")
out.append("=" * 78)
out.append("全库统计：清洗会改变多少、变空多少")
out.append("=" * 78)
tot = changed = emptied = 0
for r in con.execute(
        "SELECT phonetic, phonetic_us FROM dict "
        "WHERE (phonetic!='' OR phonetic_us!='')"):
    o1 = r["phonetic"] or ""
    o2 = r["phonetic_us"] or ""
    n1 = clean_ipa(o1)
    n2 = clean_ipa(o2)
    tot += 1
    if n1 != o1 or n2 != o2:
        changed += 1
    if (o1 and not n1) or (o2 and not n2):
        emptied += 1
out.append(f"  总音标条目   : {tot:,}")
out.append(f"  会被改变     : {changed:,}  ({changed/max(tot,1)*100:.1f}%)")
out.append(f"  洗完变空     : {emptied:,}  ({emptied/max(tot,1)*100:.2f}%)")

con.close()
open(r"D:\Dictionary\build\_ipa_dryrun.txt", "w", encoding="utf-8").write(
    "\n".join(out))
print("ok")
