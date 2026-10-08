# -*- coding: utf-8 -*-
"""构建例句库：把 Tatoeba 中英句对导入 dict.db 的 example / ex_index 表。

数据来源：https://www.manythings.org/anki/cmn-eng.zip
          （源自 Tatoeba 语料，CC-BY 2.0 (France)）
格式：英文 <TAB> 中文 <TAB> 出处，共 32,028 行。中文为繁体，需转简体。

表设计：
  example(id, en, zh, n_en, n_zh)
      —— 句子正文；n_en/n_zh 为词数/字数，用于排序（短句优先）。
  ex_index(word, ex_id)
      —— 单词 -> 例句 倒排索引，支撑「查某词的所有例句」。

排序原则（渲染时取前 N 条）：
  1) 句子越短越优先（短句更易读，也更能体现该词的用法）
  2) 英文长度接近 40-70 字符为最佳区间
"""
import os
import re
import sqlite3
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

BUILD = r"D:\Dictionary\build"
SRC = os.path.join(BUILD, "anki_cmn", "cmn.txt")
DB = os.path.join(BUILD, "dict.db")

# 每词保留的例句上限（控制体积）
MAX_PER_WORD = 6
# 只索引「有意义的词」：长度 >= 2 的字母词
WORD_RE = re.compile(r"[A-Za-z][A-Za-z'-]*")
# 过长的句子不适合做词典例句
MAX_EN_LEN = 160
MAX_ZH_LEN = 90


def main():
    if not os.path.exists(SRC):
        print(f"缺少语料文件: {SRC}")
        return 1

    try:
        from opencc import OpenCC
        cc = OpenCC("t2s")
        conv = cc.convert
    except Exception:
        print("警告：opencc 不可用，中文将保留繁体")
        conv = lambda s: s

    # ---------- 1. 读取与清洗 ----------
    print("读取语料…")
    pairs = []
    seen = set()
    with open(SRC, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.rstrip("\n")
            if not line.strip():
                continue
            parts = line.split("\t")
            if len(parts) < 2:
                continue
            en = parts[0].strip()
            zh = conv(parts[1].strip())
            if not en or not zh:
                continue
            # 清洗：去掉多余空白、统一引号
            en = re.sub(r"\s+", " ", en)
            zh = re.sub(r"\s+", "", zh)
            if len(en) > MAX_EN_LEN or len(zh) > MAX_ZH_LEN:
                continue
            # 必须含至少一个字母词
            if not WORD_RE.search(en):
                continue
            # 去重（同一对句子可能重复）
            key = (en.lower(), zh)
            if key in seen:
                continue
            seen.add(key)
            pairs.append((en, zh))
    print(f"  有效句对: {len(pairs):,}")

    # ---------- 2. 建表 ----------
    con = sqlite3.connect(DB)
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("DROP TABLE IF EXISTS example")
    con.execute("DROP TABLE IF EXISTS ex_index")
    con.execute(
        "CREATE TABLE example ("
        "  id INTEGER PRIMARY KEY,"
        "  en TEXT NOT NULL,"
        "  zh TEXT NOT NULL,"
        "  n_en INTEGER,"
        "  n_zh INTEGER"
        ")"
    )
    con.execute(
        "CREATE TABLE ex_index ("
        "  word TEXT NOT NULL,"
        "  ex_id INTEGER NOT NULL"
        ")"
    )

    print("写入句子…")
    ex_rows = []
    for i, (en, zh) in enumerate(pairs, 1):
        ex_rows.append((i, en, zh, len(WORD_RE.findall(en)), len(zh)))
    con.executemany(
        "INSERT INTO example (id,en,zh,n_en,n_zh) VALUES (?,?,?,?,?)", ex_rows
    )
    print(f"  example 表: {len(ex_rows):,} 行")

    # ---------- 3. 建倒排索引 ----------
    print("建倒排索引…")
    idx = {}      # word -> [(ex_id, n_en, en_len)]
    for ex_id, en, zh, n_en, n_zh in ex_rows:
        words = set(w.lower() for w in WORD_RE.findall(en))
        for w in words:
            if len(w) < 2:
                continue
            idx.setdefault(w, []).append((ex_id, n_en, len(en)))

    # 每词按「句子短优先、词数少优先」排序后截断
    rows = []
    for w, lst in idx.items():
        lst.sort(key=lambda t: (t[2], t[1]))
        for ex_id, _, _ in lst[:MAX_PER_WORD]:
            rows.append((w, ex_id))
    con.executemany("INSERT INTO ex_index (word,ex_id) VALUES (?,?)", rows)
    con.execute("CREATE INDEX ix_ex_index_word ON ex_index(word)")
    con.execute("CREATE INDEX ix_ex_index_ex ON ex_index(ex_id)")
    con.execute("CREATE INDEX ix_example_id ON example(id)")
    print(f"  ex_index 表: {len(rows):,} 行，覆盖 {len(idx):,} 个词")

    # ---------- 4. 统计与收尾 ----------
    con.commit()
    con.execute("ANALYZE")
    con.commit()

    # 记入 meta，供界面显示
    for k, v in [("example_count", len(ex_rows)),
                 ("example_words", len(idx)),
                 ("example_source", "Tatoeba (CC-BY 2.0)")]:
        con.execute("INSERT OR REPLACE INTO meta (k,v) VALUES (?,?)", (k, str(v)))
    con.commit()

    tot = con.execute("SELECT COUNT(*) FROM example").fetchone()[0]
    words = con.execute("SELECT COUNT(*) FROM ex_index").fetchone()[0]
    print(f"\n完成：例句 {tot:,} 条，索引 {words:,} 条")
    # 抽样验证
    print("\n抽样验证（查 dog / water / abandon 的例句）:")
    for w in ("dog", "water", "abandon"):
        rs = con.execute(
            "SELECT e.en, e.zh FROM ex_index x JOIN example e ON e.id=x.ex_id "
            "WHERE x.word=? ORDER BY e.n_en LIMIT 3", (w,)).fetchall()
        print(f"  [{w}] 共 {len(rs)} 条:") 
        for en, zh in rs:
            print(f"      {en}")
            print(f"      {zh}")
    con.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
