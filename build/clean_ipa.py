# -*- coding: utf-8 -*-
"""音标数据清洗 + 补全。

做三件事：
  ① 归一化重音符号：ASCII ' (U+0027) 与 U+02C8 混用 → 统一成 ' (U+02C8)
     注意**不能删掉重音**，否则英美重音差异就丢了。
  ② 清理英美混装/异常字段：
       · 前导 '.'（音节省略标记）整体去掉
       · 形如 "A. B." 的多段（含 "(for n.)" 这类注释）只取第一段
       · 去掉括号注释、分号后缀
       · 去掉多余空格
  ③ 用 ipa-dict 补全空缺音标。

只改 phonetic / phonetic_us 两列，并同步 ph_ok。
改完输出统计 + 备份原库。
"""
import os
import re
import shutil
import sqlite3
import sys

sys.path.insert(0, r"D:\Dictionary\build")

DB = r"D:\Dictionary\build\dict.db"
IPA_DIR = r"D:\Dictionary\build\ipa_src"
BACKUP = r"D:\Dictionary\build\dict.db.bak_before_ipa_clean"

# 重音符号归一化：把 ASCII ' 统一成 U+02C8（真正的重音符）
STRESS_ASCII = "'"
STRESS_REAL = "\u02c8"

# 音标里允许保留的字符（白名单，其余按需丢弃）
#   字母类：a-zA-Z 26 字母 + IPA 常用
OK_CHARS = set("abcdefghijklmnopqrstuvwxyz")


def clean_ipa(raw):
    """清洗单条音标。返回清洗后的串（可能为空）。

    实测（2026-09-16，全库 7,175 条含 '.' 的音标）：

      · '.' 在音标里**绝大多数是音节分隔符**（如 "ә.bri:vi'eiʃәn"），
        全库 7,224 个 '.' 里只有 1 个紧跟重音符、180 个紧跟空格。
        所以**绝不能把 '.' 当成分隔符一刀切掉** —— 那会把
        "ә.bri:vi'eiʃәn" 砍成 "ә"，把音标彻底毁掉。

      · 真正的「多读音混装」只出现在**带空格的分段**里：
          "ә'bju:s.ә'bju:z"        → 两个读音紧贴，无空格
          "'ɑ:ftә.mɑ:kit. 'æf-"    → 第二段前有空格
          "dis'æɡriɡeit. -ɡәt. -ɡeit" → 后续段以 "-" 开头（省略写法）
          "em'pæθik. .empә'θetik"  → 后续段以 "." 开头
          "karaoke: 'kærә.әuki. kærә'әuki"
        判别特征：后续段以 **空格**、或 **"." + 空格**、或 **"-"**
        开头。据此切分才安全。

      · 前导 '.' 是「音节省略标记」（".æbi'niʃiәu"），去掉即可，
        但要小心 ".." 这种（"..tʃeindʒә'biliti"）。
    """
    if not raw:
        return ""
    s = raw.strip()
    if not s:
        return ""

    # 1) 丢掉括号注释： (for n.) / (for v.) 等
    #    注意：方括号是**音标的包裹定界符**（"[ˈbʌtn]"），不是注释，
    #    所以只能"脱壳"，不能整段删除。实测有 9 条音标被方括号包着，
    #    早期版本直接删 [..] 会把这 9 条音标清成空。
    #    做法：若整串被一对括号包住，先脱掉外层括号，再做注释清理。
    s = re.sub(r"\([^)]*\)", " ", s)
    if s.startswith("[") and s.endswith("]"):
        s = s[1:-1]
    s = re.sub(r"\[[^\]]*\]", " ", s)

    # 2) 分号后面通常是另一个词的读音或说明，截掉
    if ";" in s:
        s = s.split(";")[0]

    # 3) 切掉「多读音」的后续段。
    #    只按「分隔符 + 空格」或「分隔符 + '-'」切，不碰音节分隔的 '.'。
    #    a) ". " 或 ".  " —— 点号后跟空格，是新读音的开始
    s = re.split(r"\.\s+", s)[0]
    #    b) " ." 之前 —— 空格后跟点号（" .ædvai'zi:" 形式）
    s = re.split(r"\s+\.", s)[0]
    #    c) " -xxx" —— 空格后跟连字符（"—ɡәt" / "-ni'z-" 省略写法）
    s = re.split(r"\s+-", s)[0]
    #    d) 无空格但后段以 "-" 直接开头且前面是字母（"dis'æɡriɡeit. -ɡәt" 已被 c 处理）
    #       这里处理 ".ɡәt." 这种更少见的形式：仅当点号后紧跟 "-" 时
    s = re.split(r"\.-", s)[0]

    # 4) 去掉前导 '.'（音节省略标记），可能连续多个
    s = s.lstrip(". ").strip()

    # 5) 去掉结尾的孤立点、连字符、空格
    s = s.rstrip(". -").strip()

    # 6) 归一化重音符号：ASCII ' → U+02C8（真正的重音符）
    s = s.replace(STRESS_ASCII, STRESS_REAL)

    # 7) 合并多余空格、去掉中段残留的孤立点+空格
    s = re.sub(r"\s*\.\s+", " ", s)
    s = re.sub(r"\s{2,}", " ", s).strip()
    # 8) 去掉音标两端残留的斜杠（ipa-dict 数据里有 "ˈɑɹənsən/" 这种）
    s = s.strip("/").strip()
    s = s.strip(". ")

    return s


