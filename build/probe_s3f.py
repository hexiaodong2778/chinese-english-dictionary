# -*- coding: utf-8 -*-
"""测试有道网页版翻译 sign（老版 key）。"""
import io, json, hashlib, time, random, urllib.request, urllib.parse

log = io.StringIO()
def say(s=""): log.write(str(s) + "\n")

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

def try_sign(text, key):
    lts = str(int(time.time() * 1000))
    salt = lts + str(random.randrange(10))
    sign = hashlib.md5(("fanyideskweb" + text + salt + key).encode("utf-8")).hexdigest()
    data = {
        "i": text, "from": "AUTO", "to": "AUTO", "smartresult": "dict",
        "client": "fanyideskweb", "salt": salt, "sign": sign, "lts": lts,
        "doctype": "json", "version": "2.1", "keyfrom": "fanyi.web",
        "action": "FY_BY_REALTlME",
    }
    body = urllib.parse.urlencode(data).encode()
    req = urllib.request.Request(
        "https://fanyi.youdao.com/translate?smartresult=dict&smartresult=rule",
        data=body, headers={"User-Agent": UA, "Referer": "https://fanyi.youdao.com/"})
    with urllib.request.urlopen(req, timeout=6) as r:
        return r.read()

text = "Hello, how are you today?"

for name, key in [
    ("老版key1 Tbh5E8", "Tbh5E8=q6U3EXe+&L[4c@"),
    ("老版key2 Ygy_4c", "Ygy_4c=r#e#4EX^NUGUc5"),
]:
    say(f"== {name} ==")
    try:
        raw = try_sign(text, key)
        txt = raw.decode("utf-8", "replace")
        if txt.strip().startswith("{"):
            o = json.loads(txt)
            say(f"  JSON! errorCode={o.get('errorCode')} result={json.dumps(o.get('translateResult'), ensure_ascii=False)[:200]}")
        else:
            say(f"  非JSON: {txt[:80]!r}")
    except Exception as e:
        say(f"  失败: {repr(e)}")

open(r"D:\Dictionary\build\_probe_s3f.txt", "w", encoding="utf-8").write(log.getvalue())
print("done")
