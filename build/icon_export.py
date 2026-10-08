# -*- coding: utf-8 -*-
"""把 ico 里每一帧导出成 PNG，方便目视核对各尺寸渲染效果。"""
import io
import os
import struct
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

path = r"D:\Dictionary\build\app_icon.ico"
outdir = r"D:\Dictionary\build\icon_frames"
os.makedirs(outdir, exist_ok=True)

data = open(path, "rb").read()
res, itype, count = struct.unpack_from("<HHH", data, 0)
print(f"frames={count}")

# 拼一张对比图：每个尺寸放大到同一高度，直观比较
from PIL import Image

imgs = []
for i in range(count):
    off = 6 + i * 16
    w, h, ncol, rsv, planes, bpp, size, doff = struct.unpack_from(
        "<BBBBHHII", data, off)
    W = w or 256
    blob = data[doff:doff + size]
    p = os.path.join(outdir, f"frame_{W}.png")
    with open(p, "wb") as f:
        f.write(blob)
    im = Image.open(io.BytesIO(blob)).convert("RGBA")
    print(f"  {W}x{W}  -> {p}  ({im.size})")
    imgs.append((W, im))

# 拼版：等比放大到 256 高，横向排列
tiles = [(W, im.resize((256, 256), Image.NEAREST)) for W, im in imgs]
sheet = Image.new("RGBA", (256 * len(tiles), 256), (255, 255, 255, 255))
for i, (W, im) in enumerate(tiles):
    sheet.paste(im, (i * 256, 0), im)
sheet.save(r"D:\Dictionary\build\icon_frames_sheet.png", "PNG")
print("sheet ->", r"D:\Dictionary\build\icon_frames_sheet.png")
