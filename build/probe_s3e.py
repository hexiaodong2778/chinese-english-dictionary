# -*- coding: utf-8 -*-
"""看有道 fanyi 原始返回 + 有道 jsonapi 对句子的 web_trans。"""
import io, json, urllib.request, urllib.parse

log = io.StringIO()
def say(s=""): log.write(str(s) + "\n")
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
      "Referer": "https://fanyi.youdao.com/"}

def fetch(url, timeout=6):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()

say("== 有道 fanyi 原始返回 ==")
try:
    q = urllib.parse.quote("Hello, how are you today?")
    data = fetch("https://fanyi.youdao.com/translate?doctype=json&type=AUTO&i=" + q)
    say(f"  bytes={data[:300]!r}")
except Exception as e:
    say(f"  失败: {repr(e)}")

say("\n== 有道 jsonapi 句子 web_trans ==")
try:
    q = urllib.parse.quote("Hello, how are you today?")
    data = fetch("https://dict.youdao.com/jsonapi?q=" + q)
    obj = json.loads(data.decode("utf-8", "replace"))
    wt = obj.get("web_trans") or {}
    say(f"  web_trans: {json.dumps(wt, ensure_ascii=False)[:400]}")
    # 也看 blng_sents_part（双语例句）—— 可能含整句翻译
    blng = obj.get("blng_sents_part") or {}
    say(f"  blng_sents_part keys: {list(blng.keys())}")
    sents = blng.get("sentence-pair") or []
    say(f"  sentence-pair 数: {len(sents)}")
    for s in sents[:3]:
        say(f"    EN: {s.get('sentence-eng','')[:60]}")
        say(f"    CN: {s.get('sentence-translation','')[:60]}")
except Exception as e:
    say(f"  失败: {repr(e)}")

open(r"D:\Dictionary\build\_probe_s3e.txt", "w", encoding="utf-8").write(log.getvalue())
print("done")
