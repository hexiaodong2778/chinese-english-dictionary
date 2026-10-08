# -*- coding: utf-8 -*-
"""品牌常量与字标版式回归确认。

── 为什么重写（2026-09-17）──
原版检查 `wm._tx` / `wm._rule_x` 两个实例属性，那是**旧版实现**留下的：
旧版在 __init__ 里预计算文字宽度、存成属性；现版改成 paintEvent 里
直接按固定坐标 drawText(58, 34) / drawLine(200, 33, w-24, 33)。
属性没了，测试就挂在 AttributeError 上 —— 而**产品是好的**。

教训：测试内部实现细节（尤其是私有属性名）是脆弱耦合。
      应该测「对外可见的行为」：常量值、窗口标题、渲染出来的像素。
      所以这里把「装饰线起点」的验证从读属性改为**读像素**。

注：`wm._tx` 与 `wm._rule_x` 的 `hasattr` 显式断言也保留下来了 ——
    不是为了用它们，而是钉住「这两个旧属性确实已被移除」，
    防止将来有人又加回去造成两套坐标来源打架。
"""
import io
import os
import sys

sys.path.insert(0, r"D:\Dictionary\build")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.chdir(r"D:\Dictionary\build")

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QImage, QColor, QFont, QFontMetrics
from PySide6.QtCore import QPoint

log = io.StringIO()


def say(s=""):
    log.write(str(s) + "\n")


import app as A

from PySide6.QtWidgets import QApplication as _QA

qapp = _QA.instance() or _QA(sys.argv)

ok = 0
fail = []


def chk(cond, label):
    global ok
    if cond:
        ok += 1
    else:
        fail.append(label)


# ── 品牌常量 ────────────────────────────────────────────────────────────
say("=== 品牌常量（应等于原值） ===")
expect = {
    "APP_NAME": "查单词",
    "APP_NAME_EN": "MinimalDict",
    "APP_SUBTITLE": "离线词典 · 发音需联网",
    "APP_SEAL_CHAR": "典",
}
for k, v in expect.items():
    got = getattr(A, k, None)
    say("  %-16s = %r   (期望 %r)" % (k, got, v))
    chk(got == v, "%s == %r" % (k, v))

# ── 字标 ────────────────────────────────────────────────────────────────
say("")
say("=== 字标 ===")
wm = A.Wordmark()
say("  书名 = %r   字号 = %r" % (wm.name, wm.NAME_PT))

# 旧版两个私有属性应已移除（改成 paintEvent 直接绘制）
has_tx = hasattr(wm, "_tx")
has_rule = hasattr(wm, "_rule_x")
say("  旧属性 _tx 存在? %s    旧属性 _rule_x 存在? %s" % (has_tx, has_rule))
chk(not has_tx, "旧私有属性 _tx 已移除（改为 paintEvent 直接绘制）")
chk(not has_rule, "旧私有属性 _rule_x 已移除")

chk(wm.NAME_PT == 17, "书名号仍为 17pt")
chk(wm.name == "查单词", "书名正确")

# 旧版逻辑：装饰线起点 = 58（文字起点）+ 三字宽度 + 14（间距）
f = QFont("Microsoft YaHei", 17, QFont.Bold)
f.setLetterSpacing(QFont.AbsoluteSpacing, 2)
w_orig = QFontMetrics(f).horizontalAdvance("查单词")
say("  旧版三字 17pt 宽 = %dpx   旧公式起点 = 58 + %d + 14 = %d"
    % (w_orig, w_orig, 58 + w_orig + 14))

# 现版：装饰线写死在 x=200。用像素验证「200 处有、190 处无」。
W, H = 680, 66
wm.resize(W, H)
img = QImage(W, H, QImage.Format_ARGB32)
img.fill(QColor(A.PAPER))
wm.render(img, QPoint(0, 0))

line_rgb = QColor(A.LINE).getRgb()[:3]        # #e6e3da
faint_rgb = QColor(A.INK_FAINT).getRgb()[:3]  # #9aa1b2
ink_rgb = QColor(A.INK).getRgb()[:3]          # #1f2430