def load_ipa():
    """载入 ipa-dict 的英美音标。"""
    ipa = {"us": {}, "uk": {}}
    for key in ("us", "uk"):
        path = os.path.join(IPA_DIR, f"en_{key}.txt")
        if not os.path.exists(path):
            continue
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.rstrip("\n")
                if not line or "\t" not in line:
                    continue
                w, ph = line.split("\t", 1)
                w = w.strip().lower()
                ph = ph.strip().strip("/").split(",")[0].strip()
                if w and ph and w not in ipa[key]:
                    ipa[key][w] = ph
    return ipa


def main():
    out = []

    # ---------- 备份 ----------
    if not os.path.exists(BACKUP):
        shutil.copy2(DB, BACKUP)
        out.append(f"已备份原库 -> {BACKUP}  "
                   f"({os.path.getsize(BACKUP):,} B)")
    else:
        out.append(f"备份已存在，跳过: {BACKUP}")

    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    # ---------- ① 清洗现有音标 ----------
    out.append("")
    out.append("=" * 70)
    out.append("① 清洗现有音标字段")
    out.append("=" * 70)

    rows = cur.execute(
        "SELECT rowid AS rid, word, phonetic, phonetic_us FROM dict "
        "WHERE (phonetic IS NOT NULL AND phonetic!='') "
        "   OR (phonetic_us IS NOT NULL AND phonetic_us!='')").fetchall()
    out.append(f"  待检查 {len(rows):,} 条")

    upd = []
    n_changed = n_stress = n_dot = n_paren = n_empty = 0
    samples = []
    for r in rows:
        old_uk = r["phonetic"] or ""
        old_us = r["phonetic_us"] or ""
        new_uk = clean_ipa(old_uk)
        new_us = clean_ipa(old_us)
        if new_uk == old_uk and new_us == old_us:
            continue
        n_changed += 1
        if STRESS_ASCII in old_uk or STRESS_ASCII in old_us:
            n_stress += 1
        if "." in old_uk or "." in old_us:
            n_dot += 1
        if "(" in old_uk or "(" in old_us:
            n_paren += 1
        if (old_uk and not new_uk) or (old_us and not new_us):
            n_empty += 1
        if len(samples) < 14:
            samples.append((r["word"], old_uk, new_uk, old_us, new_us))
        upd.append((new_uk, new_us, r["rid"]))

    out.append(f"  需修改 {n_changed:,} 条")
    out.append(f"    其中含重音符归一化 : {n_stress:,}")
    out.append(f"    其中含 '.' 分段清理 : {n_dot:,}")
    out.append(f"    其中含括号注释清理 : {n_paren:,}")
    out.append(f"    清洗后变空的       : {n_empty:,}")

    out.append("")
    out.append("  样本（词 / 旧英 / 新英 / 旧美 / 新美）:")
    for w, ouk, nuk, ous, nus in samples:
        out.append(f"    {w:<20}")
        out.append(f"        英 {ouk!r}  →  {nuk!r}")
        out.append(f"        美 {ous!r}  →  {nus!r}")

    cur.executemany(
        "UPDATE dict SET phonetic=?, phonetic_us=? WHERE rowid=?", upd)
    con.commit()
    out.append(f"  已提交 {len(upd):,} 条更新")

    # ---------- ② ph_ok 同步 ----------
    out.append("")
    out.append("=" * 70)
    out.append("② 同步 ph_ok 标记")
    out.append("=" * 70)
    cur.execute("UPDATE dict SET ph_ok=0 WHERE phonetic='' OR phonetic IS NULL")
    c0 = cur.rowcount
    cur.execute("UPDATE dict SET ph_ok=1 WHERE phonetic!='' AND phonetic IS NOT NULL")
    c1 = cur.rowcount
    con.commit()
    out.append(f"  ph_ok=0 -> {c0:,}    ph_ok=1 -> {c1:,}")

    # ---------- ③ 用 ipa-dict 补全 ----------
    out.append("")
    out.append("=" * 70)
    out.append("③ 用 ipa-dict 补全空缺音标")
    out.append("=" * 70)
    ipa = load_ipa()
    out.append(f"  ipa-dict: US {len(ipa['us']):,} 条, UK {len(ipa['uk']):,} 条")

    rows = cur.execute(
        "SELECT rowid AS rid, word FROM dict "
        "WHERE (phonetic IS NULL OR phonetic='') "
        "AND word NOT LIKE '% %' AND lower GLOB '[a-z]*'").fetchall()
    out.append(f"  待补的单词 {len(rows):,} 个")

    fills = []
    for r in rows:
        w = (r["word"] or "").strip().lower()
        uk = ipa["uk"].get(w) or ipa["us"].get(w) or ""
        us = ipa["us"].get(w) or ipa["uk"].get(w) or ""
        uk = uk.replace(STRESS_ASCII, STRESS_REAL)
        us = us.replace(STRESS_ASCII, STRESS_REAL)
        if uk or us:
            fills.append((uk, us, 1, r["rid"]))

    out.append(f"  实际能补 {len(fills):,} 个")
    if fills:
        cur.executemany(
            "UPDATE dict SET phonetic=?, phonetic_us=?, ph_ok=? WHERE rowid=?",
            fills)
        con.commit()
        out.append(f"  已提交 {len(fills):,} 条")

    out.append("")
    out.append("  补全样本:")
    for uk, us, _, rid in fills[:14]:
        w = cur.execute("SELECT word FROM dict WHERE rowid=?",
                        (rid,)).fetchone()[0]
        out.append(f"    {w:<22} 英={uk:<20} 美={us}")

    # ---------- ④ 最终统计 ----------
    out.append("")
    out.append("=" * 70)
    out.append("④ 最终覆盖率")
    out.append("=" * 70)
    tot = cur.execute("SELECT COUNT(*) FROM dict").fetchone()[0]
    has = cur.execute("SELECT COUNT(*) FROM dict "
                      "WHERE phonetic!='' AND phonetic IS NOT NULL"
                      ).fetchone()[0]
    both = cur.execute("SELECT COUNT(*) FROM dict "
                       "WHERE phonetic!='' AND phonetic_us!=''").fetchone()[0]
    diff = cur.execute("SELECT COUNT(*) FROM dict WHERE phonetic!='' "
                       "AND phonetic_us!='' AND phonetic!=phonetic_us"
                       ).fetchone()[0]
    out.append(f"  总量        : {tot:,}")
    out.append(f"  有英式音标  : {has:,}  ({has/tot*100:.1f}%)")
    out.append(f"  英美都有    : {both:,}")
    out.append(f"  英美不同    : {diff:,}  ({diff/max(both,1)*100:.1f}%)")

    # 剩余问题量
    dot = cur.execute("SELECT COUNT(*) FROM dict WHERE phonetic LIKE '%.%'"
                      ).fetchone()[0]
    paren = cur.execute("SELECT COUNT(*) FROM dict "
                        "WHERE phonetic LIKE '%(%'").fetchone()[0]
    cat = cur.execute("SELECT COUNT(*) FROM dict "
                      "WHERE phonetic GLOB '*[一-龥]*'").fetchone()[0]
    out.append("")
    out.append(f"  清洗后仍含 '.'  : {dot:,}")
    out.append(f"  清洗后仍含 '('  : {paren:,}")
    out.append(f"  含中文字符      : {cat:,}")

    con.close()
    open(r"D:\Dictionary\build\_ipa_clean.txt", "w",
         encoding="utf-8").write("\n".join(out))
    print("ok")


if __name__ == "__main__":
    main()
