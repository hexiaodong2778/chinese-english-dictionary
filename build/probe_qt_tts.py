"""验证 QtTextToSpeech：是否可用、能列出哪些语音、能否朗读。

QtTextToSpeech 底层走 Windows SAPI（Qt 的 sapi 插件），
全程在本进程内完成，不会 spawn powershell.exe，
因此不会触发杀毒软件的「脚本执行」告警。
"""
import sys
from PySide6.QtCore import QCoreApplication, QTimer
from PySide6.QtTextToSpeech import QTextToSpeech

app = QCoreApplication(sys.argv)

engines = QTextToSpeech.availableEngines()
print("可用引擎:", engines)

tts = QTextToSpeech()
print("默认引擎:", tts.engine())
print("状态:", tts.state())

print("\n=== 可用语音 ===")
voices = tts.availableVoices()
for v in voices:
    print(f"  名称={v.name()!r:42s} 语言={v.locale().name():10s} "
          f"性别={v.gender()} 年龄={v.age()}")

print(f"\n共 {len(voices)} 个语音")
print("当前语音:", tts.voice().name() if tts.voice() else None)

# 测试朗读
print("\n=== 朗读测试 ===")
tts.say("hello, this is a dog")
print("已发出 say()，状态 =", tts.state())

def finish():
    print("朗读结束，最终状态 =", tts.state())
    app.quit()

QTimer.singleShot(3500, finish)
sys.exit(app.exec())
