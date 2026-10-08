# -*- coding: utf-8 -*-
"""联网词典增强的「畸形返回」容错测试。

起因：test_gui_new 暴露真实崩溃 —— exam.i.f 在有道接口里
      有时是 {"l":[...]}，有时是字符串，硬 .get 会抛 AttributeError，
      导致整条词条联网增强失败（外层 except 只包住网络请求，没包解析）。
本测试用伪造响应直接喂给解析逻辑，覆盖各种畸形形状。
"""
import io, os, sys, json
sys.path.insert(0, r"D:\Dictionary\build")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

log = io.StringIO()
def say(s=""): log.write(str(s) + "\n")
ok = fail = 0
def chk(c, label, extra=""):
    global ok, fail
    if c: ok += 1; say(f"  PASS  {label}")
    else: fail += 1; say(f"  FAIL  {label}  {extra}")

import app as A

say("== 0. 辅助函数 _as_list / _dig ==")
chk(A._as_list(None) == [], "None → []")
chk(A._as_list("x") == ["x"], "str → [str]")
chk(A._as_list({"k": 1}) == [{"k": 1}], "dict → [dict]")
chk(A._as_list([1, 2]) == [1, 2], "list 原样")
chk(A._dig({"a": {"b": 1}}, "a", "b") == 1, "_dig 正常取")
chk(A._dig({"a": "str"}, "a", "b") is None, "_dig 中途遇标量返回 None")
chk(A._dig(None, "a") is None, "_dig 起点 None 返回 None")

say("\n== 1. 复现原崩溃：exam.i.f 为字符串 ==")
fake = {
    "ee": {"word": {"trs": [{"pos": "n.", "tr": [{
        "l": {"i": ["a clear liquid"]},
        "exam": {"i": {"f": "He drank the water."}},
    }]}]}},
}
_real_fetch = None
import urllib.request
class _Resp:
    def __init__(self, payload): self._p = payload
    def read(self): return json.dumps(self._p).encode("utf-8")
    def __enter__(self): return self
    def __exit__(self, *a): return False
_orig_open_url = A._open_url
A._open_url = lambda req, timeout: _Resp(fake)
try:
    d = A.fetch_online_def("water")
finally:
    A._open_url = _orig_open_url
say(f"  english = {d.get('english')}")
say(f"  examples = {d.get('examples')}")
chk(d.get("english") == [("n.", "a clear liquid")], "字符串型 f 不再崩溃且释义正确")
chk(isinstance(d.get("examples"), list), "examples 仍是列表")

say("\n== 2. f 为 list / l 为 dict / i 为 str 混合 ==")
def _ee(pos, l_val, exam=None):
    """构造 {"ee":{"word":{"trs":[{"pos":pos,"tr":[{l,exam}]}]}}}"""
    tr = {"l": l_val}
    if exam is not None:
        tr["exam"] = exam
    return {"ee": {"word": {"trs": [{"pos": pos, "tr": [tr]}]}}}

cases = [
    ("f=list",
     _ee("v.", {"i": ["to flow"]},
         {"i": {"f": [{"l": [{"i": ["I water it."]}]}]}}),
     "I water it."),
    ("f=dict&l=dict&i=str",
     _ee("v.", {"i": "to flow"}, {"i": {"f": {"l": {"i": "One more."}}}}),
     "One more."),
    ("f缺失", _ee("v.", {"i": ["to flow"]}), None),
    ("trs为dict", {"ee": {"word": {"trs": {"pos": "x", "tr": []}}}}, None),
    ("ee缺失", {}, None),
    ("ee为字符串", {"ee": "oops"}, None),
    ("l为字符串", _ee("v.", "plain string"), None),
]
for name, payload, want_ex in cases:
    A._open_url = lambda req, timeout, _p=payload: _Resp(_p)
    try:
        d = A.fetch_online_def("probe")
    except Exception as e:
        chk(False, f"{name} 不抛异常", f"{type(e).__name__}: {e}")
        continue
    finally:
        A._open_url = _orig_open_url
    if want_ex:
        chk(want_ex in [str(x) for x in d.get("examples")] or
            any(want_ex in str(x) for x in d.get("examples")),
            f"{name} 例句已解析", str(d.get("examples")))
    else:
        chk(isinstance(d, dict), f"{name} 安全返回 dict", str(d))

say("\n== 3. collins / syno / blng 畸形形状 ==")
def _col(tran_entry):
    return {"collins": {"collins_entries": [
        {"entries": {"entry": [{"tran_entry": [tran_entry]}]}}]}}

def _syn(synos):
    return {"syno": {"synos": synos}}

more = [
    ("collins条目为str", {"collins": {"collins_entries": ["bad"]}}),
    ("collins_entries为dict", {"collins": {"collins_entries": {"a": 1}}}),
    ("exam_sents为str", _col({"tran": "水", "exam_sents": "oops"})),
    ("synos为str", {"syno": {"synos": "oops"}}),
    ("ws内元素为str", _syn([{"syno": {"pos": "n.", "ws": ["bad"]}}])),
    ("ws有空格键", _syn([{"syno": {"pos": "n.", "ws": [{"w": "aqua"}]}}])),
    ("blng为str", {"blng_sents_part": "oops"}),
    ("sentence-pair为str", {"blng_sents_part": {"sentence-pair": "oops"}}),
    ("pair内为str", {"blng_sents_part": {"sentence-pair": ["oops"]}}),
]
for name, payload in more:
    A._open_url = lambda req, timeout, _p=payload: _Resp(_p)
    try:
        d = A.fetch_online_def("probe")
        chk(isinstance(d, dict), f"{name} 不崩溃", str(d))
    except Exception as e:
        chk(False, f"{name} 不崩溃", f"{type(e).__name__}: {e}")
    finally:
        A._open_url = _orig_open_url

say("\n== 4. syno 正常路径仍能取到 ==")
A._open_url = lambda req, timeout: _Resp(_syn(
    [{"syno": {"pos": "n.", "ws": [{"w": "aqua"}, {"w": "H2O"}]}}]))
try:
    d = A.fetch_online_def("water")
finally:
    A._open_url = _orig_open_url
chk(d.get("synos") == [("n.", ["aqua", "H2O"])], "同义词正常解析", str(d.get("synos")))

say("\n== 5. collins 正常路径（含例句）==")
A._open_url = lambda req, timeout: _Resp(_col({
    "pos_entry": {"pos": "N-UNCOUNT"},
    "tran": "<b>Water</b> is a liquid.",
    "exam_sents": {"sent": [{"eng_sent": "Drink <i>water</i>.",
                             "chn_sent": "喝水。"}]}}))
try:
    d = A.fetch_online_def("water")
finally:
    A._open_url = _orig_open_url
say(f"  collins = {d.get('collins')}")
chk(d.get("collins") == [("N-UNCOUNT", "Water is a liquid.")],
    "柯林斯正文已去 HTML 标签", str(d.get("collins")))
chk(("Drink water.", "喝水。") in d.get("examples", []),
    "柯林斯例句已解析", str(d.get("examples")))

say("\n== 6. 真实接口回归（有网时）==")
d = A.fetch_online_def("water")
say(f"  keys = {list(d.keys())}")
chk(bool(d.get("english")), "真实请求仍有英英释义", str(d.get("english"))[:80])
chk(bool(d.get("collins")), "真实请求仍有柯林斯", str(d.get("collins"))[:80])

say(f"\nRESULT  ok={ok} fail={fail}")
open(r"D:\Dictionary\build\_test_robust.txt", "w", encoding="utf-8").write(log.getvalue())
print("done")
