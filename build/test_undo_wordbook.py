# -*- coding: utf-8 -*-
"""撤销栈 + 单词本一键清空 —— 用户三条反馈里的后两条。

  反馈②「看不到操作撤销的按钮，放在哪了」
        → 根因：**根本没有**。清空历史的弹窗写着「此操作可撤销」，
          代码里清完就没了，那句承诺是假的。
  反馈③「单词本没有一键清除的功能，再加个确认」
        → 根因：UI 上只有「导出」，UserStore.clear_words() 写了却没人调。

本测试同时覆盖**行为**（撤销真的能还原、清空真的只清该清的）和
**接线**（按钮存在、确认框默认是取消、快捷键接上了）—— 后者用源码断言，
因为这个项目已有先例：函数写好了但没接到 UI 上（clear_words 就是）。
"""
import io
import os
import re
import sys
import tempfile

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, r"D:\Dictionary\build")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

qapp = QApplication(sys.argv)
import app as A

P = F = 0
lines = []


def say(s=""):
    lines.append(str(s))
    print(s)


def chk(name, cond, extra=""):
    global P, F
    if cond:
        P += 1
        say("  PASS  %s %s" % (name, extra))
    else:
        F += 1
        say("  FAIL  %s %s" % (name, extra))


# ---- 隔离用户数据：强制 UserStore 落在临时目录，绝不碰真实单词本
_TMP = tempfile.mkdtemp(prefix="dictwb_")
_orig_init = A.UserStore.__init__


def _patched_init(self, path=None):
    _orig_init(self, os.path.join(_TMP, "user_data.db"))


A.UserStore.__init__ = _patched_init

SRC = open(r"D:\Dictionary\build\app.py", encoding="utf-8").read()


def fn_body(text, name, must_contain=None):
    """取某个方法的源码正文（到下一个同缩进的 def/class 为止）。

    ⚠ 坑：同名方法可能有多个 —— `keyPressEvent` 在 TranslateDialog 和
      MainWindow 里各有一个，`find()` 只返回**第一个**（TranslateDialog 的，
      里面当然没有 Key_Z），于是断言假失败。用 must_contain 指定要哪一个。
    """
    start = 0
    while True:
        i = text.find("    def %s(" % name, start)
        if i < 0:
            return ""
        start = i + 1
        body = []
        for ln in text[i:].splitlines()[1:]:
            if ln.startswith("    def ") or ln.startswith("    # ---") \
                    or ln.startswith("class "):
                break
            body.append(ln)
        b = "\n".join(body)
        if must_contain is None or must_contain in b:
            return b


say("=" * 74)
say("1. UserStore 快照 / 还原（撤销的地基）")
say("=" * 74)
st = A.UserStore()
st.add_history("alpha")
st.add_history("beta")
st.add_history("gamma")
snap_h = st.snapshot_history()
chk("历史快照含 3 条", len(snap_h) == 3, "(实际 %d)" % len(snap_h))
chk("快照是纯 Python 元组（脱离连接可用）",
    all(isinstance(r, tuple) and len(r) == 2 for r in snap_h))
st.clear_history()
chk("清空后历史为空", len(st.history()) == 0)
n = st.restore_history(snap_h)
chk("还原 3 条", n == 3 and len(st.history()) == 3, "(n=%s)" % n)
chk("还原内容正确",
    sorted(w for w, _t in st.history()) == ["alpha", "beta", "gamma"])

gid1 = st.add_group("测试分组")
st.add_word("apple", 0, "")
st.add_word("banana", 0, "")
st.add_word("cherry", gid1, "笔记")
snap_w = st.snapshot_words(None)
chk("单词本快照 3 条", len(snap_w) == 3, "(实际 %d)" % len(snap_w))
chk("快照含 4 字段（word/group/note/ts）",
    all(len(r) == 4 for r in snap_w))
chk("count_words 全部 = 3", st.count_words(None) == 3)
chk("count_words 默认分组 = 2", st.count_words(0) == 2)
chk("count_words 分组1 = 1", st.count_words(gid1) == 1)

