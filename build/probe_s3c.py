# -*- coding: utf-8 -*-
"""探测有道 jsonapi 的 ee/collins/webster 字段 + 有道翻译 GET 接口。"""
import io, json, urllib.request, urllib.parse

log = io.StringIO()
def say(s=""): log.write(str(s) + "\n")
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

def fetch(url, timeout=6):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()

say("== 有道 jsonapi: water 的 ee / collins / webster ==")
data = fetch("https://dict.youdao.com/jsonapi?q=" + urllib.parse.quote("water"))
obj = json.loads(data.decode("utf-8", "replace"))

ee = obj.get("ee") or {}
say(f"ee keys: {list(ee.keys())}")
say(f"ee.word: {json.dumps(ee.get('word'), ensure_ascii=False)[:500]}")

collins = obj.get("collins") or {}
say(f"\ncollins keys: {list(collins.keys())}")
say(f"collins: {json.dumps(collins, ensure_ascii=False)[:500]}")

webster = obj.get("webster") or {}
say(f"\nwebster keys: {list(webster.keys())}")
say(f"webster: {json.dumps(webster, ensure_ascii=False)[:500]}")

oxford = obj.get("oxford") or {}
say(f"\noxford keys: {list(oxford.keys())}")
say(f"oxford: {json.dumps(oxford, ensure_ascii=False)[:400]}")

syno = obj.get("syno") or {}
say(f"\nsyno keys: {list(syno.keys())}")
say(f"syno: {json.dumps(syno, ensure_ascii=False)[:300]}")

say("\n== 有道翻译 GET ==")
try:
    q = urllib.parse.quote("Hello, how are you today?")
    data = fetch("https://fanyi.youdao.com/translate?doctype=json&type=AUTO&i=" + q)
    o = json.loads(data.decode("utf-8", "replace"))
    say(f"  keys: {list(o.keys())}")
    say(f"  errorCode: {o.get('errorCode')}")
    say(f"  translateResult: {json.dumps(o.get('translateResult'), ensure_ascii=False)}")
    say(f"  type: {o.get('type')}  l: {o.get('l')}")
except Exception as e:
    say(f"  失败: {repr(e)}")

open(r"D:\Dictionary\build\_probe_s3c.txt", "w", encoding="utf-8").write(log.getvalue())
print("done")