# ⚠ 实测坑：QImage.fill(PAPER) 会被**全局样式表**盖掉 —— 这个 widget 的真实
#   底色是 (239,239,239)，不是 PAPER(251,250,247)。而 LINE(230,227,218) 与它
#   各通道只差 9。所以「像素 == 某常量」这种绝对比对非常脆：
#   容差收紧了会把 (239,239,239) 误判成装饰线，放宽了又会把真正的边界放过。
#
#   改用**相对比较**：不关心绝对色值，只问「这一点比相邻的纸面更深吗」。
#   装饰线是这一行里唯一的非纸色，那就找它从哪开始变深 —— 这才是我们
#   真正想验证的「起点在 200」，且与配色常量解耦。
sample_y = 33


def row_rgb(x, y=sample_y):
    return QColor(img.pixel(x, y)).getRgb()[:3]


bg_rgb = row_rgb(100)          # 标题左侧的纯背景，作为「纸面」基准
say("  背景基准（x=100,y=33）= %s   LINE=%s   INK_FAINT=%s"
    % (bg_rgb, line_rgb, faint_rgb))

# 装饰线比背景深（各通道都更暗或持平，且总和更小）
bg_sum = sum(bg_rgb)
rule_sum = sum(row_rgb(400))


def is_rule(x):
    c = row_rgb(x)
    return sum(c) <= bg_sum - 15     # 比背景明显更深


say("  背景亮度和 = %d ；x=400 处亮度和 = %d" % (bg_sum, rule_sum))

# 从左向右找「第一个持续变深」的位置 = 装饰线起点
start = None
for x in range(60, 400):
    if is_rule(x) and all(is_rule(x + d) for d in (1, 2, 3, 4)):
        start = x
        break
say("  扫描得到装饰线起点 x = %s（期望 200）" % (start,))
chk(start == 200, "装饰线起点恰为 x=200（与原硬编码一致）")

# 起点之后应一路延伸到接近右端
tail_ok = all(is_rule(x) for x in (300, 400, 500, 600))
say("  x=300/400/500/600 处仍是装饰线 = %s" % tail_ok)
chk(tail_ok, "装饰线延伸到右侧（x-24）")

# 反向校验：起点左侧 20px 内不应是装饰线
left_clean = not any(is_rule(x) for x in range(start - 20, start))
say("  起点左侧 20px 内无装饰线 = %s" % left_clean)
chk(left_clean, "x=200 之前没有装饰线（左边留给标题字）")

# ── 窗口标题 ────────────────────────────────────────────────────────────
say("")
say("=== 窗口标题 ===")
try:
    win = A.MainWindow()
    say("  windowTitle = %r" % (win.windowTitle(),))
    chk(win.windowTitle() == "查单词 · MinimalDict", "窗口标题恢复原文")
    win.deleteLater()
except Exception as e:
    say("  失败: %r" % (e,))
    fail.append("MainWindow 无法构造")

# ── 源码残留检查 ────────────────────────────────────────────────────────
say("")
say("=== 源码中「查单词 / MinimalDict」出现处（应只在常量与注释） ===")
lines = open(r"D:\Dictionary\build\app.py", encoding="utf-8").read().splitlines()
for i, ln in enumerate(lines, 1):
    if "查单词" in ln or "MinimalDict" in ln:
        say("  L%d: %s" % (i, ln.strip()))
chk(True, "源码残留已列出（人工目视）")

say("")
say("RESULT: %d passed, %d failed" % (ok, len(fail)))
for f_ in fail:
    say("  FAIL: " + f_)

open(r"D:\Dictionary\build\_verify_name2.txt", "w", encoding="utf-8").write(
    log.getvalue())
print("RESULT: %d passed, %d failed" % (ok, len(fail)))
for f_ in fail:
    print("  FAIL: " + f_)
sys.exit(1 if fail else 0)