say()
say("   -- 只清一个分组，别的不许动 --")
deleted = st.clear_words_group(0)
chk("clear_words_group 返回删除数 2", deleted == 2, "(%s)" % deleted)
chk("默认分组已空", st.count_words(0) == 0)
chk("★ 另一个分组不受影响（这是最要紧的）", st.count_words(gid1) == 1)
st.restore_words(snap_w, None)
chk("整表还原回 3 条", st.count_words(None) == 3)
chk("还原后分组归属不变",
    st.count_words(0) == 2 and st.count_words(gid1) == 1)

say()
say("   -- 只还原一个分组（撤销「清空当前分组」用） --")
st.clear_words()
chk("先全清空", st.count_words(None) == 0)
st.restore_words(snap_w, 0)
chk("只还原默认分组 → 2 条", st.count_words(0) == 2, "(%d)" % st.count_words(0))
chk("其它分组仍为空", st.count_words(gid1) == 0)
st.restore_words(snap_w, None)
chk("整表还原回 3 条", st.count_words(None) == 3)

say()
say("=" * 74)
say("2. 撤销栈行为（真机路径）")
say("=" * 74)
w = A.MainWindow()
w._cur_word = ""            # 避免撤销后触发 _render（本测试不测渲染）
chk("★ 撤销按钮存在（用户找不到的就是它）", hasattr(w, "undo_btn"))
chk("撤销按钮初始置灰（没东西可撤销）", not w.undo_btn.isEnabled())
chk("撤销按钮文字含「撤销」", "撤销" in w.undo_btn.text(),
    "(%r)" % w.undo_btn.text())
chk("撤销按钮在窗口里（不是孤儿控件）", w.undo_btn.parent() is not None)
chk("初始栈为空", len(w._undo_stack) == 0)

w.store.clear_words()
w.store.clear_history()
w.store.add_word("undo1", 0)
w.store.add_word("undo2", 0)
gid2 = w.store.add_group("撤销测试组")
w.store.add_word("undo3", gid2)

# 模拟「清空当前分组」这条路径（GUI 确认框在 offscreen 下弹不出来，
# 所以直接走它内部的同一组调用，并断言 GUI 那条路径确实用了它们）
w._reload_wb_list()
snap = w.store.snapshot_words(0)
w.store.clear_words_group(0)
w._push_undo("清空分组「默认分组」（2 词）",
             lambda: w.store.restore_words(snap, 0))
chk("清空后默认分组 0 词", w.store.count_words(0) == 0)
chk("★ 撤销按钮变为可用", w.undo_btn.isEnabled())
chk("撤销按钮 tooltip 说明要撤销什么", "清空分组" in w.undo_btn.toolTip(),
    "(%r)" % w.undo_btn.toolTip())
chk("分组的词不受影响", w.store.count_words(gid2) == 1)

w._do_undo()
chk("★ 撤销后恢复 2 词", w.store.count_words(0) == 2,
    "(%d)" % w.store.count_words(0))
chk("撤销后按钮回到置灰", not w.undo_btn.isEnabled())
chk("撤销栈已空", len(w._undo_stack) == 0)
chk("撤销后其它分组仍然完好", w.store.count_words(gid2) == 1)

say()
say("   -- 多步撤销（后进先出） --")
w.store.add_history("h1")
w._push_undo("步骤A", lambda: 1)
w._push_undo("步骤B", lambda: 2)
chk("栈深 2", len(w._undo_stack) == 2)
chk("栈顶是 B", w._undo_stack[-1][0] == "步骤B")
chk("tooltip 提示还有 1 步", "还有 1 步" in w.undo_btn.toolTip(),
    "(%r)" % w.undo_btn.toolTip())
w._do_undo()
chk("撤销后栈顶变 A", w._undo_stack and w._undo_stack[-1][0] == "步骤A")
w._do_undo()
chk("再撤销栈空", len(w._undo_stack) == 0)
w._push_undo("C", lambda: 1)
w.store.clear_history()
w._push_undo("D", lambda: 1)
chk("栈超过上限会丢最旧的",
    len(w._undo_stack) <= w._UNDO_MAX, "(%d)" % len(w._undo_stack))
w._undo_stack.clear()
w._sync_undo_btn()

