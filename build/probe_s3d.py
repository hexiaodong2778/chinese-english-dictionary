# -*- coding: utf-8 -*-
"""确定可用翻译接口。"""
import io, json, urllib.request, urllib.parse

log = io.StringIO()
def say(s=""): log.write(str(s) + "\n")
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
      "Referer": "https://fanyi.youdao.com/"}

def fetch(url, timeout=6):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()

say("== 有道 fanyi + Referer ==")
try:
    q = urllib.parse.quote("Hello, how are you today?")
    data = fetch("https://fanyi.youdao.com/translate?doctype=json&type=AUTO&i=" + q)
    o = json.loads(data.decode("utf-8", "replace"))
    say(f"  errorCode={o.get('errorCode')} type={o.get('type')}")
    say(f"  译文: {json.dumps(o.get('translateResult'), ensure_ascii=False)}")
except Exception as e:
    say(f"  失败: {repr(e)}")

say("\n== Bing 翻译（cn.bing.com/translator）==")
try:
    q = urllib.parse.quote("Hello, how are you today?")
    data = fetch("https://cn.bing.com/ttranslatev3?from=en&to=zh-Hans&text=" + q)
    say(f"  返回: {data[:200]!r}")
except Exception as e:
    say(f"  失败: {repr(e)}")

open(r"D:\Dictionary\build\_probe_s3d.txt", "w", encoding="utf-8").write(log.getvalue())
print("done")
