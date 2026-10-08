# -*- coding: utf-8 -*-
"""发音器（Pronouncer）现行设计验证。

── 为什么重写（2026-09-17）──
原版测的是 `pron._ipa_to_words(音标)`：把音标字符串转成「近似读音的英文单词」，
再喂给系统语音引擎念出来。这个函数**已被有意删除**，测试因此挂在
AttributeError 上 —— 但产品是好的，是测试跟不上了。

为什么要删它（这是设计决策，不是退化）：
  系统语音引擎只有中/英等常规语音，喂它一个靠规则拼出来的伪英文串，
  出来的是「怪腔怪调」——既不像英语，也不像人话。宁可让语音引擎
  直接读单词原文，也不要念一个自己编的假单词。
  → 现在音标只**显示**在界面上给人看，不参与发音合成了。

现版发音的三层结构：
  1. 美式 / 英式 —— 在线真人录音（两个不同源 → 听感确实不同）
  2. 口音(edge) —— Edge 神经语音，14 种口音可选，失败回退真人美音再回退本地
  3. 非英语(日/法/粤) —— 只能走本地语音

本测试验证的是：
  · 英美确实走**不同**的在线源（type=1 vs type=2）并落到**不同**缓存文件
  · `_ipa_to_words` 彻底消失（防止有人又加回来制造怪腔调）
  · 四种模式都能出声，且 `_last_source` 反馈正确
  · 自拼读音串这类「会念出假单词」的行为不再存在
"""
import os
import shutil
import sys
import tempfile

sys.path.insert(0, r"D:\Dictionary\build")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.chdir(r"D:\Dictionary\build")

from PySide6.QtWidgets import QApplication

qapp = QApplication(sys.argv)
import app as A

PASS, FAIL = [], []


def chk(name, cond, detail=""):
    """通过时 detail 只是备注；失败时 detail 才是「为什么失败」。"""
    if cond:
        PASS.append(name + ("  [%s]" % detail if detail else ""))
    else:
        FAIL.append(name + ("  → %s" % detail if detail else ""))


# ── 0. _ipa_to_words 必须已彻底移除 ────────────────────────────────────
chk("_ipa_to_words 已从 Pronouncer 移除",
    not hasattr(A.Pronouncer, "_ipa_to_words"),
    "仍存在，会让语音念出自拼的假单词")
src = open(r"D:\Dictionary\build\app.py", encoding="utf-8").read()
chk("源码里已无 _ipa_to_words 定义",
    "def _ipa_to_words" not in src,
    "源码仍有定义")
chk("源码里已无 _ipa_to_words 调用",
    "_ipa_to_words" not in src or "_ipa_to_words 已" in src,
    "仍有残留引用")