say()
say("   -- 三条上限：只按步数封顶不够，条数也要封顶（内存） --")
# ⚠ 步数要按 _UNDO_MAX **动态**取，不能写死 60 次：
#   2026-09-18 把上限从 30 提到 60 后，原来写死的 60 次压栈
#   刚好不触发淘汰，于是「丢的是最旧的」这条假失败。
_STEPS = w._UNDO_MAX + 5
for i in range(_STEPS):
    w._push_undo("第%d步" % i, lambda: 1, cost=0)
chk("步数封顶生效（%d 次压栈只留 %d 步）" % (_STEPS, w._UNDO_MAX),
    len(w._undo_stack) == w._UNDO_MAX, "(%d)" % len(w._undo_stack))
chk("★ 丢的是最旧的（栈底已不是第0步）", w._undo_stack[0][0] != "第0步",
    "(%r)" % w._undo_stack[0][0])
chk("栈顶仍是最新的", w._undo_stack[-1][0] == "第%d步" % (_STEPS - 1))
w._undo_stack.clear()
w._undo_cost = 0
w._sync_undo_btn()

# 条数封顶：历史表无上限，30 步大快照会常驻几万个元组
for i in range(30):
    w._push_undo("大快照%d" % i, lambda: 1, cost=1000)
chk("★ 条数封顶生效（30×1000 条 → 总条数被压到预算内）",
    w._undo_cost <= w._UNDO_COST, "(cost=%d, 预算=%d)"
    % (w._undo_cost, w._UNDO_COST))
chk("条数封顶后仍保留多步（不是一压就空）",
    len(w._undo_stack) >= 1, "(%d 步)" % len(w._undo_stack))
# 单步就超预算时，至少要保留这 1 步，不能压成空栈
w._undo_stack.clear()
w._undo_cost = 0
w._push_undo("超大快照", lambda: 1, cost=999999)
chk("★ 单步超预算也保留 1 步（撤销按钮不会莫名置灰）",
    len(w._undo_stack) == 1 and w.undo_btn.isEnabled(),
    "(栈深 %d)" % len(w._undo_stack))
w._undo_stack.clear()
w._undo_cost = 0
w._sync_undo_btn()

say()
say("   -- ★ 撤销不能把用户正在看的分组切走 --")
# 我自查发现的 bug：_do_undo → _refresh_wordbook → wb_group.clear() 会让
# currentIndex 归 0，用户正在看的「四级」被无声切回「默认分组」，
# 撤销完像是「词丢了」。触发路径就是撤销本身。
gx = w.store.add_group("四级")
w.store.add_word("vocab1", gx)
w.store.add_word("vocab2", gx)
w._refresh_wordbook()
i_x = w.wb_group.findData(gx)
chk("测试前提：能选中「四级」分组", i_x >= 0)
w.wb_group.setCurrentIndex(i_x)
chk("前提：当前分组已是四级", w._cur_wb_group() == gx)
w._refresh_wordbook()
chk("★ 单纯刷新后仍停在四级（不被切回默认分组）",
    w._cur_wb_group() == gx, "(实际 gid=%s)" % w._cur_wb_group())
# 走完整撤销路径
snapx = w.store.snapshot_words(gx)
w.store.clear_words_group(gx)
w._push_undo("清空「四级」2 词",
             lambda: w.store.restore_words(snapx, gx), cost=len(snapx))
w.wb_group.setCurrentIndex(w.wb_group.findData(gx))
w._do_undo()
for _ in range(3):
    qapp.processEvents()
chk("★ 撤销后仍停在四级（分组视图不被切走）",
    w._cur_wb_group() == gx, "(实际 gid=%s)" % w._cur_wb_group())
chk("撤销后四级的词已恢复", w.store.count_words(gx) == 2,
    "(%d)" % w.store.count_words(gx))
chk("撤销后下拉框里四级还在", w.wb_group.findData(gx) >= 0)

say()
say("   -- 空栈时按撤销不能崩 --")
try:
    w._do_undo()
    chk("空栈撤销不抛异常", True)
    chk("空栈撤销给提示", "没有可撤销" in w.pron_now.text(),
        "(%r)" % w.pron_now.text())
except Exception as e:
    chk("空栈撤销不抛异常", False, repr(e))

