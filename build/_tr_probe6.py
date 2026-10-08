# -*- coding: utf-8 -*-
"""探测非英语（日/法/粤）在线通道能力（2026-09-18）。

要回答的问题：
  ① MyMemory 是否支持 ja / fr / yue 的双向整句翻译？耗时？
  ② 有道 suggest / web_trans / jsonapi 对**日语、法语词**能否给出中文释义？
  ③ 有道 jsonapi 对非英语词返回哪些段落（找可用的中文释义字段）？
不修改任何东西，只读网络。
"""
import json
import time
import urllib.parse
import urllib.request

UA = {"User-Agent": "Mozilla/5.0"}
MM = "https://api.mymemory.translated.net/get?q={q}&langpair={p}"
SUG = "https://dict.youdao.com/suggest?num=5&ver=3.0&doctype=json&q={q}"
API = "https://dict.youdao.com/jsonapi?q={q}&dicts=%7B%22count%22%3A99%7D"


def get(url, to=10):
    req = urllib.request.Request(url, headers=UA)
    t = time.time()
    with urllib.request.urlopen(req, timeout=to) as r:
        body = r.read()
    return body, time.time() - t


def has_cjk(s):
    return any("\u4e00" <= c <= "\u9fff" for c in (s or ""))


print("=" * 74)
print("① MyMemory 多语言双向")
print("=" * 74)
MM_CASES = [
    ("ja|zh-CN", "水"),
    ("zh-CN|ja", "水"),
    ("ja|zh-CN", "これは本です"),
    ("zh-CN|ja", "今天天气很好"),
    ("fr|zh-CN", "eau"),
    ("zh-CN|fr", "水"),
    ("fr|zh-CN", "Je vais à l'école"),
    ("zh-CN|fr", "我去学校"),
    ("yue|zh-CN", "食飯"),
    ("zh-CN|yue", "吃饭"),
    ("ja|en", "水"),
    ("en|ja", "water"),
    ("en|fr", "water"),
    ("fr|en", "eau"),
]
for pair, q in MM_CASES:
    url = MM.format(q=urllib.parse.quote(q), p=urllib.parse.quote(pair))
    try:
        body, dt = get(url)
        o = json.loads(body.decode("utf-8", "replace"))
        txt = (o.get("responseData") or {}).get("translatedText")
        print("  MM %-10s %-14s %5.2fs st=%s -> %r"
              % (pair, q, dt, o.get("responseStatus"), txt))
    except Exception as e:
        print("  MM %-10s %-14s ERR %r" % (pair, q, e))

print()
print("=" * 74)
print("② 有道 suggest 对日/法/粤词")
print("=" * 74)
for q in ["食べる", "水", "学校", "eau", "manger", "bonjour", "唔該", "食飯"]:
    try:
        body, dt = get(SUG.format(q=urllib.parse.quote(q)))
        o = json.loads(body.decode("utf-8", "replace"))
        es = ((o.get("data") or {}).get("entries")) or []
        shown = [(e.get("entry"), e.get("explain")) for e in es[:2]]
        print("  SUG %-8s %5.2fs n=%d -> %s" % (q, dt, len(es), shown))
    except Exception as e:
        print("  SUG %-8s ERR %r" % (q, e))

print()
print("=" * 74)
print("③ 有道 jsonapi 对非英语词返回的段落结构")
print("=" * 74)
for q in ["食べる", "eau"]:
    try:
        body, dt = get(API.format(q=urllib.parse.quote(q)))
        o = json.loads(body.decode("utf-8", "replace"))
        print("  API %-8s %5.2fs top-keys=%s" % (q, dt, sorted(o.keys())))
        for k in ("ec", "ce", "simple", "web_trans", "blng_sents_part",
                  "fanyi", "phrs", "relate_word", "ee", "collins"):
            v = o.get(k)
            if not v:
                continue
            s = json.dumps(v, ensure_ascii=False)
            print("    -- %-16s %s" % (k, s[:300]))
    except Exception as e:
        print("  API %-8s ERR %r" % (q, e))

print()
print("=" * 74)
print("④ 有道 web_trans 对非英语词（单条探测）")
print("=" * 74)
for q in ["食べる", "eau"]:
    try:
        body, dt = get("https://dict.youdao.com/jsonapi?q="
                       + urllib.parse.quote(q))
        o = json.loads(body.decode("utf-8", "replace"))
        wt = o.get("web_trans") or {}
        items = wt.get("web-translation") or []
        for x in items[:2]:
            trs = [(t.get("value") if isinstance(t, dict) else t)
                   for t in (x.get("trans") or [])]
            print("  WT %-8s key=%r -> %s" % (q, x.get("key"), trs[:3]))
    except Exception as e:
        print("  WT %-8s ERR %r" % (q, e))

print()
print("RESULT OK")
