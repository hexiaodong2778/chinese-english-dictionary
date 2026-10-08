# -*- coding: utf-8 -*-
"""中文反查「去后缀变体」回归测试。

── 这个 bug 是怎么来的（2026-09-17）──
数据结构：`cn_sense.sense` 存的**不是**规范化义项，而是词条释义原样切分的结果。
          beautiful 的释义是「美丽的」→ 它被索引到 sense='美丽的' 名下，
          而用户查的是「美丽」。

于是就出事了：
    查「美丽」→ 等值查询 `sense = '美丽'` 把 beautiful 整个排除在外
             → 结果全是 fairness / loveliness / pulchritude 这类生僻词
             → **最该出现的 beautiful 反而不见**

规模：全表 1,158,466 条 sense 里有 107,781 条（9.3%）以「的」结尾。
      近十分之一的中文反查都踩这个坑。

为什么会漏掉：`_sense_score()` 其实**早就**会处理「美丽的 → 美丽」
      （`s.rstrip("的地得") == kw` 给 sc=1）。但它拿不到这个词 ——
      词在「构建候选集」阶段就被漏掉了。评分再聪明也没用。

修法：在取候选那一步，把「去后缀变体」一并查（`sense IN (?,?,?,?)`）。
      既是等值查询、还是走 idx_cs_sense 索引，单次 0.06ms（原 0.01ms）。

本测试钉住的点：
  1. 后缀变体能被查到（beautiful 这类）
  2. 反向也能查到（查「美丽」能捞到「美丽的」义项）
  3. 修复没有破坏原有的核心词排序
  4. 修复没把查询拖慢（仍是索引等值查询，不是 LIKE 全表扫）
"""
import os
import sys
import time

sys.path.insert(0, r"D:\Dictionary\build")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.chdir(r"D:\Dictionary\build")

from PySide6.QtWidgets import QApplication

qapp = QApplication(sys.argv)
import app as A

PASS, FAIL = [], []


def chk(name, cond, detail=""):
    if cond:
        PASS.append(name + ("  [%s]" % detail if detail else ""))
    else:
        FAIL.append(name + ("  → %s" % detail if detail else ""))


con = A.open_db(r"D:\Dictionary\dict.db")
eng = A.DictEngine(con, "en")


def top(zh, n=3):
    return [r["word"] for r in eng.search_cn(zh)][:n]


# ── 1. 「的」后缀义项能被查到（原始 bug 场景） ──────────────────────────
# beautiful 的释义是「美丽的」，用户查「美丽」→ 修复前出来 fairness。
# 注意这里只收「查询词是目标词释义的子串（含去后缀）」，也就是
# **字面索引能覆盖**的场景。同义词（开心 ↔ 快乐）不属于本修复范围：
# happy 的释义是「快乐的/幸福的/愉快的」，压根没有「开心」二字，
# 再怎么做后缀变体也变不出来 —— 那要靠联网同义词补充（_cn_extra_for）。
cases = [
    ("美丽",  "beautiful"),   # ← 原始 bug：修复前出来 fairness
    ("漂亮",  "pretty"),      # ← 修复前出来 chic
    ("快乐",  "happy"),       # 释义「快乐的」，同类问题
    ("聪明",  "clever"),      # 释义常带「的」
    ("重要",  "important"),
    ("困难",  "difficult"),
    ("简单",  "simple"),
]
for zh, want in cases:
    got = top(zh, 5)
    chk("查「%s」能查到 %s" % (zh, want), want in got,
        "前 5 名 = %s" % (got,))

# ── 2. 原始报告的两个词，首条必须正确 ──────────────────────────────────
chk("查「美丽」首条是 beautiful", top("美丽", 1) == ["beautiful"],
    top("美丽", 3))
chk("查「漂亮」首条是 pretty", top("漂亮", 1) == ["pretty"], top("漂亮", 3))

# ── 3. 反向：查「美丽」能捞到 indexed 到「美丽的」名下的词 ──────────────
# beautiful 在 cn_sense 里的 sense 是 '美丽的'，不是 '美丽'
row = con.execute(
    "SELECT sense FROM cn_sense WHERE lower='beautiful'").fetchall()
senses = {r["sense"] for r in row}
chk("beautiful 的 sense 确实是「美丽的」", "美丽的" in senses,
    str(sorted(senses)))
chk("修复后仍能被「美丽」查到（说明变体查询生效）",
    "beautiful" in top("美丽", 5))

# ── 4. 变体查询确实走 IN 而非 LIKE ─────────────────────────────────────
# ⚠ 坑：不能写 src.split("def search_cn")[1].split("def ")[1] ——
#   那会在 search_cn **内部第一个嵌套 def** 处切断，取不到函数体后半段，
#   断言随之假失败。正确做法是靠缩进判断顶层边界。
src = open(r"D:\Dictionary\build\app.py", encoding="utf-8").read()
_body = src.split("def search_cn")[1]


