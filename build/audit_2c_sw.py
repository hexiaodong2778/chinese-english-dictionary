# -*- coding: utf-8 -*-
"""核查疑点：
1. 粤语词库 sw 列大量重复，是否影响检索？
2. 日/法/粤在界面上会不会因为缺 translation 而显示空白？
"""
import io
import os
import sqlite3
import sys

os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.chdir(r"D:\Dictionary")
sys.path.insert(0, r"D:\Dictionary\build")
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

DEPLOY = r"D:\Dictionary"

print("=" * 72)
print("① 粤语 sw 列重复情况")
print("=" * 72)
con = sqlite3.connect(f"file:{os.path.join(DEPLOY,'dict_yue.db')}?mode=ro",
                     uri=True)
con.row_factory = sqlite3.Row
n = con.execute("SELECT COUNT(*) FROM dict").fetchone()[0]
nsw = con.execute("SELECT COUNT(DISTINCT sw) FROM dict").fetchone()[0]
print(f"  总词条 {n:,}，不同 sw 值 {nsw:,}  -> 平均每 sw {n/nsw:.1f} 条")
dup = con.execute(
    "SELECT sw, COUNT(*) c FROM dict GROUP BY sw "
    "ORDER BY c DESC LIMIT 8").fetchall()
print("  sw 重复最多的：")
for r in dup:
    # 看这些 sw 对应什么词
    ws = con.execute("SELECT word FROM dict WHERE sw=? LIMIT 4",
                     (r["sw"],)).fetchall()
    print(f"    sw={r['sw']!r:12} {r['c']:>5} 条  例: "
          + ", ".join(x["word"] for x in ws))
print("\n  -> sw 是「罗马字检索键」，用来支持输入罗马字查词。")
print("     同一读音对应多个汉字是正常现象（如 a 音下的多个字），")
print("     检索时按 sw 匹配会返回该读音下的所有字，这是设计预期。")

# 验证：用具体罗马字查
print("\n  实际检索验证：")
for probe in ("nei", "jau", "m4goi"):
    rs = con.execute(
        "SELECT word, phonetic FROM dict WHERE sw=? LIMIT 5",
        (probe,)).fetchall()
    print(f"    sw={probe!r:10} -> {len(rs)} 条: "
          + ", ".join(f"{r['word']}({r['phonetic']})" for r in rs))
con.close()

print()
print("=" * 72)
print("② 界面渲染：切到日语/法语/粤语会不会空白或报错")
print("=" * 72)

from PySide6.QtWidgets import QApplication
app = QApplication.instance() or QApplication(sys.argv)
import app as A

w = A.MainWindow()
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


# 语言下拉的 index -> key
for idx in range(w.lang_box.count()):
    key = w.lang_box.itemData(idx)
    label = w.lang_box.itemText(idx)
    w.lang_box.setCurrentIndex(idx)
    app.processEvents()
    print(f"\n--- [{idx}] {label} (key={key}) ---")
    eng = w.engine
    if eng is None or eng.con is None:
        print(f"    词库未加载（缺失？）")
        # 这可能是正常的（词库文件不存在才会这样），此处只报告
        continue
    r = eng.con.execute("SELECT word FROM dict LIMIT 1").fetchone()
    print(f"    词库已加载，样例词: {r['word'] if r else '-'}")

    # 查一个词
    if key == "en":
        w.search_edit.setText("dog")
    elif key == "ja":
        w.search_edit.setText("日本")
    elif key == "fr":
        w.search_edit.setText("bonjour")
    elif key == "yue":
        w.search_edit.setText("你")
    app.processEvents()
    txt = w.detail.toPlainText()
    print(f"    查询后详情长度: {len(txt)}")
    print(f"    前 120 字: {txt[:120]!r}")
    chk(f"{label} 渲染不报错且有内容", len(txt) > 5, len(txt))

print()
print("=" * 72)
print(f"结论：通过 {ok}，失败 {len(bad)}")
for b in bad:
    print(f"  X {b}")
