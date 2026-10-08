# -*- coding: utf-8 -*-
"""无头渲染：测量底部发音文字宽度、收藏按钮可见性"""
import os, sys, io, tempfile
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

for W, H, tag in [(1080, 720, "默认"), (980, 660, "较窄")]:
    print(f"\n===== 窗口 {W}x{H}（{tag}）=====")
    w = A.MainWindow()
    # 测试进程可能没有权限写 %LOCALAPPDATA%；改用临时数据库，
    # 避免收藏状态受用户真实单词本和沙箱权限影响。
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    try:
        os.remove(db_path)
    except OSError:
        pass
    w.store = A.UserStore(db_path)
    w.resize(W, H)
    w.show()
    app.processEvents()
    w.search_edit.setText("happy")
    w._flush_query()
    for _ in range(6):
        app.processEvents()
    w._speak("us")
    for _ in range(8):
        app.processEvents()

    pn = w.pron_now
    print(f"  pron_now 宽度 = {pn.width()}px  高度 = {pn.height()}px")
    print(f"  pron_now 文本 = {pn.text()!r}")
    print(f"  fav_btn 可见 = {w.fav_btn.isVisible()}  "
          f"宽={w.fav_btn.width()} 文本={w.fav_btn.text()!r} 启用={w.fav_btn.isEnabled()}")
    print(f"  cfg_hint 宽 = {w.cfg_hint.width()}  文本={w.cfg_hint.text()!r}")
    print(f"  正文区 = {w.detail.width()}x{w.detail.height()}")

    chk("发音文字宽度 >= 120px", pn.width() >= 120, f"{pn.width()}px")
    # 文字不被截断：标签理想宽度 <= 实际宽度
    hint = pn.sizeHint().width()
    chk("发音文字未被截断", pn.width() >= min(hint, 400),
        f"实宽{pn.width()} 需{hint}")
    chk("收藏按钮可见", w.fav_btn.isVisible())
    chk("收藏按钮文字正确", "收藏" in w.fav_btn.text(), w.fav_btn.text())

    print("\n  -- 点收藏后状态同步 --")
    w._toggle_fav()
    app.processEvents()
    print(f"  fav_btn 文本 = {w.fav_btn.text()!r}")
    chk("收藏后按钮变★", "★" in w.fav_btn.text(), w.fav_btn.text())
    w._toggle_fav()
    app.processEvents()
    chk("取消后按钮变☆", "☆" in w.fav_btn.text(), w.fav_btn.text())

    if W == 1080:
        w.grab().save(r"D:\Dictionary\build\_shot_layout.png")
        print("  已存 _shot_layout.png")
    w.close()
    try:
        w.store.con.close()
        os.remove(db_path)
    except OSError:
        pass

print(f"\nPASS={ok}  FAIL={fail}")
sys.exit(0 if fail == 0 else 1)
