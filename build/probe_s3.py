# -*- coding: utf-8 -*-
"""探测阶段三数据源：Wiktionary 定义 / 例句 + 免费翻译接口。"""
import io, json, urllib.request, urllib.parse

log = io.StringIO()
def say(s=""): log.write(str(s) + "\n")

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

def fetch(url, timeout=8):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()

# ---- 1. Wiktionary 定义 REST API ----
say("== Wiktionary 定义 API ==")
try:
    data = fetch("https://en.wiktionary.org/api/rest_v1/page/definition/water")
    obj = json.loads(data.decode("utf-8", "replace"))
    say("  状态: OK")
    # 结构: {word: {lang: [{partOfSpeech, definitions:[{definition, examples}]}]}}
    en = obj.get("en", [])
    say(f"  en 词性数: {len(en)}")
    for i, pos in enumerate(en[:3]):
        part = pos.get("partOfSpeech", "?")
        defs = pos.get("definitions", [])
        d0 = defs[0].get("definition", "") if defs else ""
        ex = defs[0].get("examples", []) if defs else []
        say(f"    [{part}] {d0[:80]}")
        if ex:
            say(f"        例句: {ex[0][:80]}")
except Exception as e:
    say(f"  失败: {repr(e)}")

# ---- 2. Wiktionary 例句（wikitext 里的例句更全）----
say("\n== Wiktionary wikitext（含例句）==")
try:
    p = urllib.parse.quote("water")
    data = fetch("https://en.wiktionary.org/w/api.php?action=parse&page=" + p +
                 "&prop=wikitext&format=json&section=1")
    obj = json.loads(data.decode("utf-8", "replace"))
    wt = obj["parse"]["wikitext"]["*"]
    say(f"  wikitext 长度: {len(wt)}")
    say(f"  片段: {wt[:200]!r}")
except Exception as e:
    say(f"  失败: {repr(e)}")

# ---- 3. 免费翻译接口（Google 非官方）----
say("\n== Google Translate 非官方接口 ==")
try:
    q = urllib.parse.quote("Hello, how are you?")
    data = fetch("https://translate.googleapis.com/translate_a/single"
                 "?client=gtx&sl=en&tl=zh-CN&dt=t&q=" + q)
    obj = json.loads(data.decode("utf-8", "replace"))
    seg = obj[0]
    txt = "".join(s[0] for s in seg if s[0])
    say(f"  译文: {txt}")
except Exception as e:
    say(f"  失败: {repr(e)}")

# ---- 4. 有道翻译（公开接口，无 key）----
say("\n== 有道网页翻译接口 ==")
try:
    q = urllib.parse.quote("Hello, how are you?")
    data = fetch("https://dict.youdao.com/jsonapi?q=" + q)
    obj = json.loads(data.decode("utf-8", "replace"))
    say(f"  返回 keys: {list(obj.keys())[:8]}")
    ec = obj.get("ec") or {}
    trans = (ec.get("word") or [{}])
    if trans:
        say(f"  ec.word[0].trs: {trans[0].get('trs', '')[:10] if isinstance(trans, list) else trans}")
except Exception as e:
    say(f"  失败: {repr(e)}")

open(r"D:\Dictionary\build\_probe_s3.txt", "w", encoding="utf-8").write(log.getvalue())
print("done")