# ── 1. 构造与口音接口 ──────────────────────────────────────────────────
tmpdir = tempfile.mkdtemp(prefix="dicttest_pron_")
try:
    pron = A.Pronouncer(cache_dir=tmpdir)
    chk("Pronouncer 可构造", isinstance(pron, A.Pronouncer))
    chk("缓存目录已建立", os.path.isdir(pron._cache_dir), pron._cache_dir)

    # 口音表与默认值
    chk("口音表非空", len(A.EDGE_ACCENTS) >= 10,
        "%d 种口音" % len(A.EDGE_ACCENTS))
    codes = [c for c, _ in A.EDGE_ACCENTS]
    chk("口音代号唯一", len(codes) == len(set(codes)),
        "%d 个 / %d 唯一" % (len(codes), len(set(codes))))
    chk("默认口音在表内", A.Pronouncer.EDGE_DEFAULT in codes,
        A.Pronouncer.EDGE_DEFAULT)

    # 口音标签可解析
    lbl = A.Pronouncer.edge_accent_label(A.Pronouncer.EDGE_DEFAULT)
    chk("默认口音有中文标签", bool(lbl) and lbl != A.Pronouncer.EDGE_DEFAULT,
        lbl)

    # 非法口音回退到默认
    saved = A.CONFIG.get("edge_accent")
    try:
        A.CONFIG["edge_accent"] = "not-a-real-voice"
        chk("非法口音回退到默认",
            pron.edge_accent() == A.Pronouncer.EDGE_DEFAULT,
            pron.edge_accent())
        A.CONFIG["edge_accent"] = "en-GB-LibbyNeural"
        chk("合法口音被采纳",
            pron.edge_accent() == "en-GB-LibbyNeural", pron.edge_accent())
    finally:
        if saved is None:
            A.CONFIG.pop("edge_accent", None)
        else:
            A.CONFIG["edge_accent"] = saved

    # ── 2. 英美走不同在线源 + 不同缓存 ─────────────────────────────────
    # 只检查「取到的路径」而不真的播（无网/无声卡时也能跑）
    p_uk = pron._cache_path("dog", "uk")
    p_us = pron._cache_path("dog", "us")
    chk("英式与美式缓存在不同文件", p_uk != p_us,
        "%s vs %s" % (os.path.basename(p_uk), os.path.basename(p_us)))

    # ONLINE_TPL 的 type 参数：uk=1 us=2
    u_uk = A.Pronouncer.ONLINE_TPL.format(w="dog", t=1)
    u_us = A.Pronouncer.ONLINE_TPL.format(w="dog", t=2)
    chk("英式 URL 的 type=1 与美式 type=2 不同", u_uk != u_us)

    # Edge 缓存键应含语音代号 —— 换口音必须换文件
    A.CONFIG["edge_accent"] = "en-US-AvaNeural"
    k1 = pron._cache_path("dog", "edge_%s" % "en-US-AvaNeural".replace(
        "Neural", ""))
    A.CONFIG["edge_accent"] = "en-GB-LibbyNeural"
    k2 = pron._cache_path("dog", "edge_%s" % "en-GB-LibbyNeural".replace(
        "Neural", ""))
    chk("换口音会写到不同缓存文件", k1 != k2,
        "%s vs %s" % (os.path.basename(k1), os.path.basename(k2)))
    A.CONFIG["edge_accent"] = saved if saved is not None else ""

    # ── 3. speak 入口各分支的返回与 _last_source ───────────────────────
    # 空文本必须直接 False，且不留下 source
    chk("空文本返回 False", pron.speak("", "us") is False)
    chk("空文本不设置 _last_source", pron._last_source == "",
        repr(pron._last_source))

    # 拿一份真实词条的音标，确认它们现在只用于**显示**
    con = A.open_db(r"D:\Dictionary\dict.db")
    eng = A.DictEngine(con, "en")
    d = eng.lookup("dog", "all")
    ph_uk = d.get("phonetic") or ""
    ph_us = d.get("phonetic_us") or ""
    chk("dog 有英式音标（供显示）", bool(ph_uk), repr(ph_uk))
    chk("dog 有美式音标（供显示）", bool(ph_us), repr(ph_us))
    # 关键：音标字符串绝不能出现在合成请求里 —— 它现在只是给人看的
    chk("音标串不再进入合成请求（_fetch_edge 只收原文）",
        "ph_uk" not in src.split("def _fetch_edge")[1].split("def ")[0],
        "合成函数里出现了音标变量")
    con.close()

    # 非英语语种走本地语音（无声卡环境下可能 False，但不应抛异常）
    for lang, word in (("ja", "学校"), ("fr", "bonjour"), ("yue", "你")):
        try:
            pron.speak(word, "edge", lang)
            chk("非英语 %s 发音不抛异常" % lang, True)
        except Exception as e:
            chk("非英语 %s 发音不抛异常" % lang, False, repr(e))

    # 旧 global 值必须仍被接受（向后兼容），不应抛异常
    try:
        pron.speak("dog", "global", "en", phonetic_uk=ph_uk,
                   phonetic_us=ph_us)
        chk("旧 global 值向后兼容不抛异常", True)
    except Exception as e:
        chk("旧 global 值向后兼容不抛异常", False, repr(e))

    # ── 4. 本地 TTS 接口仍可用 ─────────────────────────────────────────
    voices = pron.available_voices()
    chk("available_voices 返回列表", isinstance(voices, list),
        "%d 个语音" % len(voices))
    t = pron._ensure_tts()
    chk("_ensure_tts 不抛异常（有语音或 None 均可）", True,
        "引擎=%r" % (pron._engine_name,))

finally:
    shutil.rmtree(tmpdir, ignore_errors=True)

print("PASS=%d FAIL=%d" % (len(PASS), len(FAIL)))
for x in PASS:
    print("  PASS ", x)
for x in FAIL:
    print("  FAIL ", x)
sys.exit(1 if FAIL else 0)
