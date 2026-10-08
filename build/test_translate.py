# -*- coding: utf-8 -*-
"""整句翻译回归 —— 钉住「例句冒充译文」这个 bug。

用户原始反馈：「翻译句子功能好像有点问题，翻译出好多莫名其妙的句子」。
根因：旧 _translate_fallback 取 blng_sents_part[0].sentence-translation，
那是**例假的**译文。本测试的核心是**反向断言**：
  那条具体的垃圾输出（「一举两得」→ "If you enjoy the coast..."）必须消失。

因为要联网，不可达时相关用例记 SKIP 而不是 FAIL。
"""
import io
import sys
import time

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, r"D:\Dictionary\build")

import app as A

P = F = S = 0
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


def skip(name, why):
    global S
    S += 1
    say("  SKIP  %s (%s)" % (name, why))


say("=" * 74)
say("0. 纯函数：闸门 _same_sentence（这是本修复的核心）")
say("=" * 74)
# 必须通过：完全相同 / 仅标点大小写差异
chk("完全相同通过", A._same_sentence("I love you.", "I love you."))
chk("大小写/标点差异通过", A._same_sentence("I love you", "I love you."))
chk("中文完全相同通过", A._same_sentence("今天天气真好。", "今天天气真好。"))
# 必须拒绝：包含但更长（这就是旧版吐垃圾的路径）
chk("『包含但更长』被拒（Oh, Amy, I love you.）",
    not A._same_sentence("Oh, Amy, I love you.", "I love you."),
    "(len 比 0.69 < 0.9)")
chk("『包含但更长』被拒（今天天气真好，不是吗？）",
    not A._same_sentence("今天天气真好，不是吗？", "今天天气真好。"))
chk("完全不相干被拒", not A._same_sentence("I love you.", "一举两得"))
chk("空串被拒", not A._same_sentence("", "I love you."))
chk("太短的模糊匹配被拒", not A._same_sentence("go", "go to school"))

say()
say("=" * 74)
say("1. 旧版的具体垃圾输出必须消失（反向断言）")
say("=" * 74)
GARBAGE = [
    ("一举两得", "If you enjoy the coast and the country"),
    ("一举两得", "both worlds on this walk"),
    ("I love you.", "埃米"),                  # 旧版吐「啊，埃米，我爱你。」
    ("我要买 a new computer", "sucks"),        # 旧版吐 My computer sucks!
    ("Where are you from?", "顺便问一下"),       # 旧版吐「顺便问一下，你来自哪里？」
    ("今天天气真好。", "lovely day"),            # 旧版吐 It's a lovely day, isn't it?
    ("computer", "老出故障"),                  # 旧版把例句当 computer 的翻译
]
for inp, bad in GARBAGE:
    tr, src = A.translate_text(inp)
    if tr is None:
        skip("「%s」不含 %r" % (inp[:16], bad[:20]), "无译文（网络不可用）")
        continue
    chk("「%s」不再吐出 %r" % (inp[:16], bad[:18]), bad.lower() not in tr.lower(),
        "-> %r" % tr[:40])

say()
say("=" * 74)
say("2. 正确的译文（能连上就断言，连不上 SKIP）")
say("=" * 74)
EXPECT = [
    # (输入, 期望译文中必须出现的片段, 说明)
    ("I love you.", ["爱"], "英→中"),
    ("The weather is really nice today, so I want to go out for a walk.",
     ["天气", "散步"], "英→中 长句"),
    ("我今天早上起晚了，所以没赶上公交车，只好打车去公司。",
     ["late", "bus"], "中→英 长句"),
]
for inp, musts, note in EXPECT:
    tr, src = A.translate_text(inp)
    if tr is None:
        skip("%s「%s」" % (note, inp[:20]), "无译文")
        continue
    chk("%s「%s」译文合理" % (note, inp[:18]),
        all(m.lower() in tr.lower() for m in musts),
        "-> %r [%s]" % (tr[:44], src))
    say("        来源: %s" % src)

say()
say("=" * 74)
say("3. 短语型输入走有道（快、成语质量好）")
say("=" * 74)
tr, src = A.translate_text("一举两得")
if tr is None:
    skip("「一举两得」→ kill two birds", "无译文")
else:
    chk("「一举两得」拿到地道表达",
        "kill two birds" in tr.lower() or "two gains" in tr.lower()
        or "two birds" in tr.lower(),
        "-> %r [%s]" % (tr, src))

say()
say("=" * 74)
say("4. 结果绝不「与输入相同」（没翻就等于没结果）")
say("=" * 74)
for inp in ["hello world", "知识就是力量"]:
    tr, src = A.translate_text(inp)
    if tr is None:
        skip("「%s」不等价回显" % inp, "无译文")
        continue
    chk("「%s」不是原样回显" % inp,
        A._norm_sent(tr) != A._norm_sent(inp), "-> %r" % tr[:36])

say()
say("=" * 74)
say("5. 空输入")
say("=" * 74)
r, e = A.translate_text("")
chk("空输入给提示而非崩溃", r is None and "请输入" in e, "(%r)" % e)

say()
say("=" * 74)
say("6. 翻译对话框接线（源码级 + 真构造）")
say("=" * 74)
import os as _os
_os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtWidgets import QApplication as _QApp
_q = _QApp.instance() or _QApp([])

_src = open(r"D:\Dictionary\build\app.py", encoding="utf-8").read()
chk("★ 对话框改用真异步（run_async），不再 processEvents 假异步",
    "run_async(work, done)" in _src
    and "QApplication.processEvents()\n        result, src = translate_text"
    not in _src)
chk("有「网页翻译」零依赖退路按钮",
    'QPushButton("网页翻译")' in _src and "def _open_web" in _src)
