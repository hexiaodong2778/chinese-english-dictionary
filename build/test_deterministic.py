"""确定性验证：逐个语言切换，切换后等待生效再断言，避免计时器竞态。"""
import sys, os, time
sys.path.insert(0, r"D:\Dictionary\build")
from PySide6.QtWidgets import QApplication
import app as A

qapp = QApplication(sys.argv)
w = A.MainWindow()
w.resize(1120, 740)
w.show()


def settle(ms=350):
    end = time.time() + ms / 1000.0
    while time.time() < end:
        qapp.processEvents()
        time.sleep(0.01)


print("=== 语言切换（等待生效后断言）===")
expect = [(0, "en", "dict.db"), (1, "ja", "dict_ja.db"),
          (2, "fr", "dict_fr.db"), (3, "yue", "dict_yue.db")]
ok = True
for idx, key, dbname in expect:
    w.lang_box.setCurrentIndex(idx)
    settle()
    got = w.lang
    total = w.engine.stats().get("total") if (w.engine and w.engine.con) else None
    path = A.resource_path(dbname)
    good = (got == key) and total
    ok = ok and bool(good)
    print(f"  idx={idx} 期望={key:4s} 实际={got:4s} total={total} "
          f"db={os.path.basename(path)} {'OK' if good else 'FAIL'}")

print("\n=== 各语言实际查词 ===")
cases = [(1, "学校", "日语"), (2, "bonjour", "法语"), (3, "nei", "粤语")]
for idx, q, label in cases:
    w.lang_box.setCurrentIndex(idx)
    settle()
    rows = w.engine.suggest(q, 3) if (w.engine and w.engine.con) else []
    d = w.engine.lookup(q, "all") if (w.engine and w.engine.con) else None
    print(f"  {label}: suggest({q}) -> {[r['word'] for r in rows][:3]}  "
          f"lookup={'hit' if d else 'miss'}")

print("\n=== 中译英模式 ===")
w.lang_box.setCurrentIndex(0)
settle()
w.cn_btn.click()
settle()
print(f"  cn 按钮 checked={w.cn_btn.isChecked()} 文本={w.cn_btn.text()!r}")
w.search_edit.setText("学习")
settle(500)
print(f"  结果条数={w.result_list.count()}")
items = [w.result_list.item(i).text().replace("\n", " | ")
         for i in range(min(3, w.result_list.count()))]
for it in items:
    print("   ", it)

print("\n=== 高考词典 ===")
gk_btn = None
for b in w.dict_group.buttons():
    if "高考" in b.text():
        gk_btn = b
        break
print("  找到高考按钮:", bool(gk_btn))
if gk_btn:
    gk_btn.click()          # 用真实点击切换词典
    settle()
    print("  当前词典 key =", getattr(w, "cur_dict", "?"),
          " checked =", gk_btn.isChecked())
    for q in ["achieve", "beautiful", "photosynthesis"]:
        w.search_edit.setText(q)
        settle(400)
        print(f"  [{q}] 结果={w.result_list.count()}")

w.close()
print("\nALL DETERMINISTIC TESTS DONE  ok=", ok)
