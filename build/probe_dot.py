# -*- coding: utf-8 -*-
"""搞清 '.' 在音标里的真实语义，才能写对清洗规则。

需要区分三类：
  A. 音节省略标记：以 '.' 开头（".æbi'niʃiәu"）→ 去掉前导点，保留主体
  B. 音节分隔符：出现在音节边界，形如 "ә.bri:vi'eiʃәn" → **必须保留**
  C. 英美/多读音混装："bæθ.bɑ:θ"、"ә'bju:s.ә'bju:z" → 取第一个

难点：B 和 C 长得很像。判别线索是什么？
"""
import re
import sqlite3
from collections import Counter

con = sqlite3.connect(r"D:\Dictionary\dict.db")
con.row_factory = sqlite3.Row
out = []

rows = con.execute(
    "SELECT word, phonetic, phonetic_us FROM dict WHERE phonetic LIKE '%.%'"
).fetchall()
out.append(f"含 '.' 的音标共 {len(rows):,} 条")

# ---------- 观察：'.' 前面是不是重音符号 ----------
out.append("")
out.append("=" * 72)
out.append("线索 1：'.' 前一个字符是什么？")
out.append("=" * 72)
pre = Counter()
for r in rows:
    s = r["phonetic"]
    for m in re.finditer(r"\.", s):
        i = m.start()
        if i > 0:
            pre[s[i - 1]] += 1
        else:
            pre["<开头>"] += 1
for c, n in pre.most_common(18):
    u = f"U+{ord(c):04X}" if len(c) == 1 else c
    out.append(f"    {c!r}  {u}  {n:>7,}")

# ---------- 观察：'.' 后一个字符 ----------
out.append("")
out.append("=" * 72)
out.append("线索 2：'.' 后一个字符是什么？")
out.append("=" * 72)
post = Counter()
for r in rows:
    s = r["phonetic"]
    for m in re.finditer(r"\.", s):
        i = m.start()
        if i + 1 < len(s):
            post[s[i + 1]] += 1
        else:
            post["<结尾>"] += 1
for c, n in post.most_common(18):
    u = f"U+{ord(c):04X}" if len(c) == 1 else c
    out.append(f"    {c!r}  {u}  {n:>7,}")

# ---------- 关键观察：是否有空格/重音在附近 ----------
out.append("")
out.append("=" * 72)
out.append("线索 3：'.' 是否紧跟重音符号（判断是否是新读音的开头）")
out.append("=" * 72)
n_stress_after = 0
n_space_after = 0
n_dot_count = 0
multi = Counter()
for r in rows:
    s = r["phonetic"]
    cnt = s.count(".")
    multi[cnt] += 1
    n_dot_count += cnt
    for m in re.finditer(r"\.", s):
        i = m.start()
        nxt = s[i + 1:i + 3]
        if nxt[:1] == "'" or nxt[:1] == "\u02c8":
            n_stress_after += 1
        if nxt[:1] == " ":
            n_space_after += 1
out.append(f"  总 '.' 个数            : {n_dot_count:,}")
out.append(f"  紧跟重音符 ' 的        : {n_stress_after:,}")
out.append(f"  紧跟空格的             : {n_space_after:,}")
out.append("")
out.append("  每条音标里 '.' 的个数分布：")
for c, n in sorted(multi.items()):
    out.append(f"    {c} 个 '.' : {n:>7,} 条")

# ---------- 直接抽样看：哪些应该是音节分隔（该保留） ----------
out.append("")
out.append("=" * 72)
out.append("抽样：'.' 出现 1 次的条目（区分 B 与 C 最难的一类）")
out.append("=" * 72)
n = 0
for r in rows:
    s = r["phonetic"]
    if s.count(".") == 1 and not s.startswith("."):
        out.append(f"    {r['word']:<22} {s!r}")
        n += 1
        if n >= 25:
            break

out.append("")
out.append("=" * 72)
out.append("抽样：'.' 出现 2 次以上")
out.append("=" * 72)
n = 0
for r in rows:
    s = r["phonetic"]
    if s.count(".") >= 2:
        out.append(f"    {r['word']:<22} {s!r}")
        n += 1
        if n >= 20:
            break

out.append("")
out.append("=" * 72)
out.append("关键判断：这些词的 '.' 是英美分隔还是音节分隔？")
out.append("=" * 72)
out.append("  对比 phonetic 与 phonetic_us 两列，若两者 '.' 位置不同，")
out.append("  说明 '.' 是音节分隔符（因为英美音节划分不同）")
out.append("")
same_dot = diff_dot = 0
for r in con.execute(
        "SELECT word, phonetic, phonetic_us FROM dict "
        "WHERE phonetic LIKE '%.%' AND phonetic_us LIKE '%.%'"):
    a, b = r["phonetic"], r["phonetic_us"]
    if a.count(".") == b.count("."):
        same_dot += 1
    else:
        diff_dot += 1
out.append(f"  两列 '.' 个数相同: {same_dot:,}")
out.append(f"  两列 '.' 个数不同: {diff_dot:,}")
out.append("")
out.append("  抽样对照（看 '.' 是否在相同位置）:")
n = 0
for r in con.execute(
        "SELECT word, phonetic, phonetic_us FROM dict "
        "WHERE phonetic LIKE '%.%' AND phonetic_us LIKE '%.%' LIMIT 60"):
    a, b = r["phonetic"], r["phonetic_us"]
    mark = "同位置" if a.replace(".", "") == b.replace(".", "") else "不同"
    out.append(f"    {r['word']:<20} {a:<28} {b:<28} [{mark}]")
    n += 1
    if n >= 15:
        break

con.close()
open(r"D:\Dictionary\build\_dot_probe.txt", "w", encoding="utf-8").write(
    "\n".join(out))
print("ok")
