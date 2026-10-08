"""验证：用 frq/bnc 词频排序 + 释义精确度加权，能否让 dog 排到第一。"""
import sqlite3

DB = r"D:\Dictionary\build\dict.db"
con = sqlite3.connect(DB)
con.row_factory = sqlite3.Row

print("=== dog / hound / canine 的词频 ===")
for w in ("dog", "hound", "canine", "pooch", "cur", "bitch", "puppy"):
    r = con.execute(
        "SELECT word, frq, bnc, collins, oxford, tag, translation FROM dict "
        "WHERE lower=?", (w,)).fetchone()
    if r:
        t = (r["translation"] or "").replace("\n", " / ")[:50]
        print(f"  {w:8s} frq={r['frq']:6d} bnc={r['bnc']:6d} "
              f"collins={r['collins']} oxford={r['oxford']} tag={r['tag']:12s} | {t}")

print("\n=== 若按 frq 升序取含『狗』的词条（frq>0，min freq 优先）===")
rows = con.execute("""
    SELECT c.word, c.zh, d.frq, d.bnc, d.collins, d.tag
    FROM cn_index c LEFT JOIN dict d ON d.lower = c.lower
    WHERE c.zh LIKE '%狗%' AND d.frq > 0
    ORDER BY d.frq ASC LIMIT 20
""").fetchall()
for r in rows:
    print(f"  {r['word']:20s} frq={r['frq'] or 0:6d} collins={r['collins'] or 0} "
          f"tag={r['tag'] or '':14s} | {r['zh'][:40]}")

print("\n=== 若按『释义以该词开头』优先 + frq 排序 ===")
rows = con.execute("""
    SELECT c.word, c.zh, d.frq, d.collins, d.tag
    FROM cn_index c LEFT JOIN dict d ON d.lower = c.lower
    WHERE c.zh LIKE '%狗%'
    ORDER BY
      CASE WHEN c.zh LIKE '狗%' OR c.zh LIKE 'n. 狗%' OR c.zh LIKE 'a. 狗%'
                OR c.zh LIKE 'v. 狗%' OR c.zh LIKE 'vt. 狗%' OR c.zh LIKE 'vi. 狗%'
           THEN 0 ELSE 1 END,
      COALESCE(d.frq, 999999) ASC
    LIMIT 20
""").fetchall()
for r in rows:
    print(f"  {r['word']:20s} frq={r['frq'] or 0:6d} collins={r['collins'] or 0} "
          f"| {r['zh'][:44]}")

con.close()