chk("有「复制译文」按钮",
    'QPushButton("复制译文")' in _src and "def _copy_out" in _src)
chk("失败时给出可操作下一步（不是只说「失败」）",
    "点上方「<b>网页翻译</b>」" in _src)
chk("Ctrl+Enter 可翻译", "ControlModifier" in _src and "Key_Return" in _src)
chk("有请求序号防慢请求覆盖新结果", "self._req" in _src)

try:
    dlg = A.TranslateDialog()
    chk("对话框可构造", True)
    chk("有 网页翻译 按钮实例", hasattr(dlg, "web_btn"))
    chk("有 复制译文 按钮实例", hasattr(dlg, "copy_btn"))
    chk("初始状态不是 busy", dlg._busy is False)
    # 空输入不该发起请求，也不该卡住 busy
    dlg.in_edit.setPlainText("")
    dlg._do_translate()
    chk("空输入给提示且不置 busy",
        dlg._busy is False and "请输入" in dlg.status.text(),
        "(%r)" % dlg.status.text())
    # 真跑一次异步（能连上就有结果，连不上也应回到「未取到译文」）
    dlg.in_edit.setPlainText("I love you.")
    dlg._do_translate()
    chk("发起后进入 busy 且按钮禁用",
        dlg._busy is True and not dlg.trans_btn.isEnabled())
    import time as _t
    for _ in range(120):
        _q.processEvents()
        if not dlg._busy:
            break
        _t.sleep(0.1)
    chk("★ 异步回调最终回到非 busy（不会卡死）", dlg._busy is False)
    chk("两个按钮恢复可用", dlg.trans_btn.isEnabled()
        and dlg.trans_btn.text() == "翻译")
    say("        最终状态: %r" % dlg.status.text())
    say("        输出前 60 字: %r" % dlg.out_view.toPlainText()[:60])
    if dlg._last_out:
        chk("有译文写进结果区", len(dlg.out_view.toPlainText()) > 0)
        chk("译文与输入不同（真的翻了）",
            A._norm_sent(dlg._last_out) != A._norm_sent("I love you."))
    else:
        skip("有译文写进结果区", "网络不可用")
    # ---- 重复提交 / 慢请求覆盖（用可控的假 translate 才测得准）----
    # 为什么不用真网络测：两次请求耗时都是 1.5s 上下，谁先回来不确定，
    # 只能靠运气撞「旧的后回来」这个顺序。改成假函数，用 Event 把旧请求
    # 死死卡住，就能确定性地构造「新结果先到、旧结果后到」。
    import threading as _th
    _gate = _th.Event()
    _seen_lang = []

    def _fake(text, lang="en"):
        # ⚠ 签名必须跟产品一致：translate_text(text, lang)。
        #   2026-09-18 多语言改造后对话框会传第二个参数，只收一个参数
        #   会 TypeError → 被 work() 的 except 吞掉 → 结果永远是空
        #   （当时表现为「新请求的结果已显示 ('')」两条假失败）。
        _seen_lang.append(lang)
        if text == "AAA":
            _gate.wait(6)          # 旧请求卡住不返回
            return "OLD-RESULT", "fake"
        return "NEW-RESULT", "fake"

    _real_tr = A.translate_text
    A.translate_text = _fake
    try:
        dlg.in_edit.setPlainText("AAA")
        dlg._do_translate()
        req_a = dlg._req
        dlg.in_edit.setPlainText("BBB")
        dlg._do_translate()
        chk("★ 等待期间再次提交会被受理（不再「按了没反应」）",
            dlg._req == req_a + 1, "(%d -> %d)" % (req_a, dlg._req))
        for _ in range(60):
            _q.processEvents()
            if dlg._last_out == "NEW-RESULT":
                break
            _t.sleep(0.05)
        chk("新请求的结果已显示", dlg._last_out == "NEW-RESULT",
            "(%r)" % dlg._last_out)
        _gate.set()                # 放行旧请求，让它的晚到结果回来
        for _ in range(60):
            _q.processEvents()
            _t.sleep(0.05)
        chk("★ 旧请求的晚到结果被丢弃（序号机制生效）",
            dlg._last_out == "NEW-RESULT", "(%r)" % dlg._last_out)
        chk("旧请求回来也不会把 busy 卡住", dlg._busy is False)
        # ---- 语言模式确实被传给了翻译引擎（多语言双向的前提）----
        chk("★ 对话框把自己的语言模式传给了 translate_text",
            _seen_lang and all(x == dlg.lang for x in _seen_lang),
            "(dlg.lang=%r, 实收 %r)" % (dlg.lang, _seen_lang[:4]))
    finally:
        A.translate_text = _real_tr

    # 换个语言模式再构造一次：标题/方向说明要跟着变，
    # 且默认值必须是 en（老调用方不传参也不能炸）
    _d_ja = A.TranslateDialog(lang="ja")
    chk("对话框可按日语模式构造", _d_ja.lang == "ja")
    chk("窗口标题标出目标语言", "日语" in _d_ja.windowTitle(),
        "(%r)" % _d_ja.windowTitle())
    chk("方向说明写明 中文 ⇄ 日语",
        "中文 → 日语" in _d_ja.dir_hint.text(),
        "(%r)" % _d_ja.dir_hint.text())
    chk("不传 lang 时默认英语（向后兼容）",
        A.TranslateDialog().lang == "en")
except Exception as e:
    chk("对话框可构造", False, repr(e))

say()
say("=" * 74)
say("RESULT  pass=%d  fail=%d  skip=%d" % (P, F, S))
say("=" * 74)
try:
    with open(r"D:\Dictionary\build\_trans_verify.txt", "w",
              encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
except Exception:
    pass
sys.stdout.flush()
import os
os._exit(1 if F else 0)
