# -*- coding: utf-8 -*-
"""截图：本轮三项改动的界面证据。

  ① 小贴士可折叠（展开 / 收起各一张，能看到省出的高度）
  ② 日语词条的「中文意思」（机翻参考），以及词头「↩ 返回」胶囊
  ③ 日语模式的翻译对话框（标题写明「中文 ⇄ 日语」）
  ④ 日语模式下输入中文的反查结果

⚠ 全程用临时目录存用户数据与配置，绝不碰真实 user_data.db / dict_config.json。
⚠ 会联网的地方（反查、机翻）都提前把结果注入缓存，让截图可复现、不受网速影响。
"""
import io
import os
import sys
import tempfile

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8",
                              errors="replace")
sys.path.insert(0, r"D:\Dictionary\build")

from PySide6.QtWidgets import QApplication

qapp = QApplication(sys.argv)
import app as A

_TMP = tempfile.mkdtemp(prefix="shotml_")
_o = A.UserStore.__init__
A.UserStore.__init__ = lambda self, path=None: _o(
    self, os.path.join(_TMP, "user_data.db"))
A.CONFIG_PATH = os.path.join(_TMP, "dict_config.json")
A.CONFIG.pop("tip_collapsed", None)

w = A.MainWindow()
w.resize(1080, 720)
w.show()
qapp.processEvents()


def pump(n=6):
    for _ in range(n):
        qapp.processEvents()


def shot(name):
    p = r"D:\Dictionary\build\_shot_%s.png" % name
    w.grab().save(p)
    print("saved", os.path.basename(p))


w.search_edit.setText("happy")
w._flush_query()
pump(8)

# ---------------------------------------------------------------- ① 小贴士
w.side_tabs.setCurrentIndex(0)
pump(4)
print("tip 展开时高度 =", w.tip_box.sizeHint().height())
shot("tip_expanded")
w._toggle_tip()
pump(4)
print("tip 收起时高度 =", w.tip_box.sizeHint().height(),
      "  按钮 =", repr(w.tip_toggle.text()))
shot("tip_collapsed")
w._toggle_tip()          # 还原成展开，给后面几张图留完整界面
pump(4)

# ------------------------------------------------- ② 日语词条 + 机翻中文意思
w.lang = "ja"
w.engine = w.dicts.get("ja") or w.dicts["en"]
w._mt_cache[("ja", "友達")] = ("朋友", "MyMemory 在线翻译")
w._render("友達", record=True)
pump(8)
print("日语词条详情前 120 字 =", repr(w.detail.toPlainText()[:120]))
shot("ja_word")

# 制造一次跳转，让词头出现「↩ 返回」胶囊
w._render("水", record=True)
pump(6)
print("nav_stack =", w._nav_stack)
shot("ja_word_back")
w._nav_back()
pump(4)

# ------------------------------------------------------ ④ 中文反查（注入缓存）
w._cn_fr_cache[("ja", "朋友")] = ("友達", "MyMemory 在线翻译")
for _ in range(3):
    w._cn_fr_req += 1
w._last_query = "朋友"
w._search_cn_foreign("朋友")
pump(10)
print("反查 hint =", repr(w.list_hint.text()))
print("反查命中数 =", w.result_list.count())
shot("ja_reverse")

# ------------------------------------------------------ ③ 翻译对话框（日语）
dlg = A.TranslateDialog(w, "ja")
dlg.resize(640, 600)
print("对话框标题 =", repr(dlg.windowTitle()))
print("方向说明   =", repr(dlg.dir_hint.text()))
dlg.in_edit.setPlainText("今天天气很好")
dlg._do_translate()
import time
t0 = time.time()
while time.time() - t0 < 10:
    qapp.processEvents()
    if not dlg._busy:
        break
    time.sleep(0.05)
print("翻译状态 =", repr(dlg.status.text()))
print("译文     =", repr(dlg.out_view.toPlainText()[:80]))
dlg.show()
pump(8)
dlg.grab().save(r"D:\Dictionary\build\_shot_trans_ja.png")
print("saved _shot_trans_ja.png")

print("DONE")
sys.stdout.flush()
sys.exit(0)
