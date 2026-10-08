# -*- coding: utf-8 -*-
"""阶段二数据层冒烟：UserStore + 历史记录集成。"""
import io, os, sys, tempfile
sys.path.insert(0, r"D:\Dictionary\build")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

log = io.StringIO()
def say(s=""): log.write(str(s) + "\n")

ok = fail = 0
def chk(c, label, extra=""):
    global ok, fail
    if c:
        ok += 1; say(f"  PASS  {label}")
    else:
        fail += 1; say(f"  FAIL  {label}  {extra}")

import app as A

# ---- 1. UserStore 基本 ----
say("== UserStore ==")
tmp = tempfile.mkdtemp(prefix="us_")
db = os.path.join(tmp, "user_data.db")
st = A.UserStore(path=db)
chk(st.con is not None, "sqlite 连接建立")

st.add_history("apple")
st.add_history("banana")
st.add_history("apple")          # 重复词应去重（更新时间）
h = st.history()
say(f"  历史: {h}")
chk(len(h) == 2, "历史去重后 2 条", str(h))
chk(h[0][0] == "apple", "最近查询排最前", str(h))

st.delete_history("banana")
chk(len(st.history()) == 1, "删除单条生效")

st.add_history("cat")
st.clear_history()
chk(len(st.history()) == 0, "一键清空生效")

# ---- 2. 单词本 + 分组 ----
say("== 单词本 ==")
chk(st.groups()[0]["name"] == "默认分组", "默认分组存在")
gid = st.add_group("四级")
chk(gid > 0, "新建分组成功", str(gid))
st.add_word("abandon", 0)
st.add_word("abandon", gid)
st.add_word("ability", 0)
chk(st.has_word("abandon", 0), "收藏存在")
chk(len(st.words(0)) == 2, "默认分组 2 词", str(st.words(0)))
chk(len(st.words(gid)) == 1, "四级分组 1 词")
st.remove_word("ability", 0)
chk(len(st.words(0)) == 1, "删除单词生效")
out = os.path.join(tmp, "export.txt")
n = st.export_words(out, 0)
chk(n == 1 and os.path.exists(out), "导出 txt 成功", str(n))

# ---- 3. MainWindow 集成 ----
say("== MainWindow 集成 ==")
from PySide6.QtWidgets import QApplication
qapp = QApplication.instance() or QApplication(sys.argv)
w = A.MainWindow()
chk(w.store is not None, "主窗口有 UserStore")
chk(hasattr(w, "_nav_stack"), "有导航栈")
chk(hasattr(w, "_auto"), "有自动选中标志")
chk(callable(getattr(w, "_nav_back", None)), "有返回上一词方法")

# 模拟查词记录历史
w.search_edit.setText("")
w.store.clear_history()
w._render("water", record=True)
chk(w._cur_word == "water", "渲染 water")
chk("water" in [x[0] for x in w.store.history()], "主动查词记入历史")

# 模拟跳转 → 导航栈
w._render("aqua", record=True)
chk(w._nav_stack == ["water"], "跳转压栈上一词", str(w._nav_stack))
w._nav_back()
chk(w._cur_word == "water", "返回上一词成功", w._cur_word)

say(f"\nRESULT  ok={ok} fail={fail}")
open(r"D:\Dictionary\build\_stage2.txt", "w", encoding="utf-8").write(log.getvalue())
print("done")
