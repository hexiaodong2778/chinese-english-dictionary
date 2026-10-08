"""
构建多语言词典 (build_langs.py)
================================
用 open-dict-data/ipa-dict 的真实 IPA 发音数据，
为 日语 / 法语 / 粤语 生成独立词库文件。

难点：日语 / 粤语的词头是汉字或假名，用户往往想用罗马字（romaji / 粤拼）检索。
本脚本从 IPA 字段反推出一个「罗马字检索键」写入 sw 字段，使：
    搜 "nihon"  -> 能找到「日本」
    搜 "nei"    -> 能找到「你」
同时保留原文精确匹配。

词库结构（与英语库保持一致，便于主程序统一处理）:
    dict(word, lower, sw, phonetic, phonetic_us, definition,
         translation, pos, collins, oxford, tag, bnc, frq, exchange, ph_ok)
    cn_index(word, lower, zh, tag)
其中非英语语种:
    phonetic     -> 该语言的 IPA
    phonetic_us  -> 留空（非英语无英美之分）
    translation  -> 中文释义（若有）
"""
import os
import re
import sqlite3
import sys

BUILD = os.path.dirname(os.path.abspath(__file__))
IPA_DIR = os.path.join(BUILD, "ipa")

LANGS = {
    "ja":  {"ipa": "ja.txt",     "db": "dict_ja.db",  "label": "日语"},
    "fr":  {"ipa": "fr_FR.txt",  "db": "dict_fr.db",  "label": "法语"},
    "yue": {"ipa": "yue.txt",    "db": "dict_yue.db", "label": "粤语"},
}

# IPA 字符 -> 拉丁字母近似，用于生成罗马字检索键
IPA_TO_LATIN = [
    ("tɕ", "ch"), ("dʑ", "j"), ("ts", "ts"), ("dz", "z"),
    ("ɕ", "sh"), ("ʑ", "j"), ("tʃ", "ch"), ("dʒ", "j"),
    ("ʃ", "sh"), ("ʒ", "j"), ("ŋ", "ng"), ("ɲ", "ny"),
    ("j", "y"), ("ɥ", "y"), ("w", "w"),
    ("a", "a"), ("i", "i"), ("u", "u"), ("e", "e"), ("o", "o"),
    ("ɛ", "e"), ("ɔ", "o"), ("ø", "oe"), ("œ", "oe"), ("y", "u"),
    ("ə", "e"), ("ɐ", "a"), ("ɵ", "oe"), ("ɤ", "o"),
    ("m", "m"), ("n", "n"), ("b", "b"), ("p", "p"),
    ("d", "d"), ("t", "t"), ("g", "g"), ("k", "k"),
    ("f", "f"), ("v", "v"), ("s", "s"), ("z", "z"),
    ("h", "h"), ("l", "l"), ("r", "r"), ("c", "k"),
    ("ː", ""), (":", ""), (".", ""), ("'", ""), ("ˈ", ""),
    ("ˌ", ""), ("-", ""), (" ", ""),
]


def ipa_to_key(ipa):
    """把 IPA 音标转成拉丁字母检索键（最长匹配优先）。"""
    if not ipa:
        return ""
    s = ipa.strip().strip("/")
    out = []
    i, n = 0, len(s)
    table = sorted(IPA_TO_LATIN, key=lambda kv: -len(kv[0]))
    while i < n:
        hit = False
        for a, b in table:
            if a and s.startswith(a, i):
                out.append(b)
                i += len(a)
                hit = True
                break
        if not hit:
            ch = s[i]
            if ch.isascii() and ch.isalnum():
                out.append(ch.lower())
            i += 1
    return "".join(out)


