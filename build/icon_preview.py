# -*- coding: utf-8 -*-
"""把 app_icon.ico 的 7 个尺寸帧拼成一张预览图，方便肉眼确认外观。
每帧按「原始像素」放在浅灰格子中央，并在下方标注尺寸与红占比。
"""
import io
import struct

from PIL import Image, ImageDraw

ICO = r"D:\Dictionary\build\app_icon.ico"
OUT = r"D:\Dictionary\build\icon_preview.png"

data = open(ICO, "rb").read()
cnt = struct.unpack_from("<H", data, 4)[0]

frames = []
for i in range(cnt):
    w, h, nc, r, pl, bpp, size, offset = struct.unpack_from(
        "<BBBBHHII", data, 6 + i * 16)
    w = w or 256
    im = Image.open(io.BytesIO(data[offset:offset + size])).convert("RGBA")
    frames.append((w, im))

CELL = 300
PAD = 14
LABEL = 26
sheet = Image.new("RGBA", (CELL * 4, (CELL + LABEL) * 2),
                  (238, 240, 243, 255))
dr = ImageDraw.Draw(sheet)

for i, (size, im) in enumerate(frames):
    col, row = i % 4, i // 4
    x0 = col * CELL
    y0 = row * (CELL + LABEL)

    # 棋盘格底，便于看清透明区域
    for yy in range(PAD, CELL - PAD, 16):
        for xx in range(PAD, CELL - PAD, 16):
            c = (252, 252, 253) if ((xx // 16 + yy // 16) % 2) else (232, 234, 238)
            dr.rectangle([x0 + xx, y0 + yy, x0 + xx + 15, y0 + yy + 15], fill=c)

    # 放大展示：小于 128 的放大到能看清轮廓（最近邻，看真实像素）
    show = im if size >= 128 else im.resize((size * 2, size * 2), Image.NEAREST)
    px = x0 + (CELL - show.width) // 2
    py = y0 + PAD + (CELL - PAD * 2 - show.height) // 2
    sheet.alpha_composite(show, (px, max(y0 + PAD, py)))

    # 红占比
    small = im.resize((64, 64), Image.LANCZOS)
    p = small.load()
    op = rd = 0
    for yy in range(64):
        for xx in range(64):
            cc = p[xx, yy]
            if cc[3] < 128:
                continue
            op += 1
            if cc[0] > 120 and cc[0] - cc[1] > 40 and cc[0] - cc[2] > 40:
                rd += 1
    ratio = rd / op * 100 if op else 0
    dr.text((x0 + 10, y0 + CELL + 4),
            f"{size}x{size}px    red {ratio:.0f}%", fill=(40, 44, 52, 255))

sheet.convert("RGB").save(OUT, "PNG")
print("saved", OUT)
