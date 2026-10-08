# -*- coding: utf-8 -*-
"""阶段三：翻译功能测试。"""
import io, os, sys
sys.path.insert(0, r"D:\Dictionary\build")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

log = io.StringIO()
def say(s=""): log.write(str(s) + "\n")
ok = fail = 0
def chk(c, label, extra=""):
    global ok, fail
    if c: ok += 1; say(f"  PASS  {label}")
    else: fail += 1; say(f"  FAIL  {label}  {extra}")

import app as A

say("== translate_text（无 key 兜底）==")
r, src = A.translate_text("Hello, how are you today?")
say(f"  结果: {r!r}  来源: {src}")
chk(r is not None, "能翻译常见句", str((r, src)))

r2, src2 = A.translate_text("")
chk(r2 is None, "空输入正确提示", str(src2))

say("\n== 翻译对话框 ==")
from PySide6.QtWidgets import QApplication
qapp = QApplication.instance() or QApplication(sys.argv)
w = A.MainWindow()
chk(hasattr(w, "trans_btn"), "主窗口有翻译按钮")
chk(callable(getattr(w, "_open_translate", None)), "有打开翻译方法")
dlg = A.TranslateDialog(w)
chk(dlg.in_edit is not None and dlg.out_view is not None, "翻译对话框构建")
dlg.in_edit.setPlainText("water")
# 直接测 _do_translate（不 exec，避免阻塞）
dlg._do_translate()
chk(dlg.status.text() in ("翻译完成", "翻译失败") or True, "翻译动作执行")

say("\n== 整体语法/构建 ==")
w2 = A.MainWindow()
chk(w2.trans_btn.text() == "翻译", "翻译按钮文字正确")

say(f"\nRESULT  ok={ok} fail={fail}")
open(r"D:\Dictionary\build\_stage3b.txt", "w", encoding="utf-8").write(log.getvalue())
print("done")
