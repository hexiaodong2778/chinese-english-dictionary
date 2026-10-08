# -*- coding: utf-8 -*-
"""全方位检查 ②：四个词库的数据完整性深度核查。

重点找：悬空引用、空值、重复、索引缺失、编码异常、
        数据分布异常（如某列全空）。
"""
import io
import os
import sqlite3
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

DEPLOY = r"D:\Dictionary"
issues = []
ok = 0


def chk(name, cond, extra=""):
    global ok
    if cond:
        ok += 1
        print(f"  PASS  {name}")
    else:
        issues.append(name)
        print(f"  FAIL  {name}  {extra}")


def dump_cols(con, table):
    return {r[1] for r in con.execute(f"PRAGMA table_info({table})")}


print("=" * 72)
print("英语词库 dict.db")
print("=" * 72)
con = sqlite3.connect(f"file:{os.path.join(DEPLOY, 'dict.db')}?mode=ro", uri=True)
con.row_factory = sqlite3.Row

print("\n--- 表结构 ---")
for t in ("dict", "cn_index", "lemma", "example", "ex_index", "meta"):
    cols = [r[1] for r in con.execute(f"PRAGMA table_info({t})")]
    n = con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
    print(f"  {t:10} {n:>9,} 行  列: {cols}")

print("\n--- dict 表关键字段非空率 ---")
n_all = con.execute("SELECT COUNT(*) FROM dict").fetchone()[0]
for col in ("word", "translation", "phonetic", "definition", "tag",
            "exchange", "collins", "oxford", "frq", "bnc"):
    try:
        n = con.execute(
            f"SELECT COUNT(*) FROM dict WHERE {col} IS NOT NULL AND {col}!=''"
        ).fetchone()[0]
        pct = n / n_all * 100
        flag = "!!" if pct < 1 else "  "
        print(f"  {flag} {col:12} 非空 {n:>9,}  ({pct:5.1f}%)")
        if col in ("word", "translation") and pct < 99:
            issues.append(f"dict.{col} 非空率仅 {pct:.1f}%")
    except Exception as e:
        print(f"     {col:12} 查询失败: {e}")

print("\n--- word 唯一性 / 小写唯一性 ---")
dup = con.execute(
    "SELECT COUNT(*) FROM (SELECT lower(word) w FROM dict "
    "GROUP BY lower(word) HAVING COUNT(*)>1)").fetchone()[0]
print(f"  lower(word) 重复组数: {dup:,}  （ECDICT 本身允许，属正常）")

print("\n--- 索引清单 ---")
for r in con.execute(
        "SELECT name,tbl_name FROM sqlite_master WHERE type='index' "
        "AND name NOT LIKE 'sqlite_%'"):
    print(f"  {r['name']:26} on {r['tbl_name']}")

print("\n--- 例句库深度检查 ---")
n_ex = con.execute("SELECT COUNT(*) FROM example").fetchone()[0]
n_ix = con.execute("SELECT COUNT(*) FROM ex_index").fetchone()[0]
n_w = con.execute("SELECT COUNT(DISTINCT word) FROM ex_index").fetchone()[0]
print(f"  example {n_ex:,} / ex_index {n_ix:,} / 覆盖词 {n_w:,}")

# 悬空索引
orphan = con.execute(
    "SELECT COUNT(*) FROM ex_index x LEFT JOIN example e ON e.id=x.ex_id "
    "WHERE e.id IS NULL").fetchone()[0]
chk("无悬空索引（指向不存在的例句）", orphan == 0, orphan)

# 未被引用的例句（允许，但要报告比例）
unref = con.execute(
    "SELECT COUNT(*) FROM example e LEFT JOIN ex_index x ON x.ex_id=e.id "
    "WHERE x.ex_id IS NULL").fetchone()[0]
print(f"  未被任何词引用的例句: {unref:,}  "
      f"({unref / max(n_ex,1) * 100:.1f}%)  —— 正常，长句可能不含被索引的词")

# 空值
empty = con.execute(
    "SELECT COUNT(*) FROM example WHERE en IS NULL OR zh IS NULL "
    "OR trim(en)='' OR trim(zh)=''").fetchone()[0]
chk("例句无空值", empty == 0, empty)

