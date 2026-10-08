"""对比 winrt 与 sapi 引擎各自的语音列表。"""
import sys
from PySide6.QtCore import QCoreApplication, QTimer
from PySide6.QtTextToSpeech import QTextToSpeech

app = QCoreApplication(sys.argv)

for eng in ("winrt", "sapi"):
    print(f"\n{'='*60}\n引擎: {eng}\n{'='*60}")
    try:
        tts = QTextToSpeech(eng)
        print("状态:", tts.state())
        vs = tts.availableVoices()
        print(f"语音数: {len(vs)}")
        for v in vs:
            loc = v.locale().name()
            print(f"  {v.name():34s} {loc:10s} {v.gender()}")
        del tts
    except Exception as e:
        print("失败:", e)

print("\n=== 用 sapi 引擎朗读英文 ===")
try:
    tts = QTextToSpeech("sapi")
    print("状态:", tts.state(), "当前语音:", tts.voice().name() if tts.voice() else None)
    # 找一个英文语音
    for v in tts.availableVoices():
        if v.locale().name().startswith("en"):
            tts.setVoice(v)
            print("切换到英文语音:", v.name(), v.locale().name())
            break
    tts.say("hello, this is a dog")
    print("say() 已发出, 状态 =", tts.state())
    QTimer.singleShot(3000, app.quit)
except Exception as e:
    print("失败:", e)
    app.quit()

sys.exit(app.exec())
