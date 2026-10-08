"""分析 translation 字段的结构，寻找可提取的「义项」规律。

目标：判断一个词条的中文释义里，某个中文词是不是「独立义项」
（如 dog = "n. 狗, 坏蛋" → "狗" 是义项），
而不是「顺带出现」（如 shock = "长毛狗" → 只是释义的一部分）。
"""
import sqlite3
import re

DB = r"D:\Dictionary\build\dict.db"
con = sqlite3.connect(DB)
con.row_factory = sqlite3.Row

print("=== 观察若干词的 translation 原始结构 ===")
for w in ("dog", "shock", "sick", "puppy", "hound", "bitch", "shit",
          "cat", "book", "water", "run", "beautiful"):
    r = con.execute("SELECT translation FROM dict WHERE lower=?",
                    (w,)).fetchone()
    if r:
        print(f"  {w:12s} = {r['translation']!r}")

print("\n=== 词性标记统计 ===")
rows = con.execute(
    "SELECT translation FROM dict WHERE translation<>'' LIMIT 20000").fetchall()
pos_pat = re.compile(r"\b(n|v|vt|vi|a|adj|ad|adv|prep|conj|pron|num|int|art|aux|abbr)\.")
cnt = 0
samples = []
for r in rows:
    t = r["translation"]
    if pos_pat.match(t.strip()):
        cnt += 1
        if len(samples) < 8:
            samples.append(t[:80])
print(f"  以词性标记开头的: {cnt} / 20000")
for s in samples:
    print("   ", s)

print("\n=== 义项分隔符统计（顿号/逗号/分号）===")
r = con.execute("""SELECT
    SUM(CASE WHEN translation LIKE '%,%' THEN 1 ELSE 0 END) AS comma,
    SUM(CASE WHEN translation LIKE '%，%' THEN 1 ELSE 0 END) AS cn_comma,
    SUM(CASE WHEN translation LIKE '%；%' THEN 1 ELSE 0 END) AS cn_semi,
    SUM(CASE WHEN translation LIKE '%\n%' THEN 1 ELSE 0 END) AS nl,
    COUNT(*) AS total
    FROM dict WHERE translation<>''""").fetchone()
print("  ", dict(r))

con.close()