# 索引里的 word 是否都是小写字母开头
bad_w = con.execute(
    "SELECT COUNT(*) FROM ex_index WHERE word GLOB '*[^a-z''-]*'").fetchone()[0]
chk("索引词均为小写字母", bad_w == 0, bad_w)

# 每词例句数分布
print("\n  每词例句数分布:")
for lo, hi in ((1, 1), (2, 3), (4, 6), (7, 9), (10, 12)):
    n = con.execute(
        "SELECT COUNT(*) FROM (SELECT word, COUNT(*) c FROM ex_index "
        f"GROUP BY word HAVING c BETWEEN {lo} AND {hi})").fetchone()[0]
    print(f"    {lo:>2}-{hi:<3} 条: {n:>7,} 个词")

# 简体检查
trad = con.execute(
    "SELECT COUNT(*) FROM example WHERE zh LIKE '%這%' OR zh LIKE '%們%' "
    "OR zh LIKE '%個%' OR zh LIKE '%為%'").fetchone()[0]
ratio = trad / max(n_ex, 1)
chk("中文已转简体（繁体字占比 <1%）", ratio < 0.01, f"{ratio:.3%} ({trad})")

# 中文字符率
nonzh = con.execute(
    "SELECT COUNT(*) FROM example WHERE zh NOT GLOB '*[一-龥]*'").fetchone()[0]
chk("例句中文含汉字", nonzh == 0, nonzh)

# lemma 表
n_lemma = con.execute("SELECT COUNT(*) FROM lemma").fetchone()[0]
print(f"\n  lemma 表: {n_lemma:,} 行")
lem_orphan = con.execute(
    "SELECT COUNT(*) FROM lemma WHERE lemma IS NULL OR form IS NULL "
    "OR trim(lemma)='' OR trim(form)=''").fetchone()[0]
chk("lemma 无空值", lem_orphan == 0, lem_orphan)

# cn_index
n_cn = con.execute("SELECT COUNT(*) FROM cn_index").fetchone()[0]
print(f"  cn_index 表: {n_cn:,} 行")
cn_cols = [r[1] for r in con.execute("PRAGMA table_info(cn_index)")]
print(f"    列: {cn_cols}")

con.close()

print()
print("=" * 72)
print("多语言词库（日/法/粤）")
print("=" * 72)
for f, lang in (("dict_ja.db", "日语"), ("dict_fr.db", "法语"),
                ("dict_yue.db", "粤语")):
    p = os.path.join(DEPLOY, f)
    print(f"\n--- {lang} {f} ---")
    c = sqlite3.connect(f"file:{p}?mode=ro", uri=True)
    c.row_factory = sqlite3.Row
    cols = dump_cols(c, "dict")
    print(f"  列: {sorted(cols)}")
    n = c.execute("SELECT COUNT(*) FROM dict").fetchone()[0]
    print(f"  词条: {n:,}")
    # 关键列非空
    for col in ("word", "translation"):
        if col in cols:
            nn = c.execute(
                f"SELECT COUNT(*) FROM dict WHERE {col} IS NOT NULL "
                f"AND {col}!=''").fetchone()[0]
            chk(f"{lang}.{col} 非空", nn > n * 0.9, f"{nn}/{n}")
    # sw 检索键（罗马字）
    if "sw" in cols:
        sw = c.execute(
            "SELECT COUNT(*) FROM dict WHERE sw IS NOT NULL AND sw!=''"
        ).fetchone()[0]
        print(f"  sw 检索键: {sw:,} ({sw/n*100:.1f}%)")
    # 音标
    if "phonetic_us" in cols:
        ph = c.execute(
            "SELECT COUNT(*) FROM dict WHERE phonetic_us IS NOT NULL "
            "AND phonetic_us!=''").fetchone()[0]
        chk(f"{lang} 有音标", ph > n * 0.5, f"{ph}/{n}")
    n_l = c.execute("SELECT COUNT(*) FROM lemma").fetchone()[0]
    print(f"  lemma: {n_l:,}")
    c.close()

print()
print("=" * 72)
print("结论")
print("=" * 72)
print(f"  通过 {ok}，问题 {len(issues)}")
for i in issues:
    print(f"    X {i}")
sys.exit(1 if issues else 0)
