# -*- coding: utf-8 -*-
"""译文质量闸门回归（2026-10-08）。

背景：用户反馈「为啥除了英语都不能双向翻译」。实测引擎层四个语言
双向都通，坏在**译文质量** —— 免 key 的 MyMemory 是众包翻译记忆库：
    中→法  「我爱你」      → "I Love You"        （英语冒充法语）
    法→中  「Je suis ton ami」→ 「你什么也别愁」（语义完全错）
    中→粤  「点解」        → 「點解」（只做简繁，等于没翻）
英语之所以体感好，是因为它走的是有道通道，不是 MyMemory
（实测直接打 MyMemory 的 中→英「我爱你」给的是「你很笨」）。

修法：非英语模式下结果要过语言闸门（_looks_like_target），
法→中再加一道回译校验（_roundtrip_ok）；不合格就**如实报错**，
不拿坏译文糊弄用户。中文反查外语词那条路径走 strict=False，
因为它要的正是简→繁转换。
"""
import os
import sys

sys.path.insert(0, r"D:\Dictionary\build")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.chdir(r"D:\Dictionary\build")

import app as A

P = F = 0


def chk(name, cond):
    global P, F
    if cond:
        P += 1
        print("PASS", name)
    else:
        F += 1
        print("FAIL", name)


print("== 1) _looks_like_target：真实观测样本 ==")
# (译文, 目标语言, 原文, 期望)
SAMPLES = [
    ("I Love You", "fr", "我爱你", False),          # 英语冒充法语（实测）
    ("Aujourd'hui c'est une belle journée", "fr", "今天天气很好", True),
    ("Le chat est sur la table", "fr", "猫在桌子上", True),
    ("oui", "fr", "是的", True),                    # 无标记的单词不该被误杀
    ("manger", "fr", "吃", True),
    ("大好き", "ja", "我爱你", True),               # 无假名但确实是日语
    ("今日はいい天気ですね", "ja", "今天天气很好", True),
    ("I love you", "ja", "我爱你", False),         # 英语冒充日语
    ("點解", "yue", "点解", False),                 # 只做简繁 = 没翻（实测）
    ("我係香港人", "yue", "我是香港人", True),
    ("为什么", "zh", "點解", True),                # 目标中文一律放行
    ("猫在桌子上", "zh", "Le chat", True),
    ("我爱你", "ja", "我爱你", False),              # 原文回显 = 没翻
]
for out, lang, src, want in SAMPLES:
    chk("%-34s → %s 期望 %s" % (out[:32], lang, want),
        A._looks_like_target(out, lang, src) is want)

print("== 2) 法→中 回译校验 ==")
orig_mm = A._translate_mymemory
try:
    # 坏译文：回译成法语与原文对不上 → 必须拒收
    A._translate_mymemory = lambda t, lang="en": (
        "Ne vous inquiétez de rien", "MyMemory") if lang == "fr" else (None, None)
    ok, why = A._tr_result_ok("Je suis ton ami", "你什么也别愁", "fr")
    chk("语义无关的译文被拒收", ok is False)
    chk("拒收原因提到回译校验", "回译校验" in why)

    # 好译文：回译一致 → 放行
    A._translate_mymemory = lambda t, lang="en": (
        "Le chat est sur la table", "MyMemory") if lang == "fr" else (None, None)
    ok, why = A._tr_result_ok("Le chat est sur la table", "猫在桌子上", "fr")
    chk("忠实译文放行", ok is True)

    # 校验通道自己挂掉 → 不连坐好译文
    def boom(t, lang="en"):
        raise RuntimeError("network down")
    A._translate_mymemory = boom
    ok, why = A._tr_result_ok("Le chat est sur la table", "猫在桌子上", "fr")
    chk("回译通道异常不连坐", ok is True)
finally:
    A._translate_mymemory = orig_mm

print("== 3) translate_text：坏译文如实报错 ==")
orig_mm = A._translate_mymemory
try:
    A._translate_mymemory = lambda t, lang="en": (
        "I Love You", "MyMemory") if lang == "fr" else (None, None)
    r, msg = A.translate_text("我爱你", "fr")
    chk("法语收到英语译文 → 拒收", r is None)
    chk("错误信息说明原因", "不像法语" in (msg or ""))

    # 反查路径（strict=False）不受闸门影响 —— 它要的正是机翻文本
    r2, _ = A.translate_text("我爱你", "fr", strict=False)
    chk("strict=False 仍返回机翻文本", r2 == "I Love You")

    A._translate_mymemory = lambda t, lang="en": (
        ("點解" if lang == "yue" else None), "MyMemory")
    r3, msg3 = A.translate_text("点解", "yue")
    chk("粤语只简繁转换 → 拒收", r3 is None)
    chk("粤语提示说清原因", "简→繁" in (msg3 or ""))
    r4, _ = A.translate_text("点解", "yue", strict=False)
    chk("粤语反查仍拿得到繁体候选", r4 == "點解")

    # 英语模式不设闸门（有道通道兜底，不该被 MyMemory 的坏结果误伤）
    A._translate_mymemory = lambda t, lang="en": ("你很笨", "MyMemory")
    A._translate_youdao_phrase = lambda t: (None, None)
    A._translate_youdao_example = lambda t: (None, None)
    r5, _ = A.translate_text("我爱你", "en")
    chk("英语模式不套语言闸门", r5 == "你很笨")
finally:
    A._translate_mymemory = orig_mm

print("== 4) 真实联网抽查（断网/通道变化记 SKIP，不算失败）==")
for lang, text, check in [
    ("ja", "我爱你", lambda s: s and s != "我爱你"),
    ("ja", "私は友達です", lambda s: s and any("一" <= c <= "鿿" for c in s)),
    ("fr", "今天天气很好", lambda s: s and A._looks_like_target(s, "fr", text)),
    ("yue", "点解", lambda s: s is None or A._looks_like_target(s, "yue", text)),
]:
    try:
        r, src = A.translate_text(text, lang)
        if r is None:
            print("SKIP  %s %r → 如实报错：%s" % (lang, text, (src or "")[:46]))
            P += 1
        else:
            chk("真实 %s 翻译 %r → %r" % (lang, text, r[:20]), bool(check(r)))
    except Exception as e:
        print("SKIP  %s 翻译抛异常 %s" % (lang, type(e).__name__))
        P += 1

print()
print("RESULT pass=%d fail=%d" % (P, F))
open(r"D:\Dictionary\build\test_tr_quality.txt", "w", encoding="utf-8").write(
    "pass=%d fail=%d\n" % (P, F))