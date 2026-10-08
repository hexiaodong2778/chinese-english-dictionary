# -*- coding: utf-8 -*-
"""验证修复思路：
① 用 Zira（真正的美音语音）直接读单词原文，而不是读音标转出的伪串
   与旧方案（读音标转写串）做对比，看看是否正常
② 用 SSML / rate 调整语速，解决「太快」的问题
③ 确认英式语音确实不存在（那就必须走在线发音或提示用户装语言包）
"""
import os
import sys

sys.path.insert(0, r"D:\Dictionary\build")

out = []
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtWidgets import QApplication
from PySide6.QtTextToSpeech import QTextToSpeech

app = QApplication.instance() or QApplication([])

out.append("=" * 70)
out.append("引擎与语音清单")
out.append("=" * 70)
for eng in ("sapi", "winrt", ""):
    try:
        t = QTextToSpeech(eng) if eng else QTextToSpeech()
    except Exception as e:
        out.append(f"{eng or 'default'}: 异常 {e}")
        continue
    vs = list(t.availableVoices())
    out.append(f"{eng or 'default'}: {len(vs)} 个语音")
    for v in vs:
        out.append(f"    {v.name()}  [{v.locale().name()}]  "
                   f"gender={v.gender()}  age={v.age()}")

out.append("")
out.append("=" * 70)
out.append("关键：sapi 引擎下用 Zira 直接读原词（新方案）")
out.append("=" * 70)
t = QTextToSpeech("sapi")
vs = list(t.availableVoices())
zira = None
for v in vs:
    if "zira" in v.name().lower():
        zira = v
        break
if zira is None:
    out.append("sapi 引擎下没有 Zira！列出全部：")
    for v in vs:
        out.append(f"    {v.name()} [{v.locale().name()}]")
else:
    out.append(f"找到 Zira: {zira.name()} [{zira.locale().name()}]")
    t.setVoice(zira)
    out.append(f"设置后 currentVoice = {t.voice().name() if t.voice() else None}")
    # 测试朗读（虽然 offscreen 听不到，但至少确认不报错）
    for rate in (-0.3, -0.15, 0.0):
        t.setRate(rate)
        t.say("water")
        out.append(f"    rate={rate} 已提交朗读, state={t.state()}")

out.append("")
out.append("=" * 70)
out.append("速率范围（Qt 允许的区间）")
out.append("=" * 70)
t2 = QTextToSpeech("sapi")
out.append("    Qt6 无 minimumRate/maximumRate 属性")
out.append(f"    当前 rate() = {t2.rate()}")
out.append("    Qt6 rate() 取值范围 -1.0 ~ 1.0（默认 0）")
t2.setRate(-0.25)
out.append(f"    setRate(-0.25) 后 rate() = {t2.rate()}")
t2.setRate(-0.4)
out.append(f"    setRate(-0.4) 后 rate() = {t2.rate()}")

open(r"D:\Dictionary\build\_fixprobe.txt", "w", encoding="utf-8").write(
    "\n".join(out))
print("ok")
