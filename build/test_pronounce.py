# -*- coding: utf-8 -*-
"""验证新发音引擎：
① 在线下载 + 缓存命中
② 英音/美音确实是两份不同录音
③ 回退路径（断网时不会静默失败）
"""
import os
import sys
import tempfile

sys.path.insert(0, r"D:\Dictionary\build")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

out = []
tmpdir = os.path.join(tempfile.gettempdir(), "cdc_audio_test")
if os.path.isdir(tmpdir):
    for f in os.listdir(tmpdir):
        try:
            os.remove(os.path.join(tmpdir, f))
        except Exception:
            pass
os.makedirs(tmpdir, exist_ok=True)

from PySide6.QtWidgets import QApplication
app = QApplication.instance() or QApplication([])

from app import Pronouncer

p = Pronouncer(cache_dir=tmpdir)
out.append(f"缓存目录: {p._cache_dir}")

out.append("")
out.append("① 在线下载测试")
for w, acc in [("water", "us"), ("water", "uk"),
               ("tomato", "us"), ("tomato", "uk")]:
    path = p._fetch_online(w, acc)
    if path:
        sz = os.path.getsize(path)
        out.append(f"  ✓ {w:<10} {acc}  {sz:>7,} B  {os.path.basename(path)}")
    else:
        out.append(f"  ✗ {w:<10} {acc}  下载失败")

out.append("")
out.append("② 缓存命中验证（第二次不应联网）")
import time
t0 = time.time()
p2 = p._fetch_online("water", "us")
dt = (time.time() - t0) * 1000
out.append(f"  第二次取 water/us: {dt:.1f} ms  path={bool(p2)}")
out.append(f"  {'✓ 明显是缓存命中（<50ms）' if dt < 50 else '⚠ 可能又联网了'}")

out.append("")
out.append("③ 英音 vs 美音 是否不同")
import hashlib
for w in ["tomato", "record", "schedule"]:
    a = p._fetch_online(w, "uk")
    b = p._fetch_online(w, "us")
    if a and b:
        ha = hashlib.sha256(open(a, "rb").read()).hexdigest()[:10]
        hb = hashlib.sha256(open(b, "rb").read()).hexdigest()[:10]
        out.append(f"  {w:<10} 英={ha} 美={hb}  "
                   f"{'✓ 不同' if ha != hb else '✗ 相同'}")

out.append("")
out.append("④ speak() 端到端（含 QMediaPlayer 路径）")
for acc in ("us", "uk", "global"):
    ok = p.speak("water", accent=acc, lang="en")
    out.append(f"  accent={acc:<7} ok={ok}  来源={p._last_source or '(无)'}")

out.append("")
out.append("⑤ 离线回退模拟（把接口指向不可达地址）")
p.ONLINE_TPL = "https://127.0.0.1:9/nope?audio={w}&type={t}"
p.ONLINE_TIMEOUT = 2
for w in ["newword1", "newword2"]:
    ok = p.speak(w, accent="us", lang="en")
    out.append(f"  {w:<10} ok={ok}  来源={p._last_source or '(无)'}")

out.append("")
out.append("⑥ 非英语语种路径")
for lang, w in [("ja", "こんにちは"), ("fr", "bonjour")]:
    ok = p.speak(w, accent="global", lang=lang)
    out.append(f"  lang={lang} {w:<12} ok={ok}  来源={p._last_source or '(无)'}")

out.append("")
out.append(f"本地可用语音: {p.available_voices()}")

open(r"D:\Dictionary\build\_speak_test.txt", "w", encoding="utf-8").write(
    "\n".join(out))
print("ok")
