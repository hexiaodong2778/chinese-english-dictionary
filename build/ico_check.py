# -*- coding: utf-8 -*-
"""检查 app_icon.ico 里真实包含哪些尺寸的帧。"""
import io
import struct
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

path = r"D:\Dictionary\build\app_icon.ico"
data = open(path, "rb").read()

res, itype, count = struct.unpack_from("<HHH", data, 0)
print(f"type={itype}  frames={count}  filesize={len(data)}")

for i in range(count):
    off = 6 + i * 16
    w, h, ncol, rsv, planes, bpp, size, offset = struct.unpack_from(
        "<BBBBHHII", data, off)
    W = w or 256
    H = h or 256
    # 用前 8 字节判断该帧是否是 PNG（PNG 签名 89 50 4E 47）
    sig = data[offset:offset + 8]
    kind = "PNG" if sig[:4] == b"\x89PNG" else "BMP"
    print(f"  frame {i}: {W}x{H}  bpp={bpp}  {kind}  {size} bytes")
