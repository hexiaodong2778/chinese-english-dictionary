"""直接驱动界面状态，验证语言切换与中译英（不用定时器链）。"""
import sys, os
sys.path.insert(0, r"D:\Dictionary\build")
from PySide6.QtWidgets import QApplication
import app as A

app = QApplication(sys.argv)
w = A.MainWindow()
w.resize(1120, 740)
w.show()
app.processEvents()

def settle(n=8):
    for _ in range(n):
        app.processEvents()

print("=== 语言切换逐一验证 ===")
for i, (k, v) in enumerate(A.LANG_DEFS.items()):
    w.lang_box.setCurrentIndex(i)
    settle()
    ok = bool(w.engine and w.engine.con)
    tot = w.engine.stats().get("total", 0) if ok else 0
    print(f"  idx={i} key={k:4s} 期望={k} 实际={w.lang} db_ok={ok} total={tot:,}")

print("\n=== 粤语罗马字查询 ===")
w.lang_box.setCurrentIndex(3)
settle()
w.search_edit.setText("nei")
settle()
print(f"  lang={w.lang} 候选数={w.result_list.count()}")
for i in range(min(3, w.result_list.count())):
    print("   ", repr(w.result_list.item(i).text()))

print("\n=== 日语罗马字查询 ===")
w.lang_box.setCurrentIndex(1)
settle()
w.search_edit.setText("nihon")
settle()
print(f"  lang={w.lang} 候选数={w.result_list.count()}")
for i in range(min(3, w.result_list.count())):
    print("   ", repr(w.result_list.item(i).text()))

print("\n=== 中译英模式 ===")
w.lang_box.setCurrentIndex(0)
settle()
w.cn_btn.click()
settle()
print(f"  cn_btn.isChecked()={w.cn_btn.isChecked()} 按钮文字={w.cn_btn.text()!r}")
w.search_edit.setText("学习")
settle()
print(f"  候选数={w.result_list.count()}")
for i in range(min(4, w.result_list.count())):
    print("   ", repr(w.result_list.item(i).text()))

print("\n=== 高考词典查询 ===")
w.cn_btn.click()   # 关掉中译英
settle()
w.dict_buttons[3].click()   # 高考
settle()
print(f"  cur_dict={A.DICTS[w.cur_dict_idx]['label']} checked={w.dict_buttons[3].isChecked()}")
for word in ["achieve", "beautiful", "photosynthesis"]:
    w.search_edit.setText(word)
    settle()
    print(f"  [{word}] 候选={w.result_list.count()}")

print("\nALL UI STATE TESTS DONE")
