# -*- coding: utf-8 -*-
"""分析现有音标字段的质量问题，确定清洗规则。

要查清：
① phonetic 与 phonetic_us 到底是什么关系（是英/美，还是同一个值？）
② 含 '.' 的英美混装有多少种形态
③ 含中文/乱码/异常符号的有多少
④ ' 与 ' 两种撇号的重音符号混用情况
"""
import re
import sqlite3

con = sqlite3.connect(r"D:\Dictionary\dict.db")
con.row_factory = sqlite3.Row
out = []

out.append("=" * 70)
out.append("① phonetic（英）vs phonetic_us（美）关系")
out.append("=" * 70)
r = con.execute(
    "SELECT "
    "SUM(CASE WHEN phonetic=phonetic_us THEN 1 ELSE 0 END) same, "
    "SUM(CASE WHEN phonetic!=phonetic_us THEN 1 ELSE 0 END) diff, "
    "COUNT(*) tot FROM dict "
    "WHERE phonetic!='' AND phonetic_us!=''").fetchone()
out.append(f"  都有值时: 相同 {r['same']:,}   不同 {r['diff']:,}   "
           f"共 {r['tot']:,}")
out.append(f"  → {'⚠ 两列基本是重复数据' if r['same'] > r['tot']*0.8 else '两列确实不同'}")

out.append("")
out.append("  不同的示例：")
for x in con.execute(
        "SELECT word, phonetic, phonetic_us FROM dict "
        "WHERE phonetic!='' AND phonetic_us!='' AND phonetic!=phonetic_us "
        "LIMIT 12"):
    out.append(f"    {x['word']:<18} 英={x['phonetic']:<20} "
               f"美={x['phonetic_us']}")

out.append("")
out.append("=" * 70)
out.append("② 含 '.' 的音标（英美混装）形态分析")
out.append("=" * 70)
rows = con.execute("SELECT word, phonetic FROM dict "
                   "WHERE phonetic LIKE '%.%'").fetchall()
out.append(f"  共 {len(rows):,} 条")
# 分类
pat_two = 0
pat_lead = 0
other = []
for x in rows:
    p = x["phonetic"]
    if re.match(r"^\s*\.", p):
        pat_lead += 1
    elif p.count(".") == 1 and len(p.split(".")) == 2:
        pat_two += 1
    else:
        if len(other) < 10:
            other.append((x["word"], p))
out.append(f"  以 '.' 开头（音节省略标记）: {pat_lead:,}")
out.append(f"  形式为 A.B 两段（真英美混装）: {pat_two:,}")
out.append(f"  其它形态示例: {other}")

out.append("")
out.append("  A.B 两段式的样本（这类要用第一个）:")
n = 0
for x in rows:
    p = x["phonetic"]
    if not re.match(r"^\s*\.", p) and p.count(".") == 1:
        parts = p.split(".")
        if len(parts) == 2 and parts[0].strip() and parts[1].strip():
            out.append(f"    {x['word']:<18} {p:<26} → 取 {parts[0].strip()}")
            n += 1
            if n >= 10:
                break

out.append("")
out.append("  以 '.' 开头样本（应整体去掉前导点）:")
n = 0
for x in rows:
    if re.match(r"^\s*\.", x["phonetic"]):
        out.append(f"    {x['word']:<18} {x['phonetic']}")
        n += 1
        if n >= 8:
            break

out.append("")
out.append("=" * 70)
out.append("③ 异常内容扫描")
out.append("=" * 70)
checks = [
    ("含中文字符", "phonetic GLOB '*[一-龥]*'"),
    ("含数字", "phonetic GLOB '*[0-9]*'"),
    ("含圆括号", "phonetic LIKE '%(%'"),
    ("含方括号", "phonetic LIKE '%[%'"),
    ("含分号", "phonetic LIKE '%;%'"),
    ("含空格", "phonetic LIKE '% %'"),
    ("直接用撇号 U+02BC 重音", "phonetic LIKE '%' || char(700) || '%'"),
    ("用 ASCII 单引号当重音", "phonetic LIKE '%''%'"),
]
for label, cond in checks:
    try:
        c = con.execute(f"SELECT COUNT(*) FROM dict WHERE phonetic!='' AND {cond}"
                        ).fetchone()[0]
        out.append(f"  {label:<24}: {c:,}")
    except Exception as e:
        out.append(f"  {label:<24}: 查询失败 {e}")

out.append("")
out.append("=" * 70)
out.append("④ 重音符号实际用的是什么（关键：旧代码找 ' 找不到）")
out.append("=" * 70)
for label, ch in [("ASCII 撇号", "'"), ("U+02BC 修饰字母撇号", "\u02bc"),
                  ("U+02C8 重音符", "\u02c8"),
                  ("U+2018 左单引号", "\u2018"),
                  ("U+2019 右单引号", "\u2019")]:
    c = con.execute("SELECT COUNT(*) FROM dict WHERE phonetic LIKE ?",
                    ("%" + ch + "%",)).fetchone()[0]
    out.append(f"  {label:<26} U+{ord(ch):04X}  "
               f"出现于 {c:,} 条音标")

out.append("")
out.append("=" * 70)
out.append("⑤ ph_ok=1 的 217,889 条到底是什么")
out.append("=" * 70)
out.append("  ph_ok=1 的抽样（看是否都是高质量音标）:")
for x in con.execute("SELECT word, phonetic, phonetic_us FROM dict "
                     "WHERE ph_ok=1 LIMIT 10"):
    out.append(f"    {x['word']:<16} {x['phonetic']:<20} {x['phonetic_us']}")

out.append("")
out.append("  ph_ok=0 但**有**音标的条目数（标记与实际不符？）:")
c = con.execute("SELECT COUNT(*) FROM dict WHERE ph_ok=0 AND phonetic!=''"
                ).fetchone()[0]
out.append(f"    {c:,}")

con.close()
open(r"D:\Dictionary\build\_ipa_qual.txt", "w", encoding="utf-8").write(
    "\n".join(out))
print("ok")
