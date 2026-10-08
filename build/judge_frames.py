# -*- coding: utf-8 -*-
"""正确判定每帧设计：印章版是「大面积红底」，书本版是「大面积浅色/透明」。

判据：统计不透明像素中，红色像素（R 明显大于 G、B）的占比。
  印章版 -> 红占比很高（>50%）
  书本版 -> 红只占右下角一小块（<20%）
"""
import io
import os
import struct

from PIL import Image

ICO = r"D:\Dictionary\build\app_icon.ico"
ico = open(ICO, "rb").read()
cnt = struct.unpack_from("<H", ico, 4)[0]

out = [f"源 ico {len(ico):,} 字节, {cnt} 帧", ""]
for i in range(cnt):
    w, h, nc, r, pl, bpp, size, offset = struct.unpack_from("<BBBBHHII",
                                                            ico, 6 + i * 16)
    w = w or 256
    im = Image.open(io.BytesIO(ico[offset:offset + size])).convert("RGBA")
    im = im.resize((64, 64), Image.LANCZOS)
    px = im.load()
    opaque = red = white = 0
    for y in range(64):
        for x in range(64):
            c = px[x, y]
            if c[3] < 128:
                continue
            opaque += 1
            if c[0] > 120 and c[0] - c[1] > 40 and c[0] - c[2] > 40:
                red += 1
            elif c[0] > 200 and c[1] > 200 and c[2] > 200:
                white += 1
    # 采样几个关键位置
    center = px[32, 32]
    rp = red / opaque * 100 if opaque else 0
    kind = "印章版（红底白典）" if rp > 50 else "书本版（书+放大镜+章）"
    out.append(f"  {w:>3}px  不透明{opaque:>4}  红占比{rp:5.1f}%  中心{center}  -> {kind}")

out.append("")
out.append("期望：全部 7 帧统一为书本版（书 + 放大镜 + 典章），红占比约 13%")
open(r"D:\Dictionary\build\_design.txt", "w", encoding="utf-8").write("\n".join(out))
print("ok")
