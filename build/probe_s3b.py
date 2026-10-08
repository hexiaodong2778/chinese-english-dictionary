# -*- coding: utf-8 -*-
"""探测阶段三数据源（二）：有道词典释义结构 + 有道翻译 + Wiktionary 重试。"""
import io, json, urllib.request, urllib.parse

log = io.StringIO()
def say(s=""): log.write(str(s) + "\n")
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

def fetch(url, timeout=6):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()

# ---- 1. 有道词典 jsonapi（单词 water）----
say("== 有道词典 jsonapi: water ==")
try:
    data = fetch("https://dict.youdao.com/jsonapi?q=" + urllib.parse.quote("water"))
    obj = json.loads(data.decode("utf-8", "replace"))
    say(f"  keys: {list(obj.keys())}")
    ec = obj.get("ec") or {}
    say(f"  ec keys: {list(ec.keys())}")
    word = (ec.get("word") or [{}])[0] if ec.get("word") else {}
    say(f"  ec.word[0] keys: {list(word.keys())}")
    trs = word.get("trs") or []
    if trs:
        tr0 = trs[0]
        say(f"  trs[0]: {json.dumps(tr0, ensure_ascii=False)[:300]}")
    # 双语例句
    blng = obj.get("blng_sents_part") or {}
    sents = blng.get("sentence-pair") or []
    say(f"  双语例句数: {len(sents)}")
    for s in sents[:3]:
        se = s.get("sentence-eng", "")
        sc = s.get("sentence-translation", "")
        say(f"    EN: {se[:60]}")
        say(f"    CN: {sc[:60]}")
except Exception as e:
    say(f"  失败: {repr(e)}")

# ---- 2. 有道翻译 fanyi（句子）----
say("\n== 有道翻译 fanyi 接口 ==")
try:
    body = urllib.parse.urlencode({
        "doctype": "json", "type": "AUTO",
        "i": "Hello, how are you today?",
    }).encode()
    req = urllib.request.Request("https://fanyi.youdao.com/translate",
                                 data=body, headers=UA)
    with urllib.request.urlopen(req, timeout=6) as r:
        obj = json.loads(r.read().decode("utf-8", "replace"))
    say(f"  keys: {list(obj.keys())}")
    say(f"  translateResult: {obj.get('translateResult')}")
except Exception as e:
    say(f"  失败: {repr(e)}")

# ---- 3. Wiktionary 重试（短超时）----
say("\n== Wiktionary 重试 ==")
try:
    data = fetch("https://en.wiktionary.org/api/rest_v1/page/definition/water", 4)
    obj = json.loads(data.decode("utf-8", "replace"))
    en = obj.get("en", [])
    say(f"  OK, en 词性数 {len(en)}")
except Exception as e:
    say(f"  失败: {repr(e)}")

# ---- 4. 备用：海词 dict.cn 或 Bing 词典 ----
say("\n== 必应词典（bing.com）==")
try:
    data = fetch("https://cn.bing.com/dict/search?q=" + urllib.parse.quote("water"), 5)
    txt = data.decode("utf-8", "replace")
    say(f"  页面长度: {len(txt)}")
    say(f"  含'释义': {'释义' in txt or 'def' in txt.lower()}")
except Exception as e:
    say(f"  失败: {repr(e)}")

open(r"D:\Dictionary\build\_probe_s3b.txt", "w", encoding="utf-8").write(log.getvalue())
print("done")
