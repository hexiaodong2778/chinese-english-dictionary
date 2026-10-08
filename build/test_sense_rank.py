"""验证「义项精确匹配」方案：把 translation 拆成义项，判断查询词是否为独立义项。"""
import sqlite3
import re

DB = r"D:\Dictionary\build\dict.db"
con = sqlite3.connect(DB)
con.row_factory = sqlite3.Row

POS_HEAD = re.compile(
    r"^(n|v|vt|vi|a|adj|ad|adv|prep|conj|pron|num|int|interj|art|aux|abbr|"
    r"na|pl|sing|pt|pp)\.")


def split_senses(tr):
    """把 translation 拆成义项列表。

    结构：按 \\n 分词性块，每块去掉词性前缀后按 , / , 拆义项。
    同时去掉 [xxx] 这类标签。
    """
    out = []
    for block in tr.replace("\\n", "\n").split("\n"):
        b = block.strip()
        if not b:
            continue
        b = POS_HEAD.sub("", b).strip()      # 去词性前缀
        b = re.sub(r"\[[^\]]*\]", "", b)      # 去 [网络] 之类标签
        for s in re.split(r"[,，;；]", b):
            s = s.strip()
            if s:
                out.append(s)
    return out


def rank(kw, pool):
    """给候选词打分：义项精确相等 > 义项开头 > 义项包含。"""
    res = []
    for r in pool:
        senses = split_senses(r["translation"] or "")
        best = 9
        for s in senses:
            if s == kw:
                best = min(best, 0)
            elif s.startswith(kw) or s.endswith(kw):
                best = min(best, 1)
            elif kw in s:
                best = min(best, 2)
        if best < 9:
            res.append((best, r["frq"] or 999999, r["word"], senses[:4]))
    res.sort(key=lambda x: (x[0], x[1]))
    return res


for kw in ("狗", "猫", "书", "水", "美丽", "学习", "跑", "电脑"):
    rows = con.execute(
        "SELECT word, translation, frq, tag FROM dict "
        "WHERE translation LIKE ? LIMIT 4000", (f"%{kw}%",)).fetchall()
    ranked = rank(kw, rows)[:10]
    print(f"\n=== 「{kw}」 共 {len(rows)} 个候选，前 10：")
    for lvl, frq, w, senses in ranked:
        lv = {0: "精确", 1: "首尾", 2: "包含"}[lvl]
        print(f"  [{lv}] {w:18s} frq={frq:6d}  义项={senses}")

con.close()
