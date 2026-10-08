"""
构建离线词典数据库 (build_dict.py)
=================================
把 ECDICT 的 ecdict.csv 转换为查询友好的 SQLite 数据库，
并补全高考/中考等考纲标签、生成中译英反查索引、预计算英美音标。

用法: python build_dict.py
输出: D:\Dictionary\build\dict.db
"""
import csv
import os
import re
import sqlite3
import sys
import time

BUILD = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(BUILD, "ecdict.csv")
DB_PATH = os.path.join(BUILD, "dict.db")
LEMMA_PATH = os.path.join(BUILD, "lemma.en.txt")

# ---------------------------------------------------------------- 音标修复
# ecdict.csv 是混合编码文件：部分行的 IPA 非 ASCII 字符丢失（如 go 的音标
# 应为 ɡəʊ，源数据却是 "gou"）。这里按上下文修复可恢复的情况，无法恢复的
# 标记为无效，避免展示错误音标。
_VOWEL_PAIRS = {"ou": "əʊ", "ou": "oʊ"}

# 常见的 ASCII 音标串 -> 正确 IPA
PHONETIC_REPAIRS = {
    "gou": "ɡəʊ",
    "nou": "nəʊ",
    "sou": "səʊ",
    "tou": "təʊ",
    "dou": "dəʊ",
    "lou": "ləʊ",
    "rou": "rəʊ",
    "mou": "məʊ",
    "bou": "bəʊ",
    "həum": "həʊm",
    "houm": "həʊm",
    "gəul": "ɡəʊl",
    "goul": "ɡəʊl",
}


def looks_corrupted(ph):
    """判断音标是否明显因编码丢失而残缺。

    注意：ECDICT 中大量音标本就是 ASCII 写法（如 twi:n / eid / 'seli:），
    这些是合法数据，不能误判。只有下列情况才算损坏：
      · 含反斜杠等残留字符
      · 裸 "ou" 而缺少 ə / ʊ（典型的 ə 被吞掉，如 go -> "gou"）
    """
    if not ph:
        return True
    if "\\" in ph:
        return True
    if "ou" in ph and "ə" not in ph and "ʊ" not in ph:
        return True
    return False


def clean_phonetic(ph):
    """清理并尽量修复音标；返回 (英式, 是否可信)。"""
    if not ph:
        return "", False
    s = ph.strip()
    # 去掉反斜杠残留
    s = s.replace("\\", "")
    # 已知修复表
    low = s.lower()
    if low in PHONETIC_REPAIRS:
        return PHONETIC_REPAIRS[low], True
    if looks_corrupted(s):
        return "", False
    return s, True


# ---------------------------------------------------------------- 音标转换
# ECDICT 的 phonetic 是英式音标（DJ 音标风格），这里按规则推导美式音标（KK 风格）
# 主要差异集中在几个固定模式上，覆盖日常词汇已经足够。
US_RULES = [
    # 非重读/重读的 ɒ -> ɑ:（英 ɒ，美 ɑ）
    (r"ɒ", "ɑ"),
    # 英式 əʊ -> 美式 oʊ  (go, home)
    (r"əʊ", "oʊ"),
    # 英式 əu -> 美式 ou
    (r"əu", "ou"),
    # 英式 ɑː -> 美式 æ（英式 father-class 中的部分词，如 ask, dance）
    (r"ɑː", "ɑː"),
    # 英式 ɔː -> 美式 ɔː 保持不变；但 ɒ 与 ɔː 合并趋势
    (r"aɪ", "aɪ"),
    (r"eɪ", "eɪ"),
]


def to_us_phonetic(ph):
    """把英式音标近似转换为美式音标（KK 风格）。

    ECDICT 的 phonetic 字段是英式（DJ）音标，且长音多用 ASCII 冒号 ":" 表示。
    英美音标的主要系统性差异：
      1. 英 əʊ  -> 美 oʊ      (go, home, no)          [含 ASCII 写法 ou]
      2. 英 ɒ   -> 美 ɑ       (hot, box, water)
      3. 英 ɑː  -> 美 æ       (ask, dance, class)
      4. 英 ɜː  -> 美 ɝ       (bird, work)
      5. 词尾 -er 卷舌         (teacher -> ɚ)
      6. 美式长音符号常省略
    """
    if not ph:
        return ""
    s = ph

    # ASCII 长音冒号统一为 IPA 长音符，便于后续规则处理
    s = s.replace(":", "ː")

    # 双元音与单元音的英美对应
    s = s.replace("əʊ", "oʊ")   # go, home
    s = s.replace("ɒ", "ɑ")     # hot, box
    s = s.replace("ɑː", "æ")    # ask, dance, class
    s = s.replace("ɜː", "ɝ")    # bird, work
    s = s.replace("ɜ", "ɝ")
    s = s.replace("ɔː", "ɔ")    # law, thought（美式常省略长音）
    s = s.replace("iː", "i")    # see
    s = s.replace("uː", "u")    # food

    # 卷舌音
    s = s.replace("ər", "ɚ")
    s = s.replace("ɜr", "ɝ")

    return s


