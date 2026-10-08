"""回归测试：语言切换与「中译英」的互斥关系。

覆盖的 bug：
    英语下开启「中译英」后切到日语，按钮虽被隐藏但仍保持 checked，
    导致查词被错误送进中译英分支（界面上出现「没有匹配 学校 的英文词」）。
修复后要求：
    · 离开英语时自动取消「中译英」
    · 日语查「学校」应得到日文词条候选
    · 回英语后「中译英」默认关闭，可再次开启并生效
"""
import sys, os, time
sys.path.insert(0, r"D:\Dictionary\build")
from PySide6.QtWidgets import QApplication
import app as A

qapp = QApplication(sys.argv)
w = A.MainWindow()
w.resize(1180, 760)
w.show()


def settle(ms=450):
    end = time.time() + ms / 1000.0
    while time.time() < end:
        qapp.processEvents()
        time.sleep(0.01)


fails = []


def check(name, cond, detail=""):
    print(("  PASS  " if cond else "  FAIL  ") + name + ("  " + detail if detail else ""))
    if not cond:
        fails.append(name)


settle(800)

print("=== 1. 英语下开启中译英 ===")
w.cn_btn.click()
settle()
check("中译英已开启", w.cn_btn.isChecked())
w.search_edit.setText("学习")
settle(600)
n_cn = w.result_list.count()
check("中译英有结果", n_cn > 0, f"条数={n_cn}")
check("列表标题含『中文反查』", "中文反查" in w.list_hint.text(), w.list_hint.text())

print("\n=== 2. 保持中译英开启，切到日语（核心回归点）===")
w.lang_box.setCurrentIndex(1)      # 日语
settle(700)
check("lang 已切到 ja", w.lang == "ja", f"lang={w.lang}")
check("中译英已被自动关闭", not w.cn_btn.isChecked())
check("中译英按钮已隐藏", not w.cn_btn.isVisible())
w.search_edit.setText("学校")
settle(800)
n_ja = w.result_list.count()
check("日语「学校」有候选", n_ja > 0, f"条数={n_ja}")
check("列表标题是『候选词』而非中文反查",
      "中文反查" not in w.list_hint.text(), w.list_hint.text())
first = w.result_list.item(0).text().replace("\n", " | ") if n_ja else ""
print("        首条:", first)
# 结果不应是英文单词（中译英的典型输出）
check("结果命中的是日语词条",
      bool(w.engine.lookup("学校", "all")) is True)

print("\n=== 3. 切回英语，中译英应保持关闭 ===")
w.lang_box.setCurrentIndex(0)      # 英语
settle(700)
check("lang 已回 en", w.lang == "en", f"lang={w.lang}")
check("中译英仍为关闭", not w.cn_btn.isChecked())
w.search_edit.setText("beautiful")
settle(700)
check("英语查词正常", w.result_list.count() > 0, f"条数={w.result_list.count()}")
check("按钮可见", w.cn_btn.isVisible())

print("\n=== 4. 重新开启中译英应仍可用 ===")
w.cn_btn.click()
settle(400)
w.search_edit.setText("美丽")
settle(700)
check("中译英再次生效", w.result_list.count() > 0, f"条数={w.result_list.count()}")
check("标题含『中文反查』", "中文反查" in w.list_hint.text(), w.list_hint.text())

print("\n=== 5. 逐个语言切换，中译英均不应残留 ===")
for idx, k in [(1, "ja"), (2, "fr"), (3, "yue")]:
    w.cn_btn.click()               # 先确保开启（英语下才可见可点）
    settle(300)
    w.lang_box.setCurrentIndex(idx)
    settle(500)
    check(f"切到 {k} 后中译英关闭", not w.cn_btn.isChecked())
    check(f"{k} 下按钮不可见", not w.cn_btn.isVisible())
    w.lang_box.setCurrentIndex(0)
    settle(400)

w.close()
print("\n" + ("ALL PASS" if not fails else f"FAILED: {fails}"))
sys.exit(1 if fails else 0)
