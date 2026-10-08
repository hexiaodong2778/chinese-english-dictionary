# -*- coding: utf-8 -*-
"""导出当前 ico 各帧，确认「桌面版」到底长什么样。"""
import os
import struct
import sys

sys.path.insert(0, r"D:\Dictionary\build")
from PIL import Image

ICO = r"D:\Dictionary\build\app_icon.ico"
OUTDIR = r"D:\Dictionary\build\_frames"
os.makedirs(OUTDIR, exist_ok=True)

blob = open(ICO, "rb").read()
res, typ, cnt = struct.unpack_from("<HHH", blob, 0)
print(f"ICO: reserved={res} type={typ} count={cnt} size={len(blob)}")

out = [f"ICO 声明 {cnt} 帧，文件 {len(blob):,} 字节", ""]
for i in range(cnt):
    off = 6 + i * 16
    w, h, ncol, rsv, planes, bpp, size, offset = struct.unpack_from(
        "<BBBBHHII", blob, off)
    w = w or 256
    h = h or 256
    payload = blob[offset:offset + size]
    # 判断是 PNG 还是 BMP
    is_png = payload[:8] == b"\x89PNG\r\n\x1a\n"
    kind = "PNG" if is_png else "BMP"
    px = 0
    if is_png:
        try:
            im = Image.open(__import__("io").BytesIO(payload))
            px = im.width
            im.save(os.path.join(OUTDIR, f"frame_{w:03d}.png"))
        except Exception as e:
            kind += f" (err {e})"
    out.append(f"  帧{i}: 声明 {w}x{h}  {bpp}bpp  {size:>7,} 字节  {kind}"
               f"  实际 {px}px")

# 也导出 make_icon 的两种源图供对比
import make_icon
mic = make_icon.draw_micro()
sml = make_icon.draw_icon(small=True)
big = make_icon.draw_icon(small=False)
for name, im in (("micro", mic), ("small", sml), ("big", big)):
    for s in (32, 48, 256):
        im.resize((s, s), Image.LANCZOS).save(
            os.path.join(OUTDIR, f"src_{name}_{s}.png"))

out.append("")
out.append("已导出到 " + OUTDIR)
open(r"D:\Dictionary\build\_frames.txt", "w", encoding="utf-8").write("\n".join(out))
print("ok")