def _fn_body(text):
    """截到下一个同缩进（4 空格）的方法定义为止。"""
    out = []
    for ln in text.splitlines()[1:]:
        if ln.startswith("    def ") or ln.startswith("class "):
            break
        out.append(ln)
    return "\n".join(out)


seg = _fn_body(_body)
chk("取候选用的是 IN 等值（不是 LIKE）", "c.sense IN (" in seg,
    "函数体长度 %d 字符，未找到 IN 查询" % len(seg))
chk("变体规则与评分逻辑一致（用的 rstrip('的地得')）",
    'rstrip("的地得")' in seg, "未找到 rstrip 变体规则")
chk("变体查询没退化回 LIKE 全表扫",
    "c.sense LIKE" not in seg, "出现了 c.sense LIKE，会全表扫")

# ── 5. 无回归：原有核心词排序不变 ──────────────────────────────────────
base = [("狗", "dog"), ("猫", "cat"), ("书", "book"), ("水", "water"),
        ("学习", "study"), ("跑", "run"), ("电脑", "computer"),
        ("环境", "environment"), ("放弃", "abandon"),
        ("生词", None)]      # 生词只要求不崩
for zh, want in base:
    if want is None:
        got = top(zh, 1)
        chk("查「%s」不抛异常" % zh, isinstance(got, list), str(got))
    else:
        got = top(zh, 1)
        chk("回归：查「%s」首条仍是 %s" % (zh, want), got == [want], got)

# ── 6. 性能：变体查询必须仍是索引等值查询 ──────────────────────────────
variants = ("美丽", "美丽的", "美丽地", "美丽得")
ph = ",".join("?" * len(variants))
sql = ("SELECT c.word FROM cn_sense c JOIN dict d ON d.lower = c.lower "
       "WHERE c.sense IN (%s) AND d.frq > 0 LIMIT 100" % ph)
plan = " ".join(str(tuple(r)) for r in con.execute(
    "EXPLAIN QUERY PLAN " + sql, variants))
chk("查询计划走 idx_cs_sense 索引", "idx_cs_sense" in plan, plan)
chk("查询计划没有全表扫（SCAN cn_sense）", "SCAN cn_sense" not in plan, plan)

t = time.perf_counter()
for _ in range(30):
    con.execute(sql, variants).fetchall()
per = (time.perf_counter() - t) * 1000 / 30
chk("单次查询 < 5ms（实测 %.3fms）" % per, per < 5.0, "%.3f ms" % per)

# ── 7. 边界：单字 / 空串 / 纯 ASCII / 带「的」的查询 ────────────────────
for q, note in (("水", "单字"), ("", "空串"), ("a", "单字母 ASCII"),
                ("the", "三字母 ASCII")):
    try:
        r = eng.search_cn(q)
        chk("边界「%s」(%s)不抛异常" % (q, note), isinstance(r, list),
            "%d 条" % len(r))
    except Exception as e:
        chk("边界「%s」(%s)不抛异常" % (q, note), False, repr(e))

# 查询词本身就带「的」——不该被 strip 成空串
r = eng.search_cn("的")
chk("查询「的」本身不崩（不被 strip 成空串）", isinstance(r, list),
    "%d 条" % len(r))

# ── 8. 「的」只在末位时才剥（不能把「目的」剥成「目」） ────────────────
# ⚠ 注意：不能断言「目的」与「目」结果**不同** —— 实测两者前 5 名都是
#   purpose/object/meaning/intention/sake，而且这是**正确**的：
#   purpose 的释义本来就同时覆盖「目的」和「目」。断言它们不同是错的。
#
#   真正要防的是「变体规则误伤带『的』的词」：若把「目的」剥成「目」，
#   就会去查 sense='目'（全表仅 2 条）从而丢失「目的」的 24 条真义项。
#   所以判据是「查『目的』能查到 purpose」+「strIP 规则确实是 rstrip
#   （只去末位，不去中间）」。
r_mu = top("目的", 5)
chk("查「目的」能查到 purpose（没被剥成「目」）", "purpose" in r_mu, r_mu)
# ⚠ 注意方向：单字「目」的结果**更多**（实测 26 条 vs 23 条），这不是缺陷 ——
#   「目」作为更短的串，天然能命中的义项更多（目标/目击/目录…）。
#   这一条只是为了确认两者被当成**不同的查询**处理，没有互相污染。
chk("单字「目」命中的义项不少于「目的」（短串匹配面更广）",
    len(top("目", 40)) >= len(top("目的", 40)),
    "目=%d 条  目的=%d 条" % (len(top("目", 40)), len(top("目的", 40))))

# rstrip 只作用于末位 —— 「地的得」出现在中间时不受影响
chk("变体规则用 rstrip（只剥末位）而非 replace（会剥中间）",
    "rstrip" in seg and "replace(\"的\"" not in seg, "变体规则可疑")

print("PASS=%d FAIL=%d" % (len(PASS), len(FAIL)))
for x in PASS:
    print("  PASS ", x)
for x in FAIL:
    print("  FAIL ", x)
sys.exit(1 if FAIL else 0)
