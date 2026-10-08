# -*- coding: utf-8 -*-
"""扩充例句库：从 Tatoeba 官方全量导出中抽取「英语句子 + 中文译文」句对。

相比 build_examples.py（用的 manythings.org 的 anki 小包，只有 3.2 万句），
这里直接解 Tatoeba 官方周更导出：

    eng_sentences.tsv.bz2   24.8 MB   英文句子     id \t eng \t 文本
    cmn_sentences.tsv.bz2    1.2 MB   中文句子     id \t cmn \t 文本
    links.tar.bz2          149.7 MB   句对链接     id \t 译文id

links 是双向的（1->77 与 77->1 都会出现），所以只要取
「一边是 eng、另一边是 cmn」的链接即可，天然拿到两份，去重即可。

产物：写入 dict.db 的 example / ex_index 两张表（与 build_examples.py 同构），
      界面层无需区分来源。

许可：Tatoeba 导出数据为 CC-BY 2.0 FR，可自由使用与再分发。
"""
import bz2
import io
import os
import re
import sqlite3
import sys
import tarfile
import time

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

BUILD = r"D:\Dictionary\build"
TAT = os.path.join(BUILD, "tatoeba")
DB = os.path.join(BUILD, "dict.db")

ENG_BZ2 = os.path.join(TAT, "eng_sentences.tsv.bz2")
CMN_BZ2 = os.path.join(TAT, "cmn_sentences.tsv.bz2")
LINKS_BZ2 = os.path.join(TAT, "links.tar.bz2")

# 每词保留的例句上限。相比小包的 6 条放宽到 12，
# 因为官方导出覆盖更广，常用词能选到更贴切的短句。
MAX_PER_WORD = 12

WORD_RE = re.compile(r"[A-Za-z][A-Za-z'-]*")

# 长度门槛：太长的句子不适合做词典例句，也会显著撑大库体积
MAX_EN_LEN = 150
MAX_ZH_LEN = 80
MAX_EN_WORDS = 26

# 中文句子里含大量非中文内容（如纯英文、纯符号）的丢弃
ZH_CHAR_RE = re.compile(r"[\u4e00-\u9fff]")


