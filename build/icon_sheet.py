# -*- coding: utf-8 -*-
"""生成图标全尺寸对比图 + 验证每帧都是印章版。"""
import os
import struct
import sys

sys.path.insert(0, r"D:\Dictionary\build")
from PIL import Image, ImageDraw

ICO = r"D:\Dictionary\build\app_icon.ico"
blob = open(ICO, "rb").read()
cnt = struct.unpack_from("<H", blob, 4)[0]

frames = []
for i in range(cnt):
    off = 6 + i * 16
    w, h, _nc, _r, _p, _b, size, offset = struct.unpack_from(
        "<BBBBHHII", blob, off)
    w = w or 256
    import io
    im = Image.open(io.BytesIO(blob[offset:offset + size])).convert("RGBA")
    frames.append((w, im))

# 判定：每帧中心区域应是红底/白字，不能是白底（书本版是白底）
out = []
for w, im in frames:
    px = im.resize((64, 64), Image.LANCZOS).load()
    corner = px[4, 4]
    center = px[32, 32]
    out.append(f"  {w:>3}px  角({corner[0]},{corner[1]},{corner[2]})  "
               f"中心({center[0]},{center[1]},{center[2]})")

# 拼对比图：放大到统一高度，横向排列
H = 160
tiles = []
for w, im in frames:
    tiles.append((w, im.resize((H, H), Image.LANCZOS)))
W = sum(H + 26 for _ in tiles) + 30
sheet = Image.new("RGBA", (W, H + 60), (255, 255, 255, 255))
d = ImageDraw.Draw(sheet)
x = 15
for w, t in tiles:
    sheet.paste(t, (x, 22), t)
    d.text((x + H // 2, H + 32), str(w), fill=(40, 40, 40), anchor="mm")
    x += H + 26
sheet.save(r"D:\Dictionary\build\icon_all_sizes.png", "PNG")

open(r"D:\Dictionary\build\_iconsheet.txt", "w", encoding="utf-8").write(
    f"ico {len(blob):,} 字节, {cnt} 帧\n" + "\n".join(out) +
    "\n\n对比图: icon_all_sizes.png")
print("ok")