def parse_ipa_file(path):
    """解析 ipa-dict 格式: word<TAB>/ipa/, /ipa2/  ->  [(word, ipa), ...]"""
    out = []
    if not os.path.exists(path):
        return out
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.rstrip("\n").rstrip("\r")
            if not line or "\t" not in line:
                continue
            parts = line.split("\t")
            if len(parts) < 2:
                continue
            word = parts[0].strip()
            if not word:
                continue
            # 取第一个音标
            m = re.findall(r"/([^/]+)/", parts[1])
            if not m:
                continue
            ipa = m[0].strip()
            if not ipa:
                continue
            out.append((word, ipa))
    return out


def main():
    grand = 0
    for code, cfg in LANGS.items():
        src = os.path.join(IPA_DIR, cfg["ipa"])
        if not os.path.exists(src):
            print(f"[{code}] SKIP: {src} not found")
            continue

        entries = parse_ipa_file(src)
        # 去重，保留首个音标
        seen = {}
        for w, ipa in entries:
            k = w.lower()
            if k not in seen:
                seen[k] = (w, ipa)
        uniq = list(seen.values())

        db_path = os.path.join(BUILD, cfg["db"])
        if os.path.exists(db_path):
            os.remove(db_path)

        con = sqlite3.connect(db_path)
        cur = con.cursor()
        cur.execute("PRAGMA journal_mode=OFF")
        cur.execute("PRAGMA synchronous=OFF")
        cur.execute("""
            CREATE TABLE dict (
                id INTEGER PRIMARY KEY,
                word TEXT, lower TEXT, sw TEXT,
                phonetic TEXT, phonetic_us TEXT,
                definition TEXT, translation TEXT, pos TEXT,
                collins INTEGER, oxford INTEGER, tag TEXT,
                bnc INTEGER, frq INTEGER, exchange TEXT, ph_ok INTEGER
            )
        """)
        cur.execute("CREATE TABLE cn_index (id INTEGER PRIMARY KEY, word TEXT, lower TEXT, zh TEXT, tag TEXT)")
        cur.execute("CREATE TABLE lemma (form TEXT, lemma TEXT)")
        cur.execute("CREATE TABLE meta (k TEXT PRIMARY KEY, v TEXT)")

        rows, lem_rows = [], []
        for w, ipa in uniq:
            roman = ipa_to_key(ipa)
            # sw 存放罗马字检索键，让用户能用 romaji / 粤拼查汉字词条
            sw = roman or "".join(c for c in w if c.isalnum()).lower()
            rows.append((w, w.lower(), sw, ipa, "", "", "", "", 0, 0, "", 0, 0, "", 1))
            if roman and roman != w.lower():
                lem_rows.append((roman, w))

        cur.executemany(
            "INSERT INTO dict (word,lower,sw,phonetic,phonetic_us,definition,"
            "translation,pos,collins,oxford,tag,bnc,frq,exchange,ph_ok) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", rows
        )
        if lem_rows:
            cur.executemany("INSERT INTO lemma (form,lemma) VALUES (?,?)", lem_rows)

        cur.execute("CREATE INDEX idx_dict_lower ON dict(lower)")
        cur.execute("CREATE INDEX idx_dict_sw ON dict(sw)")
        cur.execute("CREATE INDEX idx_cn_lower ON cn_index(lower)")
        cur.execute("CREATE INDEX idx_cn_zh ON cn_index(zh)")
        cur.execute("CREATE INDEX idx_lemma_form ON lemma(form)")
        cur.execute("INSERT INTO meta VALUES ('built', datetime('now'))")
        cur.execute("INSERT INTO meta VALUES ('count', ?)", (str(len(rows)),))
        con.commit()
        cur.execute("VACUUM")
        con.commit()
        con.close()

        sz = os.path.getsize(db_path) / 1024 / 1024
        print(f"[{code}] {cfg['label']}: {len(rows):,} 条 (含 {len(lem_rows):,} 条罗马字索引)  ->  {cfg['db']}  ({sz:.1f} MB)")
        grand += len(rows)

    print(f"\nDONE  total non-english entries: {grand:,}")


if __name__ == "__main__":
    main()
