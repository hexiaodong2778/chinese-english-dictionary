"""抓取真实运行窗口截图（英语首页 + 查词结果），用于最终验收。"""
import sys, os, time
sys.path.insert(0, r"D:\Dictionary\build")
from PySide6.QtWidgets import QApplication
import app as A

qapp = QApplication(sys.argv)
w = A.MainWindow()
w.resize(1180, 760)
w.show()


def settle(ms=600):
    end = time.time() + ms / 1000.0
    while time.time() < end:
        qapp.processEvents()
        time.sleep(0.01)


settle(900)
w.grab().save(r"D:\Dictionary\build\final_home.png")
print("home saved")

# 查一个多义词，展示详情区
w.search_edit.setText("beautiful")
settle(800)
w.grab().save(r"D:\Dictionary\build\final_word.png")
print("word saved")

# 切到高考词典
for b in w.dict_group.buttons():
    if "高考" in b.text():
        b.click()
        break
settle(400)
w.search_edit.setText("achieve")
settle(800)
w.grab().save(r"D:\Dictionary\build\final_gk.png")
print("gk saved")

# 中译英
w.lang_box.setCurrentIndex(0)
settle(400)
w.search_edit.setText("学习")
w.cn_btn.click()
settle(900)
w.grab().save(r"D:\Dictionary\build\final_cn.png")
print("cn saved")

# 日语
w.lang_box.setCurrentIndex(1)
settle(600)
w.search_edit.setText("学校")
settle(800)
w.grab().save(r"D:\Dictionary\build\final_ja.png")
print("ja saved")

w.close()
print("DONE")
