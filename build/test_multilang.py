# -*- coding: utf-8 -*-
"""多语言双向 + 小贴士折叠 + 撤销跳转 —— 用户最新三条反馈。

  反馈④「为啥不能撤销跳转操作」
        → 根因：撤销栈里只有**破坏性数据操作**（清空历史/删词/移出），
          点释义里的蓝色词跳走之后「↩ 撤销」是灰的、Ctrl+Z 没反应。
          现在「跳转」和「返回」两个方向都进栈，且对称。
  反馈⑤「那个小贴士有点挡着我了」
        → 根因：侧栏小贴士是不可折叠的大块文本，常驻占 ~150px。
          现在可折叠，并把选择写进 dict_config.json（下次打开保持）。
  反馈⑥「除了英语的其他语言为啥不能双向翻译」
        → 三个根因（都要测）：
          ① translate_text 语言对写死 zh-CN|en，跟当前语言模式无关
          ② 反查判断写了 `direction == "cn2en" and self.lang == "en"`，
             非英语模式输入中文被当外语词直接查，必然查不到
          ③ 非英语词库 translation 字段 0 条非空（数据本身没中文释义）

⚠ 本测试**绝不允许**碰真实用户数据：UserStore 落临时目录，
  dict_config.json 也被重定向到临时文件。
"""
import io
import json
import os
import sys
import tempfile
import time

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8",
                              errors="replace")
sys.path.insert(0, r"D:\Dictionary\build")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

qapp = QApplication(sys.argv)
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


def pump(sec=6.0, until=None):
    """转事件循环，让 run_async 的回调落地。"""
    t0 = time.time()
    while time.time() - t0 < sec:
        qapp.processEvents()
        if until is not None and until():
            return True
        time.sleep(0.02)
    return until() if until is not None else True


# ---- 隔离用户数据：UserStore 落临时目录
_TMP = tempfile.mkdtemp(prefix="dictml_")
_orig_store_init = A.UserStore.__init__


def _patched_store_init(self, path=None):
    _orig_store_init(self, os.path.join(_TMP, "user_data.db"))


A.UserStore.__init__ = _patched_store_init

# ---- 隔离配置：dict_config.json 也重定向到临时文件
_orig_cfg_path = A.CONFIG_PATH
A.CONFIG_PATH = os.path.join(_TMP, "dict_config.json")
_CFG_BACKUP = dict(A.CONFIG)

SRC = open(r"D:\Dictionary\build\app.py", encoding="utf-8").read()


def fn_body(text, name, must_contain=None):
    """取某个方法的源码正文（同名方法要能挑，见 test_undo_wordbook 的坑 11）。"""
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


