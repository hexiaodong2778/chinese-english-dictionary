# -*- coding: utf-8 -*-
"""排查三个疑点：
① Windows 里到底有没有英文语音（SAPI 注册表 vs Speech_OneCore）
② ECDICT 音标字段的真实格式（' 重音符号、. 分隔、ә 用的是哪个 Unicode）
③ ph_ok 列的含义 / 音标缺失的词长什么样
"""
import sqlite3
import sys
import winreg

sys.path.insert(0, r"D:\Dictionary\build")

out = []

# ---------- ① 英文语音到底装没装 ----------
out.append("=" * 70)
out.append("① 英文语音排查")
out.append("=" * 70)
paths = [
    (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Speech\Voices\Tokens"),
    (winreg.HKEY_LOCAL_MACHINE,
     r"SOFTWARE\Microsoft\Speech_OneCore\Voices\Tokens"),
    (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Speech\Voices\Tokens"),
]
for root, p in paths:
    rootname = "HKLM" if root == winreg.HKEY_LOCAL_MACHINE else "HKCU"
    try:
        k = winreg.OpenKey(root, p)
    except OSError as e:
        out.append(f"[{rootname}] {p}")
        out.append(f"    打不开: {e}")
        continue
    n = winreg.QueryInfoKey(k)[0]
    out.append(f"[{rootname}] {p}   子键 {n} 个")
    for i in range(n):
        sub = winreg.EnumKey(k, i)
        try:
            sk = winreg.OpenKey(k, sub)
            nm = winreg.QueryValueEx(sk, "")[0]
            lang = "?"
            try:
                att = winreg.OpenKey(sk, "Attributes")
                lang = winreg.QueryValueEx(att, "Language")[0]
            except OSError:
                pass
            out.append(f"    · {nm}   Language={lang}")
        except OSError:
            out.append(f"    · <{sub}> 读取失败")

# English 语言包是否装了语音
out.append("")
out.append("语言包/语音能力检查（HKCU\\...\\Speech_OneCore\\...）")
try:
    k = winreg.OpenKey(
        winreg.HKEY_CURRENT_USER,
        r"SOFTWARE\Microsoft\Speech_OneCore\Isolated\VoiceCapabilities")
    out.append(f"    找到 VoiceCapabilities, 子键 {winreg.QueryInfoKey(k)[0]} 个")
except OSError:
    out.append("    无 VoiceCapabilities 键")

# ---------- ② 音标字段格式细节 ----------
out.append("")
out.append("=" * 70)
out.append("② ECDICT 音标字段格式细节（决定映射表为什么出错）")
out.append("=" * 70)
con = sqlite3.connect(r"D:\Dictionary\dict.db")
con.row_factory = sqlite3.Row

# 抽样看原始字节
out.append("抽样 12 个词的原始音标字节（看清到底用的什么符号）：")
out.append(f"{'word':<12} {'phonetic 原始值':<24} Unicode 码点")
for w in ["water", "hot", "cup", "world", "girl", "but", "love", "dog",
          "not", "book", "cat", "go"]:
    r = con.execute("SELECT word, phonetic FROM dict WHERE lower=? LIMIT 1",
                    (w,)).fetchone()
    if not r or not r["phonetic"]:
        out.append(f"{w:<12} <空>")
        continue
    ph = r["phonetic"]
    cps = " ".join(f"U+{ord(c):04X}" for c in ph if ord(c) > 127)
    out.append(f"{w:<12} {ph!r:<24} {cps}")

out.append("")
out.append("关键音素的码点核对（映射表里写的 vs 库里实际的）：")
con2 = sqlite3.connect(r"D:\Dictionary\dict.db")
for label, chars in [
    ("库里 ә (U+04D9 西里尔 或 U+0259 IPA)", None),
]:
    pass
# 统计库中出现的非 ASCII 音标字符频次
out.append("库中音标里出现频次最高的非 ASCII 字符 TOP 25：")
freq = {}
rows = con.execute("SELECT phonetic FROM dict "
                   "WHERE phonetic!='' LIMIT 200000")
for r in rows:
    for c in r[0]:
        if ord(c) > 127:
            freq[c] = freq.get(c, 0) + 1
for c, n in sorted(freq.items(), key=lambda x: -x[1])[:25]:
    out.append(f"    {c!r:<8} U+{ord(c):04X}  {n:>8,}")

out.append("")
out.append("⚠ 映射表 IPA_MAP 里用到的字符码点：")
from app import Pronouncer
seen = set()
for a, b in Pronouncer.IPA_MAP:
    for c in a:
        if ord(c) > 127:
            seen.add(c)
out.append("    " + "  ".join(f"{c!r}(U+{ord(c):04X})"
                              for c in sorted(seen)))
for c in sorted(seen):
    if c not in freq:
        out.append(f"    ⚠ {c!r} U+{ord(c):04X} 在词库音标中从未出现 → 死映射")

# ---------- ③ ph_ok 与缺失情况 ----------
out.append("")
out.append("=" * 70)
out.append("③ ph_ok 列含义 / 音标缺失分布")
out.append("=" * 70)
r = con.execute("SELECT ph_ok, COUNT(*) c FROM dict GROUP BY ph_ok "
                "ORDER BY c DESC LIMIT 10").fetchall()
out.append("ph_ok 取值分布：")
for x in r:
    out.append(f"    ph_ok={x[0]!r:<8} {x[1]:>9,}")

r = con.execute(
    "SELECT COUNT(*) FROM dict WHERE (phonetic IS NULL OR phonetic='') "
    "AND lower GLOB '[a-z]*'").fetchone()[0]
out.append(f"纯英文但完全没音标的词: {r:,}")

out.append("")
out.append("有空格的多词词条（短语）的音标情况：")
r = con.execute("SELECT COUNT(*) FROM dict WHERE word LIKE '% %'").fetchone()[0]
r2 = con.execute("SELECT COUNT(*) FROM dict WHERE word LIKE '% %' "
                 "AND phonetic!=''").fetchone()[0]
out.append(f"    多词词条 {r:,}，其中有音标 {r2:,} ({r2/max(r,1)*100:.1f}%)")
out.append("    → 短语基本没音标，发音只能靠读原文")

out.append("")
out.append("音标里含 '.' 的条目（英美混写在同一个字段里）：")
r = con.execute("SELECT COUNT(*) FROM dict WHERE phonetic LIKE '%.%'"
                ).fetchone()[0]
out.append(f"    {r:,}")
out.append("示例：")
for x in con.execute("SELECT word, phonetic FROM dict "
                     "WHERE phonetic LIKE '%.%' LIMIT 8"):
    out.append(f"    {x[0]:<16} {x[1]}")

con.close()

open(r"D:\Dictionary\build\_phdetail.txt", "w",
     encoding="utf-8").write("\n".join(out))
print("ok")
