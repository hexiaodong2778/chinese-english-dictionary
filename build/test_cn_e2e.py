# -*- coding: utf-8 -*-
"""端到端：GUI 输入「开心」→ 联网补充 → 结果含 happy 系"""
import os, sys, io, time
os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, r"D:\Dictionary\build")
from PySide6.QtWidgets import QApplication
app = QApplication(sys.argv)
import app as A

ok = fail = 0
def chk(n, c, e=""):
    global ok, fail
    if c: ok += 1; print(f"  PASS  {n} {e}")
    else: fail += 1; print(f"  FAIL  {n} {e}")

w = A.MainWindow(); w.resize(1080, 720); w.show(); app.processEvents()

print("\n[1] 输入「开心」，看离线首屏")
w.search_edit.setText("开心"); w._flush_query()
for _ in range(6): app.processEvents()
n0 = w.result_list.count()
print(f"  离线条数 = {n0}")
hint = w.list_hint.text()
print(f"  提示 = {hint!r}")

print("\n[2] 等待联网补充回来（最多 12s）")
t0 = time.time()
while time.time() - t0 < 12:
    app.processEvents()
    if A.DictEngine.has_cn_extra("开心"):
        break
    time.sleep(0.1)
got = A.DictEngine.has_cn_extra("开心")
print(f"  已取回 = {got}  耗时 {(time.time()-t0):.1f}s")
print(f"  英文表达 = {A.DictEngine._cn_extra.get('开心')}")

# 再等渲染
for _ in range(20): app.processEvents(); time.sleep(0.05)

print("\n[3] 检查结果列表")
items = [w.result_list.item(i).data(0) for i in range(w.result_list.count())]
words = [w.result_list.item(i).data(A.Qt.UserRole)
         for i in range(w.result_list.count())]
print(f"  条数 = {len(words)}")
print(f"  前 6 = {words[:6]}")
chk("结果非空", len(words) > 0, str(len(words)))
chk("含 happy 系", any(x.lower() in ("happy", "delighted", "joyful", "rejoice",
                                    "glad") for x in words), str(words[:6]))
chk("不含 open core（标签噪声）",
    not any("open core" in x.lower() for x in words), str(words))
chk("happy 在首位或前列", any(x.lower() == "happy" for x in words[:3]),
    str(words[:3]))

print("\n[4] 其它中文词不受影响")
for kw, want in [("水", "water"), ("狗", "dog"), ("书", "book"),
                 ("电脑", "computer"), ("学习", "study")]:
    w.search_edit.setText(kw); w._flush_query()
    for _ in range(5): app.processEvents()
    ws = [w.result_list.item(i).data(A.Qt.UserRole)
          for i in range(w.result_list.count())]
    chk(f"「{kw}」首项={ws[0] if ws else None}",
        ws and ws[0].lower() == want, str(ws[:3]))

print("\n[5] 英文查词仍走 suggest、不受影响")
for kw in ["happy", "water", "dog"]:
    w.search_edit.setText(kw); w._flush_query()
    for _ in range(5): app.processEvents()
    ws = [w.result_list.item(i).data(A.Qt.UserRole)
          for i in range(w.result_list.count())]
    chk(f"「{kw}」首项={ws[0] if ws else None}",
        ws and ws[0].lower() == kw, str(ws[:3]))

print(f"\nPASS={ok}  FAIL={fail}")
w.close()
sys.exit(0 if fail == 0 else 1)
