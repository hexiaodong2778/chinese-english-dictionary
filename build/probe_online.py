# -*- coding: utf-8 -*-
"""验证三件事：
① 能不能绕过 QtTextToSpeech，直接通过 SAPI COM 拿到 Zira 并朗读
   （QtTextToSpeech 的 sapi 插件枚举不到 Zira，但注册表里明明有）
② 有道 / 剑桥的在线发音接口能不能直连、返回什么
③ 缺失音标能不能从开源数据补（先探接口可用性）
"""
import json
import os
import sys
import urllib.error
import urllib.request

out = []


def head(url, label, referer=None):
    hdr = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    if referer:
        hdr["Referer"] = referer
    try:
        req = urllib.request.Request(url, headers=hdr, method="GET")
        with urllib.request.urlopen(req, timeout=12) as r:
            data = r.read(400)
            ct = r.headers.get("Content-Type", "?")
            cl = r.headers.get("Content-Length", "?")
            out.append(f"  ✓ {label}")
            out.append(f"      status={r.status} type={ct} len={cl}")
            out.append(f"      head={data[:60]!r}")
            return True
    except urllib.error.HTTPError as e:
        out.append(f"  ✗ {label}  HTTP {e.code} {e.reason}")
    except Exception as e:
        out.append(f"  ✗ {label}  {type(e).__name__}: {e}")
    return False


out.append("=" * 72)
out.append("① SAPI COM 直取 Zira（绕过 QtTextToSpeech）")
out.append("=" * 72)
try:
    import win32com.client  # noqa
    out.append("  pywin32 已安装")
except Exception as e:
    out.append(f"  pywin32 未安装: {e}")
    out.append("  → 改用 winreg + ctypes 路线，或装 pywin32")

# 检查是否已有 win32com
try:
    import win32com.client as wc
    sp = wc.Dispatch("SAPI.SpVoice")
    voices = sp.GetVoices()
    out.append(f"  SAPI.SpVoice 可用，语音数 = {voices.Count}")
    for i in range(voices.Count):
        v = voices.Item(i)
        out.append(f"      [{i}] {v.GetDescription()}")
    # 尝试直接给 Zira 一个 token 并朗读
    for i in range(voices.Count):
        d = voices.Item(i).GetDescription()
        if "zira" in d.lower():
            sp.Voice = voices.Item(i)
            out.append(f"  ★ 已切换到: {d}")
            sp.Rate = -1          # SAPI rate: -10 ~ 10
            sp.Volume = 100
            sp.Speak("water", 0)  # 0=同步等待说完
            out.append("  ★ Speak('water') 同步执行完成，无异常")
            break
except Exception as e:
    out.append(f"  SAPI 路线失败: {type(e).__name__}: {e}")

out.append("")
out.append("=" * 72)
out.append("② 在线发音接口探测")
out.append("=" * 72)

# 有道
out.append("【有道】youdao.com")
head("https://dict.youdao.com/dictvoice?audio=water&type=2",
     "美音 type=2")
head("https://dict.youdao.com/dictvoice?audio=water&type=1",
     "英音 type=1")
head("https://dict.youdao.com/dictvoice?audio=water",
     "默认（无 type）")

out.append("")
out.append("【剑桥】dictionary.cambridge.org（通常有反爬）")
head("https://dictionary.cambridge.org/media/english/us_pron/w/wat/water/water.mp3",
     "剑桥美音 mp3 直链")

out.append("")
out.append("【金山词霸】iciba")
head("https://res.iciba.com/resource/amp3/oxford/0/48/4830d5dd5f0d0b1c7d5e.mp3",
     "iciba 静态 mp3")

out.append("")
out.append("【腾讯/其他备选】")
head("https://fanyi.baidu.com/gettts?lan=en&text=water&spd=3&source=web",
     "百度翻译 TTS")

out.append("")
out.append("=" * 72)
out.append("③ 开源音标数据源探测")
out.append("=" * 72)
head("https://raw.githubusercontent.com/open-dict-data/ipa-dict/master/data/en_US.txt",
     "ipa-dict en_US")
head("https://raw.githubusercontent.com/open-dict-data/ipa-dict/master/data/en_UK.txt",
     "ipa-dict en_UK")

open(r"D:\Dictionary\build\_probe2.txt", "w", encoding="utf-8").write(
    "\n".join(out))
print("ok")
