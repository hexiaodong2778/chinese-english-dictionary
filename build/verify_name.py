# -*- coding: utf-8 -*-
"""书名字标（Wordmark）视觉验证 —— 渲染成图片，按绘制代码的真实坐标检查像素。

── 为什么重写（2026-09-17）──
原版读的是 `wm._tx` / `wm._name_w` 这类**实例属性**，那是旧版实现留下的。
后来字标改成在 paintEvent 里直接按固定坐标绘制（更简单、少一层状态），
那些属性就不存在了 —— 测试挂在 AttributeError 上，而**产品是好的**。

教训一：测试不该依赖私有属性的存在。要验证「画得对不对」，
        直接把它渲染出来看像素，比检查内部变量名更稳、也更接近真实。

教训二（重写后又踩的坑）：不要用「同色 == 精确 RGB」来数像素。
        字是抗锯齿渲染的，笔画边缘全是混合色，中心也不一定命中纯色；
        而背景 PAPER(#fbfaf7) 本身也不是纯白。第一版因此数出 0。
        正确做法：在**绘制代码自己写死的坐标**上取点，判断「有色差」，
        再看色相偏红还是偏墨 —— 这与实现解耦，但仍在验证真实产出。
"""
import io
import os
import sys

sys.path.insert(0, r"D:\Dictionary\build")
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.chdir(r"D:\Dictionary\build")

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QImage, QColor
from PySide6.QtCore import QPoint

qapp = QApplication(sys.argv)
import app as A

OUT = r"D:\Dictionary\build\_wordmark_render.png"
W, H = 680, 66

PASS, FAIL = [], []


def chk(name, cond, detail=""):
    (PASS if cond else FAIL).append(
        name + ("  " + str(detail) if detail else ""))


def within(rgb, target, tol):
    """rgb 与 target 各通道差都 <= tol。"""
    r, g, b = rgb
    tr, tg, tb = target
    return abs(r - tr) <= tol and abs(g - tg) <= tol and abs(b - tb) <= tol


# ── 渲染 ────────────────────────────────────────────────────────────────
w = A.Wordmark()
w.resize(W, H)
img = QImage(W, H, QImage.Format_ARGB32)
img.fill(QColor(A.PAPER))
w.render(img, QPoint(0, 0))          # offscreen 下无需 show()，实测可正常触发 paintEvent
img.save(OUT)

chk("词标构造成功", isinstance(w, A.Wordmark))
chk("名词取自 APP_NAME", w.name == A.APP_NAME, w.name)
chk("副标题取自 APP_SUBTITLE", w.subtitle == A.APP_SUBTITLE, w.subtitle)
chk("字号取自 NAME_PT", w.NAME_PT == 17, w.NAME_PT)
chk("高度固定为 66", w.height() == 66, w.height())
chk("渲染图已落盘", os.path.exists(OUT), OUT)

paper = QColor(A.PAPER).getRgb()[:3]
seal = QColor(A.SEAL).getRgb()[:3]
ink = QColor(A.INK).getRgb()[:3]


def rgb_at(x, y):
    c = QColor(img.pixel(x, y))
    return (c.red(), c.green(), c.blue())


# ── 1. 书本意象（印章红）：绘制代码里 bx,by,bw,bh = 14,18,34,30 ─────────
# 在书页外框的描边上采样。描边 1.6px，向外多探索几像素以免差一像素落空。
book_hits = 0
book_samples = 0
for x in range(12, 50):
    for y in range(16, 50):
        book_samples += 1
        if within(rgb_at(x, y), seal, 60):
            book_hits += 1
chk("书本意象用印章红绘制", book_hits > 20,
    "%d 个偏红采样点 / %d" % (book_hits, book_samples))

# ── 2. 标题墨字：drawText(58, 34, name)，四字 17pt 粗体 ─────────────────
title_hits = 0
title_samples = 0
for x in range(56, 200):
    for y in range(16, 38):
        title_samples += 1
        if within(rgb_at(x, y), ink, 70):
            title_hits += 1
chk("标题用正文墨色绘制", title_hits > 40,
    "%d 个墨色采样点 / %d" % (title_hits, title_samples))

# ── 3. 右侧装饰线：drawLine(200, 33, w-24, 33)，LINE 色 ──────────────────
line = QColor(A.LINE).getRgb()[:3]
rule_hits = sum(1 for x in range(210, W - 30, 3)
                if within(rgb_at(x, 33), line, 60))
chk("右侧装饰横线已绘制", rule_hits > 50,
    "%d / %d 个采样点命中" % (rule_hits, len(range(210, W - 30, 3))))

# ── 4. 装饰线末端小红点：drawEllipse(QPoint(w-20, 33), 3, 3) ───────────
dot_hits = sum(1 for dy in range(-2, 3) for dx in range(-2, 3)
               if within(rgb_at(W - 20 + dx, 33 + dy), seal, 70))
chk("装饰线末端有红点", dot_hits >= 9, "%d / 25 个像素偏红" % dot_hits)

# ── 5. 整体不是空白 ────────────────────────────────────────────────────
non_paper = sum(1 for y in range(0, H, 2) for x in range(0, W, 2)
                if not within(rgb_at(x, y), paper, 4))
chk("画面不是空白", non_paper > 200, "%d 个非纸色采样点" % non_paper)

# ── 6. 标题字主要在左侧（装饰线从 200 起算） ───────────────────────────
ink_left = sum(1 for y in range(16, 38) for x in range(56, 200)
               if within(rgb_at(x, y), ink, 70))
ink_right = sum(1 for y in range(16, 38) for x in range(210, W - 10)
                if within(rgb_at(x, y), ink, 70))
chk("标题字集中在左侧", ink_left > ink_right * 3,
    "左 %d / 右 %d" % (ink_left, ink_right))

# ── 7. 重复渲染稳定（无随机性） ─────────────────────────────────────────
img2 = QImage(W, H, QImage.Format_ARGB32)
img2.fill(QColor(A.PAPER))
w.render(img2, QPoint(0, 0))
chk("重复渲染结果一致", img == img2)

# ── 8. 尺寸变化不崩（装饰线随宽度伸展） ─────────────────────────────────
w2 = A.Wordmark()
w2.resize(980, 66)
img3 = QImage(980, 66, QImage.Format_ARGB32)
img3.fill(QColor(A.PAPER))
w2.render(img3, QPoint(0, 0))
c = QColor(img3.pixel(900, 33)).getRgb()[:3]
chk("加宽后装饰线跟随延伸到 900px 处", within(c, line, 70),
    "x=900 处颜色 %s" % (c,))

# ── 9. 副标题确实画在标题下方 ───────────────────────────────────────────
faint = QColor(A.INK_FAINT).getRgb()[:3]
sub_hits = sum(1 for x in range(58, 210) for y in range(40, 56)
               if within(rgb_at(x, y), faint, 70))
chk("副标题绘制在标题下方", sub_hits > 30, "%d 个采样点" % sub_hits)

print("PASS=%d FAIL=%d" % (len(PASS), len(FAIL)))
for x in PASS:
    print("  PASS ", x)
for x in FAIL:
    print("  FAIL ", x)
sys.exit(1 if FAIL else 0)
