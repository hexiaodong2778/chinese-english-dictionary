"""
生成程序图标 (make_icon.py)
============================
设计思路：一眼看出是「查单词」软件
  · 主体：一本摊开的书（字典意象）
  · 中缝：书脊折线
  · 点睛：一枚红色「典」字印章
  · 配一条放大镜轮廓，暗示「查」

输出多尺寸 .ico（16/24/32/48/64/128/256），兼容 Windows 任务栏与资源管理器。
"""
import os
import sys
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

OUT = r"D:\Dictionary\build\app_icon.ico"
OUT_PNG = r"D:\Dictionary\build\app_icon.png"

# 配色（与主程序一致）
PAPER      = (251, 250, 247, 255)
PAPER_EDGE = (232, 228, 218, 255)
INK        = (31, 36, 48, 255)
SEAL       = (179, 53, 44, 255)
SEAL_DARK  = (150, 40, 33, 255)
GOLD       = (176, 141, 79, 255)

S = 1024  # 先大尺寸绘制，再缩放


def rounded(draw, box, r, fill=None, outline=None, width=1):
    draw.rounded_rectangle(box, radius=r, fill=fill, outline=outline, width=width)


def load_font(size, bold=True):
    """找一个可用中文字体。"""
    cands = [
        r"C:\Windows\Fonts\msyhbd.ttc",
        r"C:\Windows\Fonts\msyh.ttc",
        r"C:\Windows\Fonts\simhei.ttf",
        r"C:\Windows\Fonts\simsun.ttc",
    ]
    for c in cands:
        if os.path.exists(c):
            try:
                return ImageFont.truetype(c, size)
            except Exception:
                continue
    return ImageFont.load_default()


def draw_micro():
    """微型图标（16/24px 专用）。

    16px 下任何书本细节都会糊掉，唯一可行的策略是「一个符号 + 一个汉字」：
      · 整块红底圆角方块（印章意象，颜色先立住）
      · 中间一个白色「典」字，尽可能占满
    这样即使 16px 也能一眼看出是「中文词典」。
    """
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    m = int(S * 0.02)
    rounded(d, (m, m, S - m, S - m), int(S * 0.19), fill=SEAL)

    # 白色「典」字，占满内部
    fs = int(S * 0.74)
    font = load_font(fs)
    txt = "典"
    bb = d.textbbox((0, 0), txt, font=font)
    tw, th = bb[2] - bb[0], bb[3] - bb[1]
    d.text((S / 2 - tw / 2 - bb[0], S / 2 - th / 2 - bb[1]), txt,
           font=font, fill=(255, 255, 255, 255))
    return img


