# -*- coding: utf-8 -*-
"""建中文义项倒排索引表 cn_sense。

问题：search_cn 用 `zh LIKE '%开心%'` 查，前置通配符让 idx_cn_zh 失效，
必须全表扫 76.8 万行 → 每次 600ms，打字必卡。

方案：把 cn_index.zh 按义项拆开，一个义项一行，字段存「干净义项」，
      再对 sense 建普通索引。查询 `WHERE sense = ?` 走索引 → 毫秒级。

拆分规则：与 DictEngine.split_senses 保持一致（切词性标记、中英逗号/分号），
          额外去掉 [领域] 标记与括号注释 —— 这些是噪音来源。
"""
import os
import re
import sqlite3
import sys
import time

DB = r"D:\Dictionary\dict.db"

# ---- 与 app.py 保持一致的切分逻辑（复制此处以避免 import PySide6）----
_POS_RE = re.compile(
    r"(?:^|(?<=[\s]))"
    r"(n|v|vt|vi|a|adj|ad|adv|prep|conj|pron|num|int|interj|art|aux|"
    r"abbr|na|pl|sing|pt|pp|pref|suf)\.",
)
_SPLIT_RE = re.compile(r"[，,；;、/]+")
_BRACKET_RE = re.compile(r"\[[^\]]*\]|【[^】]*】|\([^)]*\)|（[^）]*）")
# 省略号 / 占位符：ECDICT 用 ... 表示「给…浇水」这类可替换宾语。
# 直接删掉（而不是换成空格），否则「给 浇水」这种带空格的伪义项会入库，
# 用户搜「浇水」永远匹配不到。
_DOTS_RE = re.compile(r"[.．·…]+")
_JUNK_RE = re.compile(r"[\s]+")


def split_senses(zh):
    """把 ECDICT 的 zh 拆成独立义项，返回去重后的干净义项列表。"""
    if not zh:
        return []
    text = zh.replace("\\n", "\n")
    text = _POS_RE.sub("\n", text)
    out = []
    for block in text.split("\n"):
        # 领域标记 [法] [计] 等是义项边界的强信号：去掉它时要留下分隔，
        # 否则「…移民 [法] 侵入者」会被拼成「移民侵入者」这种伪义项。
        block = _BRACKET_RE.sub("，", block)
        for part in _SPLIT_RE.split(block):
            p = part.strip()
            p = _DOTS_RE.sub("", p)              # 「给...浇水」→「给浇水」
            p = _JUNK_RE.sub("", p).strip(".").strip()
            # ⚠ 单字义项必须保留：「水」「狗」「书」「跑」都是合法核心义项，
            #   早期写 len(p) < 2 会把它们全部丢掉，导致查「水」查不到 water。
            if not p or len(p) > 12:
                continue
            if not re.search(r"[\u4e00-\u9fff]", p):
                continue
            out.append(p)
    # 去重保序
    seen, uniq = set(), []
    for s in out:
        if s not in seen:
            seen.add(s)
            uniq.append(s)
    return uniq


def main():
    t0 = time.time()
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    print("1) 建表 cn_sense")
    cur.execute("DROP TABLE IF EXISTS cn_sense")
    cur.execute("""
        CREATE TABLE cn_sense (
            sense TEXT,        -- 规范化的中文义项（查询键）
            word  TEXT,
            lower TEXT,
            zh    TEXT,        -- 该词条的完整释义（评分要用，冗余存一份避免回表）
            pos   INTEGER,     -- 义项在原释义中的序号，越小越核心
            tag   TEXT
        )
    """)

    print("2) 扫描 cn_index 并拆分义项")
    n_src = cur.execute("SELECT COUNT(*) FROM cn_index").fetchone()[0]
    print(f"   cn_index 共 {n_src:,} 行")

    # ⚠ 必须用「两个游标」：读游标和写游标分开。
    # 同一个 cursor 上边迭代 SELECT 边 executemany INSERT，
    # 迭代会被写操作打断 —— 上一版只写进第一批 20,002 行就结束了，
    # 表面看"完成"，实际只建了 0.3% 的索引（最隐蔽的一类 bug）。
    rcur = con.cursor()          # 专门负责读
    wcur = con.cursor()          # 专门负责写
    batch, total = [], 0
    for r in rcur.execute("SELECT word, lower, zh, tag FROM cn_index"):
        senses = split_senses(r["zh"])
        for i, s in enumerate(senses):
            batch.append((s, r["word"], r["lower"], r["zh"], i, r["tag"]))
        if len(batch) >= 20000:
            wcur.executemany(
                "INSERT INTO cn_sense (sense,word,lower,zh,pos,tag) "
                "VALUES (?,?,?,?,?,?)", batch)
            total += len(batch)
            batch = []
            print(f"   已写入 {total:,} / 目标约 200 万", end="\r")
            sys.stdout.flush()
    if batch:
        wcur.executemany(
            "INSERT INTO cn_sense (sense,word,lower,zh,pos,tag) "
            "VALUES (?,?,?,?,?,?)", batch)
        total += len(batch)
    con.commit()
    print(f"\n   cn_sense 共 {total:,} 行")

    print("3) 建索引")
    for sql in [
        "CREATE INDEX idx_cs_sense ON cn_sense(sense)",
        "CREATE INDEX idx_cs_lower ON cn_sense(lower)",
    ]:
        t1 = time.time()
        cur.execute(sql)
        print(f"   {sql.split()[2]}  {time.time()-t1:.1f}s")
    con.commit()

    print("4) ANALYZE（让查询计划器选对索引）")
    cur.execute("ANALYZE")
    con.commit()

    print("5) 抽样验证")
    for q in ["开心", "高兴", "快乐", "水", "狗", "跑", "吃"]:
        rows = wcur.execute(
            "SELECT word, pos FROM cn_sense WHERE sense=? "
            "ORDER BY pos LIMIT 6", (q,)).fetchall()
        print(f"   {q}: " + ", ".join(f"{r[0]}(p{r[1]})" for r in rows))
    # 行数自检
    n_out = wcur.execute("SELECT COUNT(*) FROM cn_sense").fetchone()[0]
    print(f"   自检行数 = {n_out:,}")
    assert n_out > 1_000_000, f"仅写入 {n_out:,} 行，疑似又被打断！"

    con.execute("VACUUM")
    con.close()
    print(f"\n完成，耗时 {time.time()-t0:.1f}s")
    print("DB size =", f"{os.path.getsize(DB):,}")


if __name__ == "__main__":
    main()
