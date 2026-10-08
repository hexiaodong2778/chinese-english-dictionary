"""测试语言切换与中译英的真实渲染。"""
import sys, os
sys.path.insert(0, r"D:\Dictionary\build")
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer
import app as A

app = QApplication(sys.argv)
w = A.MainWindow()
w.resize(1120, 740)
w.show()

steps = []

def step_lang_ja():
    w.lang_box.setCurrentIndex(1)   # 日语
    QTimer.singleShot(300, lambda: w.search_edit.setText("学校"))

def step_snap_ja():
    p = r"D:\Dictionary\build\shot_ja.png"
    w.grab().save(p)
    print("ja:", os.path.getsize(p), "lang=", w.lang,
          "engine_db_ok=", bool(w.engine and w.engine.con))
    if w.engine and w.engine.con:
        rows = w.engine.suggest("学", 5)
        print("   ja suggest:", [r["word"] for r in rows])
    QTimer.singleShot(200, step_lang_fr)

def step_lang_fr():
    w.lang_box.setCurrentIndex(2)   # 法语
    QTimer.singleShot(300, lambda: w.search_edit.setText("bonjour"))

def step_snap_fr():
    p = r"D:\Dictionary\build\shot_fr.png"
    w.grab().save(p)
    print("fr:", os.path.getsize(p), "lang=", w.lang)
    if w.engine and w.engine.con:
        rows = w.engine.suggest("bonj", 5)
        print("   fr suggest:", [r["word"] for r in rows])
        d = w.engine.lookup("bonjour", "all")
        print("   fr lookup bonjour:", d.get("phonetic") if d else None)
    QTimer.singleShot(200, step_lang_yue)

def step_lang_yue():
    w.lang_box.setCurrentIndex(3)   # 粤语
    QTimer.singleShot(300, lambda: w.search_edit.setText("nei"))

def step_snap_yue():
    p = r"D:\Dictionary\build\shot_yue.png"
    w.grab().save(p)
    print("yue:", os.path.getsize(p), "lang=", w.lang)
    if w.engine and w.engine.con:
        print("   yue total:", w.engine.stats().get("total"))
    QTimer.singleShot(200, step_en_cn)

def step_en_cn():
    w.lang_box.setCurrentIndex(0)   # 回到英语
    # 用 click() 模拟真实点击，使其进入「中译英」状态
    w.cn_btn.click()
    QTimer.singleShot(300, lambda: w.search_edit.setText("学习"))

def step_snap_cn():
    p = r"D:\Dictionary\build\shot_cn2.png"
    w.grab().save(p)
    print("cn:", os.path.getsize(p), "cn_mode=", w.cn_btn.isChecked(),
          "rows=", w.result_list.count())
    app.quit()

QTimer.singleShot(600, step_lang_ja)
QTimer.singleShot(1000, step_snap_ja)
QTimer.singleShot(1300, step_snap_fr)
QTimer.singleShot(1700, step_snap_yue)
QTimer.singleShot(2100, step_snap_cn)

sys.exit(app.exec())