# ---------------------------------------------------------------- 标签补全
# ECDICT 自带的 gk 标签只覆盖 3677 条，会漏掉大量真正的高考词汇。
# 这里用词频 + 词汇难度特征做启发式补全：高频且长度适中的常见词列为高考词。
def is_common_word(word, bnc, frq, collins, oxford):
    """判断是否为高中阶段应掌握的常见词。"""
    if not word or len(word) > 14:
        return False
    if "-" in word or " " in word:
        return False
    try:
        b = int(bnc) if bnc else 0
    except ValueError:
        b = 0
    try:
        f = int(frq) if frq else 0
    except ValueError:
        f = 0
    rank = min([x for x in (b, f) if x > 0], default=0)
    if rank == 0:
        return False
    # 核心依据：词频排名靠前 + 柯林斯星级或牛津3000
    if rank <= 6000 and (collins or oxford):
        return True
    if rank <= 3500:
        return True
    return False


DEMO_TAG_ORDER = ["zk", "gk", "cet4", "cet6", "ky", "toefl", "ielts", "gre"]


def main():
    if not os.path.exists(CSV_PATH):
        print("ERROR: ecdict.csv not found at", CSV_PATH)
        sys.exit(1)

    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("PRAGMA journal_mode=OFF")
    cur.execute("PRAGMA synchronous=OFF")

    cur.execute(
        """
        CREATE TABLE dict (
            id        INTEGER PRIMARY KEY,
            word      TEXT,
            lower     TEXT,
            sw        TEXT,
            phonetic  TEXT,
            phonetic_us TEXT,
            definition TEXT,
            translation TEXT,
            pos       TEXT,
            collins   INTEGER,
            oxford    INTEGER,
            tag       TEXT,
            bnc       INTEGER,
            frq       INTEGER,
            exchange  TEXT,
            ph_ok     INTEGER
        )
        """
    )
    # 中译英反查索引表
    cur.execute(
        """
        CREATE TABLE cn_index (
            id       INTEGER PRIMARY KEY,
            word     TEXT,
            lower    TEXT,
            zh       TEXT,
            tag      TEXT
        )
        """
    )
    # 词形还原表
    cur.execute("CREATE TABLE lemma (form TEXT, lemma TEXT)")
    cur.execute("CREATE TABLE meta (k TEXT PRIMARY KEY, v TEXT)")

    t0 = time.time()
    n = 0
    cn_rows = []
    batch = []
    BATCH = 5000

    with open(CSV_PATH, "r", encoding="utf-8", errors="replace", newline="") as f:
        rd = csv.reader(f)
        hdr = next(rd)
        ix = {h: i for i, h in enumerate(hdr)}

        def g(row, key):
            i = ix.get(key)
            if i is None or i >= len(row):
                return ""
            return row[i]

        for row in rd:
            word = g(row, "word").strip()
            if not word:
                continue
            n += 1
            lower = word.lower()
            sw = "".join(c for c in word if c.isalnum()).lower()
            raw_ph = g(row, "phonetic").strip()
            ph, ph_ok = clean_phonetic(raw_ph)
            ph_us = to_us_phonetic(ph) if ph else ""
            definition = g(row, "definition")
            translation = g(row, "translation")
            pos = g(row, "pos")
            tag = g(row, "tag").strip()

            try:
                collins = int(g(row, "collins") or 0)
            except ValueError:
                collins = 0
            try:
                oxford = int(g(row, "oxford") or 0)
            except ValueError:
                oxford = 0
            try:
                bnc = int(g(row, "bnc") or 0)
            except ValueError:
                bnc = 0
            try:
                frq = int(g(row, "frq") or 0)
            except ValueError:
                frq = 0

            tags = set(tag.replace(",", " ").split())

            # ---- 标签补全：给真正的高频常见词打上 gk，让高考词典能查到 ----
            if "gk" not in tags and is_common_word(word, bnc, frq, collins, oxford):
                tags.add("gk")
            # 高考词通常也在中考范围外的高频词里；这里只补 gk 以免过度膨胀

            tag_out = " ".join(t for t in DEMO_TAG_ORDER if t in tags)

            batch.append(
                (word, lower, sw, ph, ph_us, definition, translation, pos,
                 collins, oxford, tag_out, bnc, frq, g(row, "exchange"),
                 1 if ph_ok else 0)
            )

            # ---- 中译英：把中文释义拆成可检索的条目 ----
            if translation:
                cn = re.sub(r"\\n", " ", translation)
                cn = re.sub(r"\s+", " ", cn).strip()
                # 去掉词性前缀，保留释义主体
                cn_body = re.sub(r"^[a-zA-Z.]+\s*", "", cn)
                if cn_body:
                    cn_rows.append((word, lower, cn_body[:400], tag_out))

            if len(batch) >= BATCH:
                cur.executemany(
                    "INSERT INTO dict (word,lower,sw,phonetic,phonetic_us,definition,"
                    "translation,pos,collins,oxford,tag,bnc,frq,exchange,ph_ok) "
                    "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    batch,
                )
                batch.clear()
            if len(cn_rows) >= BATCH:
                cur.executemany(
                    "INSERT INTO cn_index (word,lower,zh,tag) VALUES (?,?,?,?)", cn_rows
                )
                cn_rows.clear()

            if n % 100000 == 0:
                print(f"  processed {n} ...", flush=True)

    if batch:
        cur.executemany(
            "INSERT INTO dict (word,lower,sw,phonetic,phonetic_us,definition,"
            "translation,pos,collins,oxford,tag,bnc,frq,exchange,ph_ok) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            batch,
        )
    if cn_rows:
        cur.executemany(
            "INSERT INTO cn_index (word,lower,zh,tag) VALUES (?,?,?,?)", cn_rows
        )

    print(f"  dict rows: {n}, cn_index rows: {cur.execute('SELECT COUNT(*) FROM cn_index').fetchone()[0]}")

    # ---------------- 词形还原  ----------------
    # lemma.en.txt 的真实格式为：  lemma/count -> form1,form2,form3
    lem = 0
    if os.path.exists(LEMMA_PATH):
        lb = []
        seen = set()
        with open(LEMMA_PATH, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith(";"):
                    continue
                if "->" not in line:
                    continue
                head, _, tail = line.partition("->")
                # 去掉词频计数
                base = head.split("/")[0].strip().strip("_").lower()
                if not base:
                    continue
                key = (base, base)
                if key not in seen:
                    seen.add(key)
                    lb.append(key)
                for form in tail.split(","):
                    form = form.strip().strip("_").lower()
                    if not form or form == base:
                        continue
                    key = (form, base)
                    if key in seen:
                        continue
                    seen.add(key)
                    lb.append(key)
                    lem += 1
                if len(lb) >= BATCH:
                    cur.executemany("INSERT INTO lemma (form,lemma) VALUES (?,?)", lb)
                    lb.clear()
        if lb:
            cur.executemany("INSERT INTO lemma (form,lemma) VALUES (?,?)", lb)
        del seen
    print(f"  lemma rows: {cur.execute('SELECT COUNT(*) FROM lemma').fetchone()[0]}")

    # ---------------- 索引 ----------------
    print("  building indexes ...", flush=True)
    cur.execute("CREATE INDEX idx_dict_lower ON dict(lower)")
    cur.execute("CREATE INDEX idx_dict_sw ON dict(sw)")
    cur.execute("CREATE INDEX idx_cn_lower ON cn_index(lower)")
    cur.execute("CREATE INDEX idx_cn_zh ON cn_index(zh)")
    cur.execute("CREATE INDEX idx_lemma_form ON lemma(form)")
    cur.execute("CREATE INDEX idx_dict_bnc ON dict(bnc)")
    cur.execute("CREATE INDEX idx_dict_frq ON dict(frq)")

    cur.execute("INSERT INTO meta VALUES ('built', ?)", (time.strftime("%Y-%m-%d %H:%M:%S"),))
    cur.execute("INSERT INTO meta VALUES ('count', ?)", (str(n),))
    con.commit()

    print("  optimizing ...", flush=True)
    cur.execute("ANALYZE")
    cur.execute("VACUUM")
    con.commit()
    con.close()

    size = os.path.getsize(DB_PATH) / 1024 / 1024
    print(f"DONE  db={DB_PATH}  size={size:.1f} MB  rows={n}  secs={time.time()-t0:.1f}")


if __name__ == "__main__":
    main()