try:
    # ==================================================================
    say("=" * 74)
    say("1. 语言判定与语言对（离线，确定性）")
    say("=" * 74)
    chk("「学校」算中文（日语里同形，无法用字符区分，按中文处理）",
        A._is_zh_text("学校"))
    chk("「学校へ行く」算日语（有假名）", not A._is_zh_text("学校へ行く"))
    chk("「私は学生です」算日语", not A._is_zh_text("私は学生です"))
    chk("「コンピュータ」算日语（片假名）", not A._is_zh_text("コンピュータ"))
    chk("「bonjour」不算中文", not A._is_zh_text("bonjour"))
    chk("_has_kana 认得平假名", A._has_kana("あいう"))
    chk("_has_kana 认得片假名", A._has_kana("アイウ"))
    chk("_has_kana 不误判纯汉字", not A._has_kana("学校"))
    chk("_has_cjk 对日语汉字也为真（所以不能拿它当「是中文」）",
        A._has_cjk("学校") and not A._is_zh_text("学校へ"))

    say()
    say("   -- tr_lang_pair：语言对随语言模式变（旧版写死中英） --")
    for lang, code in (("en", "en"), ("ja", "ja"), ("fr", "fr"),
                       ("yue", "yue")):
        s_, d_ = A.tr_lang_pair("我爱你", lang)
        chk("中文 → %s：源=zh-CN 目标=%s" % (lang, code),
            (s_, d_) == (A.ZH_MM, code), "(实得 %r)" % ((s_, d_),))
        s_, d_ = A.tr_lang_pair("abcdefg", lang)
        chk("%s → 中文：源=%s 目标=zh-CN" % (lang, code),
            (s_, d_) == (code, A.ZH_MM), "(实得 %r)" % ((s_, d_),))
    chk("四种语言都在 TR_MYMEMORY 里",
        set(A.TR_MYMEMORY) >= {"en", "ja", "fr", "yue"})
    chk("未知语言回落英语（不炸）",
        A.tr_lang_pair("你好", "de")[1] == "en")

    say()
    say("   -- _tr_candidates：机翻结果切片（要能容忍噪音） --")
    chk("去括号注释",
        A._tr_candidates("ありがとうございます）。") == ["ありがとうございます"],
        "(%r)" % A._tr_candidates("ありがとうございます）。"))
    chk("逗号切分并去掉标点",
        A._tr_candidates("eau， 水") == ["eau", "水"],
        "(%r)" % A._tr_candidates("eau， 水"))
    chk("整句保持完整", A._tr_candidates("今日はいい天気ですね")
        == ["今日はいい天気ですね"])
    chk("空输入给空列表", A._tr_candidates("") == [])
    chk("去重", A._tr_candidates("水、水") == ["水"],
        "(%r)" % A._tr_candidates("水、水"))

    # ==================================================================
    say()
    say("=" * 74)
    say("2. ★ 通道路由：非英语绝不走中英专用通道")
    say("=" * 74)
    # 有道那三条通道（suggest / web_trans / blng_sents）只覆盖中英：
    # 实测对日语词返回 0 条、对法语词返回的是**英文词**的释义，
    # 拿去用会再次产出「莫名其妙的句子」。所以非英语模式必须一条都不试。
    CNT = {"mm": 0, "yd_phrase": 0, "yd_ex": 0}
    seen_pairs = []

    _o_mm = A._translate_mymemory
    _o_ydp = A._translate_youdao_phrase
    _o_yde = A._translate_youdao_example

    # ⚠ 这里直接替掉 _translate_mymemory 并**在同一处记录语言对**。
    #   第一版写的是「替掉 _translate_mymemory + 另外包一层 _mymemory_raw」——
    #   结果内层那个 spy 永远不会被调到（外层已经返回固定值了），
    #   于是 seen_pairs 恒为空、6 条断言假失败。
    MM_OK = {"v": True}
    # ⚠ 2026-10-08：假 MyMemory 必须返回**像目标语言**的文本。
    #   翻译结果现在要过语言闸门（_looks_like_target），而
    #   「MM-RESULT」这种纯 ASCII 串对 ja/yue 来说一眼假 ——
    #   闸门拒收它是**正确行为**，不是回归。旧版返回 MM-RESULT 是
    #   因为那时根本没有闸门。
    MM_FAKE = {"ja": "大好き", "fr": "je t'aime bien",
               "yue": "我好開心", "en": "MM-RESULT"}
    #   ⚠ yue 这一格是「反面教材」：它就是 MyMemory 粤语通道的真实产出
    #   （繁体中文、没有粤式字），闸门应当拒收它。

    def _spy_mm(text, lang="en"):
        CNT["mm"] += 1
        src, dst = A.tr_lang_pair(text, lang)
        seen_pairs.append("%s|%s" % (src, dst))
        if not MM_OK["v"]:
            return (None, None)
        return (MM_FAKE.get(lang, "MM-RESULT"), "fake-mm")

    def _spy(slot, ret):
        def g(*a, **k):
            CNT[slot] += 1
            return ret
        return g

    A._translate_mymemory = _spy_mm
    A._translate_youdao_phrase = _spy("yd_phrase", ("YD-RESULT", "fake-yd"))
    A._translate_youdao_example = _spy("yd_ex", ("YD-EX", "fake-ex"))
    try:
        for lang in ("ja", "fr", "yue"):
            CNT.update(mm=0, yd_phrase=0, yd_ex=0)
            seen_pairs.clear()
            r, s = A.translate_text("我爱你", lang)
            if lang == "yue":
                # 粤语是**已知不可用**的那一格：MyMemory 的 yue 通道
                # 实测只做简→繁（点解→點解、我今日好开心→我今日好開心），
                # 给不出粤式表达。闸门必须拒收并说清原因，
                # 而不是把「我好開心」当粤语译文端给用户。
                chk("★ yue 模式拒收「只是繁体中文」的伪粤语译文",
                    r is None, "(%r)" % r)
                chk("★ yue 模式说清是简繁转换 incapable",
                    "简→繁" in (s or ""), "(%r)" % (s or "")[:50])
            else:
                chk("★ %s 模式翻译走 MyMemory" % lang, r == MM_FAKE[lang],
                    "(%r)" % r)
            chk("★ %s 模式拒绝有道 suggest" % lang, CNT["yd_phrase"] == 0,
                "(%d 次)" % CNT["yd_phrase"])
            chk("★ %s 模式拒绝有道例句通道" % lang, CNT["yd_ex"] == 0,
                "(%d 次)" % CNT["yd_ex"])
            chk("%s 模式的 MyMemory 语言对是 zh-CN|%s" % (lang, lang),
                seen_pairs and seen_pairs[0] == "zh-CN|%s" % lang,
                "(%r)" % seen_pairs)

        say()
        say("   -- ★ 关键对照：MyMemory 失败时，非英语**不许**退回中英通道 --")
        # 这一条才是真正的分水岭。只要 MyMemory 有结果，英语模式也会
        # 立刻返回，看不出中英通道在不在链上；必须让它失败才暴露差异。
        MM_OK["v"] = False
        for lang in ("ja", "fr", "yue"):
            CNT.update(mm=0, yd_phrase=0, yd_ex=0)
            r, s = A.translate_text("我爱你", lang)
            chk("★ %s 模式 MyMemory 失败后不会退回中英通道（否则又出"
                "莫名其妙的句子）" % lang,
                CNT["yd_phrase"] == 0 and CNT["yd_ex"] == 0,
                "(suggest %d 次 / 例句 %d 次)" % (CNT["yd_phrase"],
                                                CNT["yd_ex"]))
            chk("%s 模式失败时如实报错而非硬凑" % lang, r is None,
                "(%r)" % r)

        CNT.update(mm=0, yd_phrase=0, yd_ex=0)
        seen_pairs.clear()
        r, s = A.translate_text("I love you.", "en")
        chk("★ 英语模式 MyMemory 失败后仍会用有道短语通道（非英语没有，"
            "英语有 —— 这就是「按语言分开的通道顺序」）",
            CNT["yd_phrase"] >= 1, "(%d 次)" % CNT["yd_phrase"])
        chk("英语模式最终拿到结果", r == "YD-RESULT", "(%r)" % r)
        chk("英语模式的 MyMemory 语言对是 en|zh-CN",
            seen_pairs and seen_pairs[0] == "en|zh-CN",
            "(%r)" % seen_pairs)
        MM_OK["v"] = True

        # 译文质量闸门（2026-10-08）：MyMemory 是众包记忆库，会串语言
        # ——实测「我爱你」中→法返回 "I Love You"、「点解」中→粤只做
        # 简繁转换。这类结果必须**如实报错**，不能当译文给用户。
        say()
        say("   -- 译文质量闸门：不像目标语言的结果一律拒收 --")
        _o_mm = A._translate_mymemory
        try:
            for lang, bad, why in (("fr", "I Love You", "英语冒充法语"),
                                   ("ja", "I love you", "英语冒充日语"),
                                   ("yue", "點解", "粤语只做简繁转换")):
                A._translate_mymemory = (
                    lambda t, lang="en", _b=bad: (_b, "fake-mm"))
                r, s = A.translate_text("我爱你", lang)
                chk("★ %s 模式拒收%s的译文" % (lang, why), r is None,
                    "(%r)" % r)
                chk("   拒收后给出可操作的下一步", bool(s) and "网页翻译" in s,
                    "(%r)" % (s or "")[:60])
        finally:
            A._translate_mymemory = _o_mm

        # 正对照：证明插桩本身是有效的（否则「0 次」可能只是计数器坏了）
        CNT["yd_phrase"] = 0
        A._translate_youdao_phrase("test")
        chk("★ 正对照：直接调用时插桩确实计数（插桩有效）",
            CNT["yd_phrase"] >= 1, "(%d 次)" % CNT["yd_phrase"])
    finally:
        A._translate_mymemory = _o_mm
        A._translate_youdao_phrase = _o_ydp
        A._translate_youdao_example = _o_yde

    # ==================================================================
    say()
    say("=" * 74)
    say("3. 中文 → 日语/法语/粤语 反查（真机路径 + 假翻译，不联网）")
    say("=" * 74)
    w = A.MainWindow()
    chk("主窗口可构造", w is not None)

    _o_tr = A.translate_text
    _o_sched_online = w._schedule_online_enhance
    w._schedule_online_enhance = lambda *a, **k: None   # 别让本测试打网络

    CALLS = []

    # ⚠ 2026-10-08：translate_text 多了 strict 关键字（反查路径要
    #   strict=False —— 它要的正是简→繁转换，不能套语言闸门）。
    #   假函数必须收下 **kw，否则这里会 TypeError、
    #   后面 3 条断言全部假失败（签名没跟上产品演进，不是产品回归）。
    def _fake_tr(text, lang="en", **kw):
        CALLS.append((text, lang, kw.get("strict")))
        return {"ja": "水", "fr": "eau， 水", "yue": "水"}.get(lang, "water"), "fake"

    A.translate_text = _fake_tr
    try:
        w.lang = "ja"
        w.engine = w.dicts.get("ja") or w.dicts["en"]
        w._last_query = "水"
        w._search_cn_foreign("水")
        chk("★ 发起反查时立刻给出「联网翻译中」反馈（不假装卡住）",
            "翻译中" in w.list_hint.text() or "联网" in w.list_hint.text(),
            "(%r)" % w.list_hint.text())
        ok = pump(8, lambda: w._cn_fr_now is not None)
        chk("异步回调最终落地", ok)
        chk("★ 反查把**当前语言模式**传给了翻译引擎",
            CALLS and CALLS[0][1] == "ja", "(%r)" % CALLS[:2])
        chk("★ 反查走 strict=False（要简→繁转换，不能被语言闸门挡）",
            CALLS and CALLS[0][2] is False, "(%r)" % CALLS[:2])
        chk("反查结果记录了机翻原文", w._cn_fr_now and w._cn_fr_now[1] == "水",
            "(%r)" % (w._cn_fr_now[1] if w._cn_fr_now else None))

        say("        列表条数=%d  hint=%r"
            % (w.result_list.count(), w.list_hint.text()))

        say()
        say("   -- 缓存：同一个词第二次不再联网 --")
        CALLS.clear()
        w._cn_fr_now = None
        w._search_cn_foreign("水")
        chk("命中缓存时同步渲染（不必等网络）", w._cn_fr_now is not None)
        chk("★ 命中缓存时零网络请求", len(CALLS) == 0, "(%d 次)" % len(CALLS))

        say()
        say("   -- 请求序号：慢的旧请求不得覆盖后发请求 --")
        import threading as _th
        gate = _th.Event()
        CALLS.clear()

        def _slow_tr(text, lang="en", **kw):
            CALLS.append((text, lang, kw.get("strict")))
            if text == "旧":
                gate.wait(6)
                return "旧的机翻结果", "fake"
            return "新的机翻结果", "fake"

        A.translate_text = _slow_tr
        w._last_query = "旧"
        w._search_cn_foreign("旧")
        w._last_query = "新"
        w._search_cn_foreign("新")
        pump(6, lambda: w._cn_fr_now and w._cn_fr_now[0] == "新")
        chk("新请求的结果先显示", w._cn_fr_now and w._cn_fr_now[0] == "新",
            "(%r)" % (w._cn_fr_now[0] if w._cn_fr_now else None))
        gate.set()
        pump(2)
        chk("★ 慢的旧请求回来后被丢弃（序号机制生效）",
            w._cn_fr_now and w._cn_fr_now[0] == "新",
            "(%r)" % (w._cn_fr_now[0] if w._cn_fr_now else None))

        say()
        say("   -- 词库查不到时，如实说明并给出机翻（不编） --")
        A.translate_text = lambda t, lang="en", **kw: ("これはペンです", "fake")
        w.lang = "ja"
        w._last_query = "斑马鱼"
        w._search_cn_foreign("斑马鱼")
        pump(6, lambda: w._cn_fr_now and w._cn_fr_now[0] == "斑马鱼")
        html_txt = w.detail.toPlainText() or ""
        chk("★ 未收录时把机翻结果原样给用户（比「未找到」有用）",
            "机翻" in html_txt, "(%r)" % html_txt[:80])
    finally:
        A.translate_text = _o_tr
        w._schedule_online_enhance = _o_sched_online

    say()
    say("   -- 接线检查：非英语模式输入中文真的会触发反查（源码级） --")
    body = fn_body(SRC, "_on_text_now", must_contain="_search_cn_foreign")
    chk("_on_text_now 里有非英语中文分支", bool(body))
    chk("★ 该分支不再被 `self.lang == \"en\"` 限制死",
        "self.lang != \"en\" and _is_zh_text(t)" in body, "")
    chk("★ 先给本语言词条一次机会（日语汉字词与中文同形）",
        "suggest(t, 60, self._dict_key())" in body, "")
    body = fn_body(SRC, "_search_cn_foreign")
    chk("★ 反查走真异步（run_async）而不是主线程同步等",
        "run_async(" in body and "processEvents" not in body, "")
    chk("反查有请求序号防覆盖", "_cn_fr_req" in body, "")

    # ==================================================================
    say()
    say("=" * 74)
    say("4. 非英语词条的「中文意思」机翻（并标注为机翻参考）")
    say("=" * 74)
    MT = []

    _o_mmr2 = A._mymemory_raw

    def _fake_mmr(text, pair, allow_same=False):
        MT.append((text, pair, allow_same))
        return "水", "fake"

    A._mymemory_raw = _fake_mmr
    try:
        # ---- 护栏①：打字时的候选预览（record=False）不许联网 ----
        w.lang = "ja"
        w.engine = w.dicts.get("ja") or w.dicts["en"]
        w._mt_cache.clear()
        w._mt_fetching.clear()
        w._cur_word = ""
        MT.clear()
        probe = None
        for cand in w.engine.suggest("", 5, w._dict_key()) or []:
            probe = cand.get("word")
            break
        if not probe:
            for cand in w.engine.suggest("a", 5, w._dict_key()) or []:
                probe = cand.get("word")
                break
        if probe:
            w._render(probe, record=False)   # 打字预览这条路径
            chk("★ 打字预览（record=False）不触发联网机翻",
                len(MT) == 0, "(%d 次)" % len(MT))
        else:
            skip("打字预览不触发联网机翻", "该语言词库没有可预览的词")

        # ---- 护栏②：用户主动查（record=True）才联网 ----
        w._mt_cache.clear()
        w._mt_fetching.clear()
        MT.clear()
        if probe:
            w._render(probe, record=True)
            chk("★ 用户主动查看时才会联网机翻",
                len(MT) >= 1 or (w.lang, probe) in w._mt_cache,
                "(%d 次)" % len(MT))
            chk("机翻用 allow_same=True（日语汉字词与中文同形是常态）",
                all(x[2] is True for x in MT) if MT else True,
                "(%r)" % (MT[:1],))

        say()
        say("   -- 缓存与去重 --")
        w._mt_cache.clear()
        w._mt_fetching.clear()
        MT.clear()
        A._mymemory_raw = lambda t, p, allow_same=False: (MT.append(1) or "水", "fake")
        w._schedule_mt_zh("water_x")
        w._schedule_mt_zh("water_x")
        n_immediate = len(MT)
        chk("同一个词在飞行中不重复请求（_mt_fetching 去重）",
            n_immediate <= 1, "(%d 次)" % n_immediate)
        pump(4, lambda: ("ja", "water_x") in w._mt_cache)
        chk("结果写进缓存", ("ja", "water_x") in w._mt_cache)
        MT.clear()
        w._schedule_mt_zh("water_x")
        chk("★ 已缓存则不再联网", len(MT) == 0, "(%d 次)" % len(MT))
    finally:
        A._mymemory_raw = _o_mmr2

    # ---- 文案：必须标「机翻参考」，别让人以为是词典原文 ----
    chk("★ 非英语词条的释义标注了「机翻参考」", "机翻参考" in SRC)
    chk("释义区在非英语模式下叫「中文意思」", 'self._section("中文意思")' in SRC)
    body = fn_body(SRC, "_schedule_mt_zh")
    chk("★ 机翻只由 record=True 触发（源码注释与调用点都在）",
        "record=True" in body and "run_async(" in body, "")

    # ==================================================================
    say()
    say("=" * 74)
    say("5. 小贴士可折叠，且记住选择")
    say("=" * 74)
    chk("★ 有折叠按钮（用户说「有点挡着我了」）",
        hasattr(w, "tip_toggle"))
    chk("有独立标题行", hasattr(w, "tip_title"))
    chk("折叠按钮在窗口里（不是孤儿控件）",
        w.tip_toggle.parent() is not None)

    # 从干净状态开始：确保 CONFIG 里没有这个键
    A.CONFIG.pop("tip_collapsed", None)
    w._apply_tip_collapsed(w._tip_saved_collapsed())
    # ⚠ 判可见性必须用 isHidden()，**不能用 isVisible()**：
    #   offscreen 下顶层窗口从未 show() 过，子控件的 isVisible() 恒为 False，
    #   于是「默认展开」和「再点一下展开」两条会假失败（第一版就踩了）。
    #   isHidden() 问的是「有没有被显式 hide 掉」，不受窗口是否显示影响。
    chk("默认是展开的（不改变老用户习惯）",
        not w.tip.isHidden() and not w._tip_collapsed)
    chk("展开时按钮写「收起 ▾」", w.tip_toggle.text() == "收起 ▾",
        "(%r)" % w.tip_toggle.text())
    chk("展开时标题就是「小贴士」", w.tip_title.text() == "小贴士",
        "(%r)" % w.tip_title.text())

    w._toggle_tip()
    chk("★ 点一下收起来了", w._tip_collapsed and w.tip.isHidden())
    chk("收起后按钮写「展开 ▸」", w.tip_toggle.text() == "展开 ▸",
        "(%r)" % w.tip_toggle.text())
    chk("收起后标题提示已收起", "已收起" in w.tip_title.text(),
        "(%r)" % w.tip_title.text())
    chk("按钮 tooltip 说明接下来会发生什么",
        "展开" in w.tip_toggle.toolTip(), "(%r)" % w.tip_toggle.toolTip())

    # 用户的原话是「挡着我了」——「收起」必须真的省出高度，不能只是
    # 把字藏起来但布局还占着同样的位置。
    h_collapsed = w.tip_box.sizeHint().height()
    w._toggle_tip()
    h_expanded = w.tip_box.sizeHint().height()
    w._toggle_tip()
    say("      小贴士高度：收起 %dpx / 展开 %dpx"
        % (h_collapsed, h_expanded))
    chk("★ 收起后确实省出高度（不是把字藏起来还占地方）",
        h_expanded - h_collapsed >= 60,
        "(收起 %d / 展开 %d)" % (h_collapsed, h_expanded))

    say()
    say("   -- 选择要落盘，下次打开保持 --")
    chk("★ 选择已写进配置（内存）",
        A.CONFIG.get("tip_collapsed") == "1",
        "(%r)" % A.CONFIG.get("tip_collapsed"))
    chk("★ 选择已写进 dict_config.json",
        os.path.exists(A.CONFIG_PATH)
        and json.load(open(A.CONFIG_PATH, encoding="utf-8")).get(
            "tip_collapsed") == "1")
    chk("写盘用字符串 \"1\"/\"0\"（load_config 会丢弃非字符串值）",
        isinstance(A.CONFIG.get("tip_collapsed"), str))

    w2 = A.MainWindow()
    chk("★ 新开的窗口保持收起状态（不是每次都要重新收）",
        w2._tip_collapsed and w2.tip.isHidden())

    w._toggle_tip()
    chk("再点一下展开", not w._tip_collapsed and not w.tip.isHidden())
    chk("展开的选择也写进配置", A.CONFIG.get("tip_collapsed") == "0",
        "(%r)" % A.CONFIG.get("tip_collapsed"))
    chk("写配置时没把整份文件写坏（仍是合法 JSON 对象）",
        isinstance(json.load(open(A.CONFIG_PATH, encoding="utf-8")), dict))
    w2._tip_collapsed = None

    # ==================================================================
    say()
    say("=" * 74)
    say("6. ★ 撤销跳转 / 撤销返回（两个方向对称）")
    say("=" * 74)
    w.lang = "en"
    w.engine = w.dicts["en"]
    w._schedule_online_enhance = lambda *a, **k: None
    w._undo_stack.clear()
    w._undo_cost = 0
    w._sync_undo_btn()
    w._nav_stack = []
    w._cur_word = ""

    chk("跳转前「撤销」是灰的", not w.undo_btn.isEnabled())

    # 挑两个真实存在的词，走真正的 _render
    import sqlite3
    con = sqlite3.connect(r"D:\Dictionary\dict.db")
    words = [r[0] for r in con.execute(
        "select word from dict where length(word) between 4 and 6 "
        "and word glob '[a-z]*' limit 2")]
    con.close()
    if len(words) < 2:
        skip("撤销跳转", "词库里没取到两个测试用词")
    else:
        wa, wb = words[0], words[1]
        w._render(wa, record=True)
        chk("第一个词渲染成功", w._cur_word == wa, "(%r)" % w._cur_word)
        chk("第一个词不进撤销栈（没有「上一步」）",
            len(w._undo_stack) == 0, "(%d)" % len(w._undo_stack))

        w._render(wb, record=True)
        chk("跳转后当前词变了", w._cur_word == wb, "(%r)" % w._cur_word)
        chk("★ 跳转后「撤销」变为可用", w.undo_btn.isEnabled())
        chk("★ 撤销栈里那一步说明是「跳转回…」",
            w._undo_stack and "跳转回" in w._undo_stack[-1][0],
            "(%r)" % (w._undo_stack[-1][0] if w._undo_stack else None))
        chk("导航栈记下了上一个词", w._nav_stack == [wa],
            "(%r)" % w._nav_stack)

        w._do_undo()
        chk("★ 撤销跳转回到上一个词", w._cur_word == wa,
            "(%r)" % w._cur_word)
        chk("★ 撤销后搜索框也跟着回填（不是只有详情栏变了）",
            w.search_edit.text() == wa, "(%r)" % w.search_edit.text())
        chk("★ 撤销后导航栈也还原（否则「返回」落点会错位）",
            w._nav_stack == [], "(%r)" % w._nav_stack)
        chk("撤销后按钮回到置灰", not w.undo_btn.isEnabled())

        say()
        say("   -- 反向：点「返回」本身也要能撤销 --")
        w._undo_stack.clear()
        w._undo_cost = 0
        w._nav_stack = []
        w._cur_word = ""
        w._render(wa, record=True)
        w._render(wb, record=True)
        w._undo_stack.clear()          # 只看「返回」这一步
        w._undo_cost = 0
        w._nav_back()
        chk("返回后当前词是上一个", w._cur_word == wa, "(%r)" % w._cur_word)
        chk("★ 「返回」自己也进撤销栈（不是单向门）",
            w._undo_stack and "回到" in w._undo_stack[-1][0],
            "(%r)" % (w._undo_stack[-1][0] if w._undo_stack else None))
        w._do_undo()
        chk("★ 撤销「返回」后回到返回前的词", w._cur_word == wb,
            "(%r)" % w._cur_word)

        say()
        say("   -- 空栈与异常不该崩 --")
        w._undo_stack.clear()
        w._undo_cost = 0
        w._nav_stack = []
        try:
            w._do_undo()
            w._nav_back()
            chk("空栈时按撤销 / 返回都不崩", True)
        except Exception as e:
            chk("空栈时按撤销 / 返回都不崩", False, repr(e))

    say()
    say("   -- 接线检查（源码级） --")
    body = fn_body(SRC, "_render", must_contain="_push_undo")
    chk("★ _render 里跳转真的压了撤销（不是只有 _nav_back）",
        "_push_undo" in body and "跳转回" in body, "")
    body = fn_body(SRC, "_nav_back")
    chk("★ _nav_back 里也压了撤销", "_push_undo" in body, "")
    chk("返回按钮在词头（胶囊样式，不再是被吞掉的 12px 小字）",
        "nav:back" in SRC and "↩ 返回" in SRC)

    # ==================================================================
    say()
    say("=" * 74)
    say("7. ★ 性能护栏：新增的联网功能不许被扯进打字路径")
    say("=" * 74)
    # 用户上一轮刚投诉过「单词打得很慢」。本轮新增了两处联网
    # （反查 + 词条机翻），最大的风险就是打字时顺手发请求。
    # 打字路径 = _on_text_now（防抖后执行）→ 候选预览用 record=False。
    # 这里插桩计数，要求：**英语模式打字时零机翻请求**。
    NET = {"mt": 0, "tr": 0}
    _o_mmr3 = A._mymemory_raw
    _o_tr3 = A.translate_text

    def _c_mmr(*a, **k):
        NET["mt"] += 1
        return None, None

    def _c_tr(*a, **k):
        NET["tr"] += 1
        return None, None

    A._mymemory_raw = _c_mmr
    A.translate_text = _c_tr
    try:
        w.lang = "en"
        w.engine = w.dicts["en"]
        w._mt_cache.clear()
        w._mt_fetching.clear()
        NET.update(mt=0, tr=0)
        times = []
        for i in range(1, 6):
            t0 = time.perf_counter()
            w._on_text_now("water"[:i])
            times.append((time.perf_counter() - t0) * 1000)
        times.sort()
        med = times[len(times) // 2]
        say("      打字 5 次的耗时(ms): %s  中位 %.1f"
            % (["%.1f" % x for x in times], med))
        chk("★ 英语模式打字时不发机翻请求（零调用）", NET["mt"] == 0,
            "(%d 次)" % NET["mt"])
        chk("★ 英语模式打字时不走多语言翻译", NET["tr"] == 0,
            "(%d 次)" % NET["tr"])
        chk("★ 每键中位仍在 30ms 以内（上一轮修好的性能没有回退）",
            med < 30, "(中位 %.1f ms)" % med)

        # 正对照：插桩必须真的能计数
        A._mymemory_raw = lambda *a, **k: (NET.update(mt=NET["mt"] + 1), (None, None))[1]
        w._schedule_mt_zh("perf_ctl")
        chk("★ 正对照：主动发起时机翻确实被调用（插桩有效）",
            NET["mt"] >= 1, "(%d 次)" % NET["mt"])
    finally:
        A._mymemory_raw = _o_mmr3
        A.translate_text = _o_tr3

    # ==================================================================
    say()
    say("=" * 74)
    say("8. 真实联网抽查（连不上就 SKIP，不算失败）")
    say("=" * 74)
    try:
        r, s = A.translate_text("我爱你", "ja")
        if r:
            chk("★ 中文 → 日语 真实翻译可用（%s）" % s, True, "-> %r" % r[:40])
        else:
            skip("中文 → 日语 真实翻译可用", "网络不可用：%s" % s)
    except Exception as e:
        skip("中文 → 日语 真实翻译可用", repr(e))

    try:
        r, s = A._mymemory_raw("點解", "yue|zh-CN")
        if r:
            chk("★ 粤语 → 中文 真实翻译可用", True, "-> %r" % r)
        else:
            skip("粤语 → 中文 真实翻译可用", "网络不可用")
    except Exception as e:
        skip("粤语 → 中文 真实翻译可用", repr(e))

    try:
        r, s = A.translate_text("これは本です", "ja")
        if r:
            chk("★ 日语 → 中文 真实翻译可用", True, "-> %r" % r[:40])
        else:
            skip("日语 → 中文 真实翻译可用", "网络不可用")
    except Exception as e:
        skip("日语 → 中文 真实翻译可用", repr(e))

finally:
    # ---- 无论如何都要把真实配置和数据还原回去 ----
    A.CONFIG.clear()
    A.CONFIG.update(_CFG_BACKUP)
    A.CONFIG_PATH = _orig_cfg_path
    A.UserStore.__init__ = _orig_store_init

say()
say("=" * 74)
say("RESULT  pass=%d  fail=%d  skip=%d" % (P, F, S))
say("=" * 74)
try:
    with open(r"D:\Dictionary\build\_multilang_verify.txt", "w",
              encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
except Exception:
    pass
sys.stdout.flush()
sys.exit(1 if F else 0)
