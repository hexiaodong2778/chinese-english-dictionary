# -*- coding: utf-8 -*-
"""新增功能测试：官方词典直达 + 真实例句渲染。"""
import io
import os
import sqlite3
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
BUILD = r"D:\Dictionary\build"
sys.path.insert(0, BUILD)

ok = 0
bad = []


def chk(name, cond, extra=""):
    global ok
    if cond:
        ok += 1
        print(f"  PASS  {name}")
    else:
        bad.append(name)
        print(f"  FAIL  {name}  {extra}")


src = io.open(os.path.join(BUILD, "app.py"), encoding="utf-8").read()

print("== 1. OFFICIAL_DICTS 定义 ==")
from app import OFFICIAL_DICTS
chk("共 6 部官方词典", len(OFFICIAL_DICTS) == 6, len(OFFICIAL_DICTS))
keys = [o["key"] for o in OFFICIAL_DICTS]
for k in ("oxford", "cambridge", "collins", "longman", "merriam", "vocab"):
    chk(f"包含 {k}", k in keys)
for o in OFFICIAL_DICTS:
    chk(f"{o['label']} URL 带 {{w}} 占位符", "{w}" in o["url"])
    chk(f"{o['label']} 是 https", o["url"].startswith("https://"))
    chk(f"{o['label']} 有 full/note", bool(o["full"]) and bool(o["note"]))
# URL 里不应残留 format 之外的占位符
import re as _re
for o in OFFICIAL_DICTS:
    ph = _re.findall(r"\{(\w+)\}", o["url"])
    chk(f"{o['label']} 占位符只有 w", set(ph) <= {"w"}, ph)

print("\n== 2. 界面接入 ==")
chk("_od_open 方法存在", "def _od_open(self, dict_key)" in src)
chk("od_buttons 已创建", "self.od_buttons = []" in src)
chk("od_host 已加入布局", "self.od_host" in src and "sl.addWidget(self.od_host)" in src)
chk("odBtn 样式已定义", "#odBtn {" in src or "#odBtn{{" in src.replace("{{", "{"))
chk("官方词典行有标签", "词典原文" in src)
chk("欢迎页提到词典原文", "跳转牛津" in src)

print("\n== 3. 例句引擎 ==")
chk("examples 方法存在", "def examples(self, word, limit=8)" in src)
chk("example_count 方法存在", "def example_count(self)" in src)
chk("渲染含例句板块", 'self._section("例句")' in src)
chk("例句注明数据来源", "Tatoeba" in src)

print("\n== 4. 例句库数据 ==")
# 关键：必须检查**部署目录**的 dict.db，而不是 build 目录的。
# build 目录的库只是构建产物；程序实际读的是 exe 同目录那份。
# 曾因只更新了 build/dict.db 而漏掉部署版，导致界面看不到例句。
DB_DEPLOY = r"D:\Dictionary\dict.db"
DB_BUILD = os.path.join(BUILD, "dict.db")
db = DB_DEPLOY if os.path.exists(DB_DEPLOY) else DB_BUILD
print(f"  检查词库: {db}")
chk("检查的是部署目录词库", db == DB_DEPLOY, db)
con = sqlite3.connect(db)
con.row_factory = sqlite3.Row
try:
    n_ex = con.execute("SELECT COUNT(*) FROM example").fetchone()[0]
    n_ix = con.execute("SELECT COUNT(*) FROM ex_index").fetchone()[0]
    n_w = con.execute("SELECT COUNT(DISTINCT word) FROM ex_index").fetchone()[0]
    chk("example 表行数 > 5万", n_ex > 50000, f"{n_ex:,}")
    chk("ex_index 行数 > 5万", n_ix > 50000, f"{n_ix:,}")
    chk("覆盖词数 > 1万", n_w > 10000, f"{n_w:,}")

    # 索引完整性：不能有指向不存在例句的索引
    orphan = con.execute(
        "SELECT COUNT(*) FROM ex_index x LEFT JOIN example e ON e.id=x.ex_id "
        "WHERE e.id IS NULL").fetchone()[0]
    chk("无悬空索引", orphan == 0, orphan)

    # 例句不能为空
    empty = con.execute(
        "SELECT COUNT(*) FROM example WHERE en='' OR zh='' OR en IS NULL "
        "OR zh IS NULL").fetchone()[0]
    chk("无空例句", empty == 0, empty)

    # 中文必须是简体（抽查常见繁体字不应出现）
    trad = con.execute("SELECT COUNT(*) FROM example WHERE zh LIKE '%這%' "
                       "OR zh LIKE '%們%' OR zh LIKE '%個%'").fetchone()[0]
    chk("中文已转简体", trad == 0, trad)

    # 例句不能全是短句
    short = con.execute("SELECT COUNT(*) FROM example WHERE n_en < 4").fetchone()[0]
    ratio = short / max(n_ex, 1)
    chk("过短例句占比 < 25%", ratio < 0.25, f"{ratio:.1%}")

    print("\n  抽样（每词前 2 条）：")
    for w in ("dog", "water", "abandon", "government", "beautiful", "school"):
        rs = con.execute(
            "SELECT e.en, e.zh FROM ex_index x JOIN example e ON e.id=x.ex_id "
            "WHERE x.word=? ORDER BY e.n_en LIMIT 2", (w,)).fetchall()
        chk(f"{w} 有例句", len(rs) > 0)
        for r in rs:
            print(f"      {r['en']}")
            print(f"      {r['zh']}")

    meta = {r["k"]: r["v"] for r in con.execute("SELECT k,v FROM meta")}
    chk("meta 记录例句来源", "Tatoeba" in (meta.get("example_source") or ""),
        meta.get("example_source"))
finally:
    con.close()

print(f"\n通过 {ok}，失败 {len(bad)}")
if bad:
    for b in bad:
        print(f"  X {b}")
sys.exit(1 if bad else 0)