def draw_icon(small=False):
    """绘制图标。small=True 时输出极简版（小尺寸专用，去掉细节只留剪影）。"""
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    # ---------- 底板：圆角方形，书封质感 ----------
    if small:
        # 小尺寸：底板铺满且边框加粗，避免 16px 下边缘糊成一团
        m = int(S * 0.025)
        rounded(d, (m, m, S - m, S - m), int(S * 0.20), fill=PAPER,
                outline=INK, width=max(3, int(S * 0.022)))
    else:
        m = int(S * 0.045)
        rounded(d, (m, m, S - m, S - m), int(S * 0.22), fill=PAPER,
                outline=PAPER_EDGE, width=max(2, int(S * 0.008)))

    if not small:
        # 顶部细线（书页顶边暗示）
        d.line((int(S * 0.20), int(S * 0.20), S - int(S * 0.20), int(S * 0.20)),
               fill=PAPER_EDGE, width=max(2, int(S * 0.006)))

    # ---------- 摊开的书 ----------
    cx = S // 2
    if small:
        # 小尺寸：书本整体上移收窄，把右下角让给印章
        top = int(S * 0.255)
        bot = int(S * 0.665)
        half = int(S * 0.270)
        curve = int(S * 0.058)
    else:
        top = int(S * 0.265)
        bot = int(S * 0.720)
        half = int(S * 0.285)
        curve = int(S * 0.052)

    left_page = [
        (cx, top),
        (cx - half * 0.55, top - curve * 0.55),
        (cx - half, top + curve * 0.30),
        (cx - half, bot),
        (cx - half * 0.55, bot - curve * 0.60),
        (cx, bot),
    ]
    right_page = [
        (cx, top),
        (cx + half * 0.55, top - curve * 0.55),
        (cx + half, top + curve * 0.30),
        (cx + half, bot),
        (cx + half * 0.55, bot - curve * 0.60),
        (cx, bot),
    ]
    lw = max(3, int(S * 0.017)) if not small else max(4, int(S * 0.030))
    d.polygon(left_page, fill=(255, 255, 255, 255))
    d.line(left_page + [left_page[0]], fill=INK, width=lw, joint="curve")
    d.polygon(right_page, fill=(255, 255, 255, 255))
    d.line(right_page + [right_page[0]], fill=INK, width=lw, joint="curve")

    # 中缝
    d.line((cx, top + curve * 0.2, cx, bot), fill=INK, width=lw)

    if not small:
        # ---------- 页内文字线（暗示词条）----------
        tl = max(2, int(S * 0.010))
        for i in range(3):
            yy = int(top + (bot - top) * (0.30 + i * 0.17))
            d.line((cx - half * 0.72, yy, cx - half * 0.16, yy),
                   fill=(150, 156, 170, 255), width=tl)
            d.line((cx + half * 0.16, yy, cx + half * 0.72, yy),
                   fill=(150, 156, 170, 255), width=tl)
    else:
        # 小尺寸：只画 2 条粗文字线，保证 16px 下仍是「有字的书」
        tl = max(3, int(S * 0.026))
        for i in range(2):
            yy = int(top + (bot - top) * (0.36 + i * 0.26))
            d.line((cx - half * 0.66, yy, cx - half * 0.22, yy),
                   fill=(120, 128, 145, 255), width=tl)
            d.line((cx + half * 0.22, yy, cx + half * 0.66, yy),
                   fill=(120, 128, 145, 255), width=tl)

    # ---------- 印章：右下角红章 ----------
    if small:
        # 小尺寸：印章放大、右移下移，红底白字对比最强
        seal_r = int(S * 0.230)
        sx = int(S * 0.752)
        sy = int(S * 0.748)
        rounded(d, (sx - seal_r, sy - seal_r, sx + seal_r, sy + seal_r),
                int(seal_r * 0.24), fill=SEAL)
        fs = int(seal_r * 1.55)
        font = load_font(fs)
        txt = "典"
        bb = d.textbbox((0, 0), txt, font=font)
        tw, th = bb[2] - bb[0], bb[3] - bb[1]
        d.text((sx - tw / 2 - bb[0], sy - th / 2 - bb[1]), txt,
               font=font, fill=(255, 255, 255, 255))
        # 小尺寸：放大镜只留一个金色圆环，作「查」的极简符号
        gx, gy = int(S * 0.235), int(S * 0.212)
        gr = int(S * 0.105)
        glw = max(5, int(S * 0.030))
        d.ellipse((gx - gr, gy - gr, gx + gr, gy + gr),
                  outline=GOLD, width=glw)
        hx1 = gx - gr * 0.66
        hy1 = gy + gr * 0.66
        hx2 = gx - gr * 1.50
        hy2 = gy + gr * 1.50
        d.line((hx1, hy1, hx2, hy2), fill=GOLD, width=glw)
        return img

    seal_r = int(S * 0.178)
    sx = int(S * 0.760)
    sy = int(S * 0.755)
    rounded(d, (sx - seal_r, sy - seal_r, sx + seal_r, sy + seal_r),
            int(seal_r * 0.30), fill=SEAL)
    # 内描边
    inset = int(seal_r * 0.15)
    rounded(d, (sx - seal_r + inset, sy - seal_r + inset,
                sx + seal_r - inset, sy + seal_r - inset),
            int(seal_r * 0.20), outline=(255, 255, 255, 190),
            width=max(2, int(S * 0.007)))

    # 印章文字
    fs = int(seal_r * 1.28)
    font = load_font(fs)
    txt = "典"
    bb = d.textbbox((0, 0), txt, font=font)
    tw, th = bb[2] - bb[0], bb[3] - bb[1]
    d.text((sx - tw / 2 - bb[0], sy - th / 2 - bb[1]), txt,
           font=font, fill=(255, 255, 255, 255))

    # ---------- 左上角放大镜（暗示「查」）----------
    gx, gy = int(S * 0.238), int(S * 0.252)
    gr = int(S * 0.098)
    glw = max(3, int(S * 0.018))
    d.ellipse((gx - gr, gy - gr, gx + gr, gy + gr),
              outline=GOLD, width=glw)
    # 镜片淡色填充
    d.ellipse((gx - gr + glw, gy - gr + glw, gx + gr - glw, gy + gr - glw),
              fill=(255, 255, 255, 205))
    # 手柄（斜向左下，避免压住书本主体）
    hx1 = gx - gr * 0.62
    hy1 = gy + gr * 0.62
    hx2 = gx - gr * 1.42
    hy2 = gy + gr * 1.42
    d.line((hx1, hy1, hx2, hy2), fill=GOLD, width=glw)

    return img


