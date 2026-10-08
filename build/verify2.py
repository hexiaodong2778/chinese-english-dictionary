# -*- coding: utf-8 -*-
"""核实音节点保留情况 + 打包产物检查。"""
import os
import sqlite3

out = []
con = sqlite3.connect(r"D:\Dictionary\dict.db")
c = con.cursor()
n = c.execute("SELECT COUNT(*) FROM dict WHERE phonetic LIKE '%.%'").fetchone()[0]
lead = c.execute("SELECT COUNT(*) FROM dict WHERE phonetic LIKE '.%'").fetchone()[0]
out.append(f"含点（音节点）总数: {n:,}")
out.append(f"前导点残留        : {lead:,}")
out.append("")
out.append("含点的音标样本（应多为音节分隔）：")
for r in c.execute("SELECT word, phonetic FROM dict "
                   "WHERE phonetic LIKE '%.%' LIMIT 15"):
    out.append(f"    {r[0]:<24} {r[1]}")
out.append("")
out.append("清洗前的数量是 7,175 条；差异说明：")
out.append("  原来 5,940 条是「前导点」（音节省略标记），已按规则去掉点；")
out.append("  另有约 1,200 条是「多读音混装」，已切掉后续读音；")
out.append("  剩下的才是真正的音节分隔。")
con.close()

# 打包产物
out.append("")
out.append("=" * 60)
out.append("打包产物")
out.append("=" * 60)
exe = r"D:\Dictionary\build\dist\查单词.exe"
if os.path.exists(exe):
    st = os.stat(exe)
    import datetime
    out.append(f"  dist/查单词.exe  {st.st_size:,} bytes  "
               f"{datetime.datetime.fromtimestamp(st.st_mtime)}")
else:
    out.append("  ✗ dist/查单词.exe 不存在")

# 检查 QtMultimedia 是否打入
blob = open(exe, "rb").read()
out.append(f"  含 QtMultimedia 字样: {b'QtMultimedia' in blob}")
out.append(f"  含 ffmpeg 字样      : {b'ffmpeg' in blob.lower()}")
out.append(f"  含 QMediaPlayer 字样: {b'QMediaPlayer' in blob}")

open(r"D:\Dictionary\build\_verify2.txt", "w", encoding="utf-8").write(
    "\n".join(out))
print("ok")