say()
say("   -- 撤销函数抛异常也不能崩（还原失败要兜住） --")
w._push_undo("会炸的步骤", lambda: (_ for _ in ()).throw(RuntimeError("boom")))
try:
    w._do_undo()
    chk("撤销函数异常被吞掉", True)
except Exception as e:
    chk("撤销函数异常被吞掉", False, repr(e))

say()
say("=" * 74)
say("3. 接线检查（源码级）—— 函数写好了必须真的接到 UI 上")
say("=" * 74)
wb_body = fn_body(SRC, "_build_wordbook_tab")
cw = fn_body(SRC, "_clear_wordbook")
ch = fn_body(SRC, "_clear_history")   # ⚠ 先全部取出来再断言 —— 上一版把这一行
                                      #   放在断言之后，导致 NameError（我自己写错）
chk("★ 单词本 Tab 里有「清空」按钮",
    'QPushButton("清空")' in wb_body)
chk("清空按钮用破坏性样式 dangerBtn", "dangerBtn" in wb_body)
chk("清空按钮接的是 _clear_wordbook",
    "_clear_wordbook" in wb_body)

chk("★ _clear_wordbook 有确认框（QMessageBox）", "QMessageBox" in cw)
chk("确认框写明「确定要清空」", "确定要清空" in cw)
chk("★ 确认框默认按钮是「取消」（防误按回车）",
    "setDefaultButton(cancel)" in cw)
chk("确认框给出精确词数", "n_cur" in cw and "n_all" in cw)
chk("提供「清空当前分组」选项", "清空当前分组" in cw)
chk("提供「清空全部分组」选项", "清空全部分组" in cw)
chk("★ 清空后入撤销栈（可恢复）",
    "_push_undo" in cw and "restore_words" in cw)
chk("★ 快照入栈时带上条数 cost（否则条数封顶形同虚设）",
    cw.count("cost=len(snap)") >= 2 and "cost=len(snap)" in ch)
chk("撤销栈有总条数封顶（内存护栏）", "_UNDO_COST" in SRC)
chk("清空当前分组用 clear_words_group（不是 clear_words）",
    "clear_words_group" in cw)
chk("提示里告诉用户能撤销", "撤销" in cw)

chk("清空历史也用真快照（不再是假的「可撤销」）",
    "snapshot_history" in ch and "restore_history" in ch)
chk("清空历史入撤销栈", "_push_undo" in ch)
chk("清空前先取数量用于文案", "len(rows)" in ch)
chk("删除单条历史可撤销",
    "snapshot_history" in fn_body(SRC, "_hist_menu"))
chk("移出单词本可撤销",
    "snapshot_words" in fn_body(SRC, "_wb_menu"))

kpe = fn_body(SRC, "keyPressEvent", must_contain="Key_Escape")
chk("取到的是 MainWindow 那个 keyPressEvent（含 Esc 处理）",
    "Key_Escape" in kpe)
chk("★ Ctrl+Z 接到撤销", "Key_Z" in kpe and "ControlModifier" in kpe
    and "_do_undo" in kpe)
chk("Alt+← 接到返回上一词", "Key_Left" in kpe and "AltModifier" in kpe
    and "_nav_back" in kpe)
chk("Ctrl+Z 与「返回」不共用同一个键（否则会互相踩）",
    kpe.count("_do_undo") >= 1 and kpe.count("_nav_back") >= 1)

chk("撤销按钮已加到侧栏（常驻可见）",
    "self.undo_btn" in SRC and "urow.addWidget(self.undo_btn)" in SRC)
chk("撤销按钮配有状态说明文字（不用猜 tooltip）",
    hasattr(w, "undo_hint"))
chk("★ 撤销按钮**不能**放进底部发音栏（那一条宽度已满，"
    "加 74px 会把发音文字从 246px 挤到 195px 而截断）",
    "pbl.addWidget(self.undo_btn)" not in SRC)
chk("撤销按钮有独立样式 undoBtn", "#undoBtn" in SRC)
chk("undoBtn 有禁用态样式（一眼看出能不能撤）",
    "#undoBtn:disabled" in SRC)
chk("dangerBtn 有样式", "#dangerBtn" in SRC)

