# -*- coding: utf-8 -*-
"""精确核查多语言词库到底哪一列有数据、哪一列是空的。

上一轮检查用 phonetic_us 判断"有无音标"，但多语言库可能把音标
放在 phonetic 列。必须逐列统计，才能判断界面是否会显示空白。
"""
import io
import os
import sqlite3
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

DEPLOY = r"D:\Dictionary"

for f, lang in (("dict_ja.db", "日语"), ("dict_fr.db", "法语"),
                ("dict_yue.db", "粤语")):
    p = os.path.join(DEPLOY, f)
    print("=" * 72)
    print(f"{lang}  {f}")
    print("=" * 72)
    con = sqlite3.connect(f"file:{p}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    n = con.execute("SELECT COUNT(*) FROM dict").fetchone()[0]
    print(f"总词条: {n:,}\n")

    cols = [r[1] for r in con.execute("PRAGMA table_info(dict)")]
    print(f"{'列名':16} {'非空数':>10} {'占比':>8}   示例")
    print("-" * 72)
    for c in cols:
        if c in ("id",):
            continue
        try:
            nn = con.execute(
                f"SELECT COUNT(*) FROM dict WHERE [{c}] IS NOT NULL "
                f"AND [{c}]!='' AND [{c}]!=0").fetchone()[0]
            # 取一个非空样例
            r = con.execute(
                f"SELECT [{c}] FROM dict WHERE [{c}] IS NOT NULL "
                f"AND [{c}]!='' AND [{c}]!=0 LIMIT 1").fetchone()
            sample = (str(r[0])[:34] if r else "")
            pct = nn / n * 100 if n else 0
            flag = "  " if pct > 50 else ("!!" if pct == 0 else "? ")
            print(f"{flag}{c:14} {nn:>10,} {pct:>7.1f}%   {sample}")
        except Exception as e:
            print(f"   {c:14} 查询失败: {e}")

    # 取几条完整记录看看
    print(f"\n前 3 条完整记录：")
    for r in con.execute("SELECT * FROM dict LIMIT 3"):
        d = dict(r)
        print("  " + " | ".join(
            f"{k}={str(v)[:26]}" for k, v in d.items()
            if k not in ("id", "bnc", "frq", "collins", "oxford", "ph_ok")))
    con.close()
    print()
