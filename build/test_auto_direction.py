"""测试自动方向识别 + 中译英点击后渲染完整词条。

关键验收点（对应需求）：
  1. 输入「狗」自动走中译英，首选 dog
  2. 点击结果 → 渲染 dog 的完整词条（含美/英音标、多词典释义）
  3. 输入英文 "dog" 自动走英译中，不被误判
  4. 「锁定中文」按钮按下后强制中译英
"""
import sys
import time
sys.path.insert(0, r"D:\Dictionary\build")
from PySide6.QtWidgets import QApplication
import app as A

qapp = QApplication(sys.argv)
w = A.MainWindow()
w.resize(1180, 760)
w.show()


def settle(ms=500):
    end = time.time() + ms / 1000.0
    while time.time() < end:
        qapp.processEvents()
        time.sleep(0.01)


fails = []


def check(name, cond, detail=""):
    print(("  PASS  " if cond else "  FAIL  ") + name +
          ("  " + detail if detail else ""))
    if not cond:
        fails.append(name)


settle(800)

print("=== 1. detect_direction 静态判断 ===")
cases = [("狗", "cn2en"), ("dog", "en2cn"), ("学习", "cn2en"),
         ("hello world", "en2cn"), ("水", "cn2en"), ("abandon", "en2cn"),
         ("电脑abc", "cn2en"), ("", "en2cn")]
for text, expect in cases:
    got = A.MainWindow.detect_direction(text)
    check(f"detect_direction({text!r}) == {expect}", got == expect, f"got={got}")

print("\n=== 2. 输入『狗』自动中译英 ===")
w.search_edit.setText("狗")
settle(900)
rows = w.result_list.count()
check("有结果", rows > 0, f"条数={rows}")
first = w.result_list.item(0).data(A.MainWindow.__dict__.get("X", 0) or 0) \
    if False else w.result_list.item(0).text()
check("首选是 dog", first.startswith("dog"), f"首行={first[:40]!r}")
check("列表标题为『中文反查』", "中文反查" in w.list_hint.text(),
      w.list_hint.text())
print("        前 3 条:",
      [w.result_list.item(i).text().split("\n")[0]
       for i in range(min(3, rows))])

print("\n=== 3. 点击 dog → 渲染完整词条 ===")
w.result_list.setCurrentRow(0)
settle(700)
html = w.detail.toHtml()
check("已渲染词条", w._cur_word == "dog", f"_cur_word={w._cur_word!r}")
check("含美式音标", "美" in html and "/" in html)
check("含英式音标", "英" in html)
check("不含『没有找到』", "没有找到" not in html and "查不到" not in html)
check("含中文释义『狗』", "狗" in html)
print("        _cur_word =", w._cur_word,
      "| 美音标 =", w._cur_ph_us, "| 英音标 =", w._cur_ph_uk)

print("\n=== 4. 输入英文 dog 不被误判为中文 ===")
w.search_edit.setText("dog")
settle(800)
check("列表标题不是中文反查", "中文反查" not in w.list_hint.text(),
      w.list_hint.text())
t0 = w.result_list.item(0).text() if w.result_list.count() else ""
check("首选是 dog 词条", t0.startswith("dog"), f"首行={t0[:40]!r}")

print("\n=== 5. 混合内容自动识别 ===")
w.search_edit.setText("狗dog")
settle(800)
check("含中文 → 走中译英", "中文反查" in w.list_hint.text(),
      w.list_hint.text())

print("\n=== 6. 锁定中文模式 ===")
w.search_edit.clear()
settle(300)
w.cn_btn.click()
settle(500)
check("已锁定", w._cn_locked)
check("按钮文案为『锁定中文』", w.cn_btn.text() == "锁定中文",
      w.cn_btn.text())
check("词典按钮已隐藏",
      all(not b.isVisible() for b in w.dict_buttons))
w.search_edit.setText("猫")
settle(800)
check("锁定下查『猫』出 cat",
      w.result_list.count() > 0 and
      w.result_list.item(0).text().startswith("cat"),
      w.result_list.item(0).text()[:30] if w.result_list.count() else "-")

print("\n=== 7. 解锁恢复自动 ===")
w.cn_btn.click()
settle(400)
check("已解锁", not w._cn_locked)
w.search_edit.setText("dog")
settle(700)
check("英文走英译中", "中文反查" not in w.list_hint.text(),
      w.list_hint.text())
check("词典按钮恢复可见",
      any(b.isVisible() for b in w.dict_buttons))

w.close()
print("\n" + ("ALL PASS" if not fails else f"FAILED ({len(fails)}): {fails}"))
sys.exit(1 if fails else 0)