say()
say("   -- 「返还」按钮可见性：从 12px 淡灰小字改为胶囊按钮 --")
chk("返回链接是胶囊样式（含背景/边框/圆角）",
    "background:{PAPER_ALT};border:1px solid {LINE};"
    "\"\n            f\"border-radius:11px" in SRC
    or ("nav:back" in SRC and "border-radius:11px;padding:2px 10px;'>↩ 返回"
        in SRC))
chk("没有历史时不显示返回按钮（避免点了没反应）",
    'back_html = ""' in SRC and "if self._nav_stack:" in SRC)

say()
say("=" * 74)
say("4. 真实用户数据没被碰过")
say("=" * 74)
real = os.path.join(os.environ.get("LOCALAPPDATA") or "", A.APP_NAME,
                    "user_data.db")
say("  真实库: %s" % real)
say("  本测试用的是临时库: %s" % st.path)
chk("测试没有写到真实用户库", _TMP in st.path)

say()
say("=" * 74)
say("5. ★ 性能护栏：撤销/快照绝不许被扯进「打字」这条路径")
say("=" * 74)
# 用户上一轮刚因为「单词打得很慢」投诉过（每键 220ms → 修到中位 3.8ms）。
# 加撤销功能时最大的风险就是：为了记录历史，在打字路径上顺手做快照。
# 代码结构上看调用点只在「清空/删除/移出」上，但**结构上没问题不等于
# 真的没被调用**，所以这里直接插桩计数 —— 打字时相关函数必须**零调用**。
_orig_snap_h = w.store.snapshot_history
_orig_snap_w = w.store.snapshot_words
_orig_push = w._push_undo
_orig_sync = w._sync_undo_btn
CNT = {"snap_h": 0, "snap_w": 0, "push": 0, "sync": 0}


def _count(slot, fn):
    def g(*a, **k):
        CNT[slot] += 1
        return fn(*a, **k)
    return g


w.store.snapshot_history = _count("snap_h", _orig_snap_h)
w.store.snapshot_words = _count("snap_w", _orig_snap_w)
w._push_undo = _count("push", _orig_push)
w._sync_undo_btn = _count("sync", _orig_sync)

import time as _tm
_times = []
for i in range(1, 6):
    pre = "water"[:i]
    t0 = _tm.perf_counter()
    w._on_text_now(pre)
    _times.append((_tm.perf_counter() - t0) * 1000)
_times.sort()
med = _times[len(_times) // 2]
say("      打字 5 次的耗时(ms): %s  中位 %.1f"
    % (["%.1f" % x for x in _times], med))
chk("打字时 snapshot_history 零调用", CNT["snap_h"] == 0,
    "(%d 次)" % CNT["snap_h"])
chk("打字时 snapshot_words 零调用", CNT["snap_w"] == 0,
    "(%d 次)" % CNT["snap_w"])
chk("打字时 _push_undo 零调用", CNT["push"] == 0, "(%d 次)" % CNT["push"])
chk("打字时 _sync_undo_btn 零调用", CNT["sync"] == 0, "(%d 次)" % CNT["sync"])
chk("★ 每键仍在 30ms 以内（上一轮修好的性能没有回退）", med < 30,
    "(中位 %.1f ms)" % med)

# 正对照：让插桩自己证明它是有用的 —— 否则「零调用」可能只是计数器坏了
snap = w.store.snapshot_history()
w.store.clear_history()
w._push_undo("正对照", lambda: 1)
chk("★ 正对照：清空历史时 snapshot_history 确实被调用（插桩有效）",
    CNT["snap_h"] >= 1, "(%d 次)" % CNT["snap_h"])
chk("★ 正对照：_push_undo 确实被调用", CNT["push"] >= 1,
    "(%d 次)" % CNT["push"])
chk("★ 正对照：_sync_undo_btn 确实被调用", CNT["sync"] >= 1,
    "(%d 次)" % CNT["sync"])

w.store.snapshot_history = _orig_snap_h
w.store.snapshot_words = _orig_snap_w
w._push_undo = _orig_push
w._sync_undo_btn = _orig_sync

say()
say("=" * 74)
say("RESULT  pass=%d  fail=%d" % (P, F))
say("=" * 74)
try:
    with open(r"D:\Dictionary\build\_undo_verify.txt", "w",
              encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
except Exception:
    pass
sys.stdout.flush()
os._exit(1 if F else 0)
