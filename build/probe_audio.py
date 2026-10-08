# -*- coding: utf-8 -*-
"""关键验证：有道的英音(type=1) 与美音(type=2) 是不是真的不同录音。
下载两个文件比对哈希 + 大小 + 音频参数。
"""
import hashlib
import urllib.request

out = []
HDR = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}


def grab(word, typ):
    url = f"https://dict.youdao.com/dictvoice?audio={word}&type={typ}"
    req = urllib.request.Request(url, headers=HDR)
    with urllib.request.urlopen(req, timeout=15) as r:
        return r.read()


for w in ["water", "tomato", "schedule", "either", "bath", "record"]:
    try:
        a = grab(w, 1)   # 英
        b = grab(w, 2)   # 美
        ha = hashlib.sha256(a).hexdigest()[:12]
        hb = hashlib.sha256(b).hexdigest()[:12]
        diff = "✓ 不同录音" if a != b else "✗ 完全相同"
        out.append(f"{w:<10} 英={len(a):>6,}B {ha}   美={len(b):>6,}B {hb}   "
                   f"{diff}  比率={len(b)/max(len(a),1):.2f}")
    except Exception as e:
        out.append(f"{w:<10} 失败: {type(e).__name__}: {e}")

out.append("")
out.append("解析 mp3 头部确认采样率/时长：")
import io
try:
    for w in ["water"]:
        for typ, nm in ((1, "英"), (2, "美")):
            d = grab(w, typ)
            # 简单解析第一个 MPEG 帧头
            i = d.find(b"\xff\xfb")
            if i >= 0:
                h = d[i:i + 4]
                ver = (h[1] >> 3) & 0x3
                br = (h[2] >> 4) & 0xF
                sr = (h[2] >> 2) & 0x3
                BR = [None, 32, 40, 48, 56, 64, 80, 96, 112, 128, 160, 192,
                      224, 256, 320, None]
                SR = [44100, 48000, 32000, None]
                out.append(f"    {w} {nm}: MPEG ver bits={ver} "
                           f"bitrate={BR[br]}kbps samplerate={SR[sr]} "
                           f"总长={len(d):,}B 约{len(d)*8/BR[br]/1000:.1f}秒")
except Exception as e:
    out.append(f"    解析失败: {e}")

out.append("")
out.append("检查 pywin32 / 其它可用 TTS 路线：")
for m in ("win32com", "comtypes", "pyttsx3"):
    try:
        __import__(m)
        out.append(f"    ✓ {m} 已安装")
    except Exception:
        out.append(f"    ✗ {m} 未安装")

open(r"D:\Dictionary\build\_probe3.txt", "w", encoding="utf-8").write(
    "\n".join(out))
print("ok")