def build_ico():
    """构建多尺寸 ico：所有尺寸统一用完整版（书本 + 放大镜 + 典章）。"""
    big = draw_icon(small=False)
    sml = draw_icon(small=True)
    mic = draw_micro()
    from ico_writer import write_ico
    frames = [(s, big) for s in (16, 24, 32, 48, 64, 128, 256)]
    frames = [(s, im.resize((s, s), Image.LANCZOS)) for s, im in frames]
    n = write_ico(OUT, frames)
    print("ico saved with sizes:", [s for s, _ in frames], "frames:", n)
    return big, sml, mic


def main():
    big = draw_icon(small=False)
    sml = draw_icon(small=True)
    mic = draw_micro()
    # 主 PNG 用完整版（书本 + 放大镜 + 印章），代表软件形象
    big.save(OUT_PNG, "PNG")
    big.resize((256, 256), Image.LANCZOS).save(
        r"D:\Dictionary\build\app_icon_256.png", "PNG")
    sml.resize((256, 256), Image.LANCZOS).save(
        r"D:\Dictionary\build\app_icon_small_256.png", "PNG")
    mic.resize((256, 256), Image.LANCZOS).save(
        r"D:\Dictionary\build\app_icon_micro_256.png", "PNG")

    # 真正写入多尺寸 ico：**所有尺寸统一为完整版**
    #   （摊开的书 + 金色放大镜 + 右下角红色「典」印章）
    #
    # 为什么统一用完整版：
    #   用户明确要求「所有图标都要原来那个书本放大镜和典字都有的那个」。
    #   此前试过小尺寸只留印章版的混合策略，用户看到桌面上是个「大典」，
    #   并不是想要的效果。因此 16~256 七帧全部使用完整版。
    #   每帧都从 256px 的 big 母图 LANCZOS 缩放，保证外观完全一致。
    #
    # 注意：必须用手工 ICO 封装。PIL 的 save(format="ICO") 会无视这些
    #       预渲染帧，改用基准图重采样，导致 16px 变成缩糊的书本。
    from ico_writer import write_ico

    frames = [(s, big) for s in (16, 24, 32, 48, 64, 128, 256)]
    frames = [(s, im.resize((s, s), Image.LANCZOS)) for s, im in frames]
    n = write_ico(OUT, frames)
    print("png ->", OUT_PNG, os.path.getsize(OUT_PNG))
    print("ico ->", OUT, n)
    print("sizes:", [s for s, _ in frames])


if __name__ == "__main__":
    main()
