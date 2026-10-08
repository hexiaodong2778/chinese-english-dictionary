# -*- coding: utf-8 -*-
"""找出清洗后变空的那 9 条，确认是否可接受。"""
import sqlite3
import sys

sys.path.insert(0, r"D:\Dictionary\build")
from clean_ipa import clean_ipa

con = sqlite3.connect(r"D:\Dictionary\dict.db")
con.row_factory = sqlite3.Row
out = []
out.append("清洗后变空的条目：")
n = 0
for r in con.execute(
        "SELECT word, phonetic, phonetic_us FROM dict "
        "WHERE (phonetic!='' OR phonetic_us!='')"):
    o1 = r["phonetic"] or ""
    o2 = r["phonetic_us"] or ""
    n1 = clean_ipa(o1)
    n2 = clean_ipa(o2)
    if (o1 and not n1) or (o2 and not n2):
        n += 1
        out.append(f"  {n}. {r['word']!r}")
        out.append(f"       英: {o1!r} → {n1!r}")
        out.append(f"       美: {o2!r} → {n2!r}")
out.append(f"  共 {n} 条")
con.close()
open(r"D:\Dictionary\build\_ipa_empty.txt", "w", encoding="utf-8").write(
    "\n".join(out))
print("ok")
