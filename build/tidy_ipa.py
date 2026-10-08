# -*- coding: utf-8 -*-
"""补一道收尾清洗：去掉 ipa-dict 带进来的残留斜杠等杂质。"""
import re
import sqlite3

DB = r"D:\Dictionary\build\dict.db"
con = sqlite3.connect(DB)
con.row_factory = sqlite3.Row
cur = con.cursor()
out = []

rows = cur.execute(
    "SELECT rowid AS rid, word, phonetic, phonetic_us FROM dict "
    "WHERE phonetic LIKE '%/%' OR phonetic_us LIKE '%/%' "
    "   OR phonetic LIKE '%  %' OR phonetic_us LIKE '%  %'").fetchall()
out.append(f"待收尾清理 {len(rows):,} 条")

upd = []
samples = []
for r in rows:
    a = (r["phonetic"] or "").replace("/", " ")
    b = (r["phonetic_us"] or "").replace("/", " ")
    a = re.sub(r"\s{2,}", " ", a).strip()
    b = re.sub(r"\s{2,}", " ", b).strip()
    if a != (r["phonetic"] or "") or b != (r["phonetic_us"] or ""):
        upd.append((a, b, r["rid"]))
        if len(samples) < 10:
            samples.append((r["word"], r["phonetic"], a, r["phonetic_us"], b))

out.append("样本：")
for w, oa, na, ob, nb in samples:
    out.append(f"  {w:<20} 英 {oa!r} → {na!r}")
    out.append(f"  {'':<20} 美 {ob!r} → {nb!r}")

if upd:
    cur.executemany(
        "UPDATE dict SET phonetic=?, phonetic_us=? WHERE rowid=?", upd)
    con.commit()
out.append(f"已提交 {len(upd):,} 条")

# 最终复核
tot = cur.execute("SELECT COUNT(*) FROM dict").fetchone()[0]
has = cur.execute("SELECT COUNT(*) FROM dict WHERE phonetic!=''").fetchone()[0]
slash = cur.execute("SELECT COUNT(*) FROM dict WHERE phonetic LIKE '%/%'"
                    ).fetchone()[0]
out.append("")
out.append(f"总量 {tot:,}  有音标 {has:,} ({has/tot*100:.1f}%)  "
           f"仍含斜杠 {slash:,}")

con.close()
open(r"D:\Dictionary\build\_ipa_final.txt", "w", encoding="utf-8").write(
    "\n".join(out))
print("ok")