def read_tsv_bz2(path):
    """读 Tatoeba 的 per_language 导出：id \t lang \t text"""
    out = {}
    with bz2.open(path, "rt", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.rstrip("\n")
            if not line:
                continue
            parts = line.split("\t")
            if len(parts) < 3:
                continue
            try:
                sid = int(parts[0])
            except ValueError:
                continue
            out[sid] = parts[2]
    return out


def iter_links(path):
    """流式读取 links.tar.bz2 里的 links.csv（id \t translation_id）。"""
    with tarfile.open(path, "r:bz2") as tar:
        name = None
        for m in tar.getmembers():
            if m.name.endswith("links.csv"):
                name = m
                break
        if name is None:
            raise RuntimeError("links.tar.bz2 里找不到 links.csv")
        f = tar.extractfile(name)
        for raw in io.TextIOWrapper(f, encoding="utf-8", errors="replace"):
            raw = raw.rstrip("\n")
            if not raw:
                continue
            p = raw.split("\t")
            if len(p) < 2:
                continue
            try:
                yield int(p[0]), int(p[1])
            except ValueError:
                continue


def main():
    for p in (ENG_BZ2, CMN_BZ2, LINKS_BZ2):
        if not os.path.exists(p):
            print(f"缺少文件: {p}")
            return 1

    try:
        from opencc import OpenCC
        cc = OpenCC("t2s")
        conv = cc.convert
    except Exception:
        print("警告：opencc 不可用，中文将保留繁体")
        conv = lambda s: s

    t0 = time.time()

    print("读取英文句子…")
    eng = read_tsv_bz2(ENG_BZ2)
    print(f"  {len(eng):,} 句")

    print("读取中文句子…")
    cmn = read_tsv_bz2(CMN_BZ2)
    print(f"  {len(cmn):,} 句")

    # ---------- 抽取句对 ----------
    print("扫描句对链接…")
    pairs = []
    seen = set()
    n_link = 0
    for a, b in iter_links(LINKS_BZ2):
        n_link += 1
        # 只要 eng <-> cmn 这一种组合
        en_txt = None
        zh_txt = None
        if a in eng and b in cmn:
            en_txt, zh_txt = eng[a], cmn[b]
        elif a in cmn and b in eng:
            en_txt, zh_txt = eng[b], cmn[a]
        else:
            continue

        en = re.sub(r"\s+", " ", en_txt).strip()
        zh = re.sub(r"\s+", "", zh_txt).strip()
        if not en or not zh:
            continue
        if len(en) > MAX_EN_LEN or len(zh) > MAX_ZH_LEN:
            continue
        if len(WORD_RE.findall(en)) > MAX_EN_WORDS:
            continue
        # 中文句至少要有几个汉字，否则多半是符号串
        if len(ZH_CHAR_RE.findall(zh)) < 2:
            continue
        if not WORD_RE.search(en):
            continue
        key = (en.lower(), zh)
        if key in seen:
            continue
        seen.add(key)
        pairs.append((en, conv(zh)))
    print(f"  扫描 {n_link:,} 条链接，得到 {len(pairs):,} 个去重句对"
          f"  ({time.time() - t0:.0f}s)")

    # ---------- 写入数据库 ----------
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

    # ---------- 倒排索引 ----------
    print("建倒排索引…")
    idx = {}
    for ex_id, en, zh, n_en, n_zh in ex_rows:
        for w in set(x.lower() for x in WORD_RE.findall(en)):
            if len(w) < 2:
                continue
            idx.setdefault(w, []).append((ex_id, n_en, len(en), n_zh))

    rows = []
    for w, lst in idx.items():
        # 排序原则：不要最短的，要「信息量最合适」的。
        # 实测纯按长度升序会选出 "Run!" / "I run." 这类太单薄的句子，
        # 当成词典例句没有参考价值。因此定义一个理想区间：
        #   · 英文 6-14 词最合适（短到能读完，长到有完整语境）
        #   · 中文 8-40 字
        # 用「与理想区间中心的距离」排序，短于/长于区间都会被推后。
        def rank(t, _w=w):
            ex_id, n_en, en_len, n_zh = t
            if n_en < 6:
                d_en = (6 - n_en) * 3          # 过短重罚
            elif n_en > 14:
                d_en = (n_en - 14) * 2
            else:
                d_en = 0
            # 中文翻译也要够长，太短的译文说明句子本身单薄
            d_zh = max(0, 8 - n_zh) * 2
            return (d_en + d_zh, abs(en_len - 55), n_en)

        lst.sort(key=rank)
        for ex_id, _, _, _ in lst[:MAX_PER_WORD]:
            rows.append((w, ex_id))
    con.executemany("INSERT INTO ex_index (word,ex_id) VALUES (?,?)", rows)
    con.execute("CREATE INDEX ix_ex_index_word ON ex_index(word)")
    con.execute("CREATE INDEX ix_ex_index_ex ON ex_index(ex_id)")
    con.execute("CREATE INDEX ix_example_id ON example(id)")
    print(f"  ex_index 表: {len(rows):,} 行，覆盖 {len(idx):,} 个词")

    con.commit()
    con.execute("ANALYZE")
    con.commit()

    for k, v in [("example_count", len(ex_rows)),
                 ("example_words", len(idx)),
                 ("example_source", "Tatoeba (CC-BY 2.0 FR)")]:
        con.execute("INSERT OR REPLACE INTO meta (k,v) VALUES (?,?)", (k, str(v)))
    con.commit()

    # ---------- 抽样验证 ----------
    print("\n抽样验证:")
    for w in ("dog", "water", "abandon", "government", "run", "beautiful"):
        rs = con.execute(
            "SELECT e.en, e.zh FROM ex_index x JOIN example e ON e.id=x.ex_id "
            "WHERE x.word=? ORDER BY e.n_en LIMIT 3", (w,)).fetchall()
        print(f"  [{w}] {len(rs)} 条")
        for en, zh in rs:
            print(f"      {en}")
            print(f"      {zh}")

    db_mb = os.path.getsize(DB) / 1048576
    print(f"\n完成。dict.db = {db_mb:.0f} MB，总耗时 {time.time() - t0:.0f}s")
    con.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
