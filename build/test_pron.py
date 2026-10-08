# -*- coding: utf-8 -*-
"""发音：英美确实用两份不同的音源（回归）。

── 为什么重写（2026-09-17）──
原版测试的是 `Pronouncer._ipa_to_words()`，即「音标 → 近似拼写串」那段逻辑。
那段逻辑**已被有意删除**：它把音标替换成 "wotә" 这种假拼写再交给系统语音，
而系统里其实只有中文语音，结果是怪腔调的「拼读感」。
现行设计是**直接用真人在线录音**，不再自己拼读音标。

所以这个测试改成验证现行设计成立的必要条件：
  ① 英美两个按钮走的是两个不同的接口 type（1 / 2）
  ② 下载到的英美音频确实是两份不同的录音
  ③ 已彻底不存在「自己拼读音标」的代码路径
"""
import io
import os
import sys
import tempfile

sys.path.insert(0, r"D:\Dictionary\build")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import app as A

PASS, FAIL = [], []


def chk(name, cond, detail=""):
    (PASS if cond else FAIL).append(
        name + ("  " + str(detail) if detail else ""))


# ① 接口 type 映射：英美必须不同
tmp = tempfile.mkdtemp(prefix="cdc_pron_")
pr = A.Pronouncer(cache_dir=tmp)

hits = {}


class _Resp:
    def __init__(self, data):
        self._d = data

    def read(self):
        return self._d

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


_real_open = A._open_url


def _fake_open(req, timeout=None):
    url = req.full_url if hasattr(req, "full_url") else req
    hits.setdefault(len(hits), url)
    # 造两份内容不同的合法 mp3，模拟英美是不同录音
    tag = b"UK" if "type=1" in url else b"US"
    body = b"\xff\xfb\x64" + tag + b"\x00" * 3000
    return _Resp(body)


A._open_url = _fake_open
try:
    p_uk = pr._fetch_online("water", "uk")
    p_us = pr._fetch_online("water", "us")
finally:
    A._open_url = _real_open

chk("英式请求走 type=1",
    any("type=1" in u for u in hits.values()), list(hits.values()))
chk("美式请求走 type=2",
    any("type=2" in u for u in hits.values()), list(hits.values()))
chk("英美请求是不同的 URL",
    len({u.split("type=")[-1] for u in hits.values()}) == 2, list(hits.values()))
chk("英美落盘到不同缓存文件",
    bool(p_uk) and bool(p_us) and p_uk != p_us,
    "%s vs %s" % (os.path.basename(p_uk or ""), os.path.basename(p_us or "")))
if p_uk and p_us and os.path.exists(p_uk) and os.path.exists(p_us):
    chk("两份音频内容不同（确非同一份录音）",
        open(p_uk, "rb").read() != open(p_us, "rb").read())

# ② 「自己拼读音标」的路径必须彻底消失
chk("_ipa_to_words 已移除", not hasattr(A.Pronouncer, "_ipa_to_words"))
src = io.open(r"D:\Dictionary\build\app.py", encoding="utf-8").read()
chk("源码里没有 _ipa_to_words 定义", "def _ipa_to_words" not in src)

# ③ 四种模式都能落到某个真实音源（不返回 False）
for acc, lang, why in (("us", "en", "美式"),
                       ("uk", "en", "英式"),
                       ("edge", "en", "Edge 口音")):
    pr2 = A.Pronouncer(cache_dir=tempfile.mkdtemp(prefix="cdc_pron2_"))
    ok = pr2.speak("water", accent=acc, lang=lang)
    chk("%s发音返回成功" % why, ok, "来源=%s" % pr2._last_source)

# ④ 非英语也能出声（走本地语音）
pr3 = A.Pouncer if False else A.Pronouncer(cache_dir=tempfile.mkdtemp(prefix="cdc_pron3_"))
ok = pr3.speak("bonjour", accent="edge", lang="fr")
chk("法语路径可出声", ok, "来源=%s" % pr3._last_source)

# ⑤ 空文本必须安全失败，不能抛
chk("空文本安全返回 False", pr.speak("", "us") is False)

print("PASS=%d FAIL=%d" % (len(PASS), len(FAIL)))
for p in PASS:
    print("  PASS ", p)
for f in FAIL:
    print("  FAIL ", f)
