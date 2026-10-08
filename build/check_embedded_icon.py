# -*- coding: utf-8 -*-
"""在 exe 里定位内嵌的 ICO 整块数据（PyInstaller 原样嵌入 app_icon.ico），
解出各帧并与 build/app_icon.ico 逐帧比对，确认嵌入的确实是我们生成的图标。
"""
import hashlib
import io
import os
import struct

EXE = r"D:\Dictionary\build\dist\查单词.exe"
ICO = r"D:\Dictionary\build\app_icon.ico"
blob = open(EXE, "rb").read()
ico = open(ICO, "rb").read()
out = []


def parse(data, tag):
    if len(data) < 6:
        return None
    res, typ, cnt = struct.unpack_from("<HHH", data, 0)
    if res != 0 or typ != 1 or cnt == 0 or cnt > 64:
        return None
    frames = []
    pos = 6 + cnt * 16
    if pos > len(data):
        return None
    for i in range(cnt):
        w, h, nc, r, pl, bpp, size, offset = struct.unpack_from(
            "<BBBBHHII", data, 6 + i * 16)
        if offset + size > len(data) or size == 0:
            return None
        frames.append((w or 256, (h or 256), bpp,
                       data[offset:offset + size]))
    return frames


# 源 ico 帧
src = parse(ico, "src")
out.append(f"源 ico: {len(ico):,} 字节, {len(src)} 帧")
for w, h, bpp, pl in src:
    out.append(f"    {w:>3}x{h:<3} {bpp}bpp {len(pl):>7,} 字节  "
               f"sha={hashlib.sha256(pl).hexdigest()[:12]}")

# 在 exe 中找工作副本：搜 ICO 头 + 帧数
needle = ico[:6 + len(src) * 16]
idx = blob.find(needle)
out.append("")
out.append(f"exe 内查找 ico 头 {needle[:6].hex()} ...")
if idx < 0:
    out.append("  未找到完整 ico 头，改按 PNG 签名逐个定位")
    found = []
    p = 0
    while True:
        p = blob.find(b"\x89PNG\r\n\x1a\n", p)
        if p < 0:
            break
        try:
            im = __import__("PIL.Image", fromlist=["Image"]).open(
                io.BytesIO(blob[p:p + 400000]))
            if im.width == im.height and im.width in (16, 24, 32, 48, 64, 128, 256):
                found.append((p, im.width))
        except Exception:
            pass
        p += 8
    out.append(f"  找到 {len(found)} 个方形 PNG 帧")
    for off, w in found[:16]:
        out.append(f"    off=0x{off:X} {w}px")
else:
    out.append(f"  找到完整 ico 块 @ 0x{idx:X}")
    emb = parse(blob[idx:idx + len(ico)], "emb")
    if emb:
        out.append(f"  内嵌 {len(emb)} 帧")
        same = True
        for i, ((w, h, bpp, a), (w2, h2, bpp2, b)) in enumerate(zip(src, emb)):
            eq = a == b
            same = same and eq
            out.append(f"    {w:>3}px  源{len(a):>7,}  嵌{len(b):>7,}  "
                       f"{'一致' if eq else '不一致'}")
        out.append("")
        out.append("结论：" + ("exe 内嵌图标与源文件逐帧完全一致。"
                              if same else "存在差异，需排查！"))

# 说明每帧设计：小尺寸应是红底（角像素红），大尺寸应是透明底
out.append("")
out.append("各帧设计判定（角像素）：")
from PIL import Image
for w, h, bpp, pl in src:
    im = Image.open(io.BytesIO(pl)).convert("RGBA")
    px = im.resize((64, 64), Image.LANCZOS).load()
    c = px[3, 3]
    if c[3] < 40:
        kind = "透明底 → 书本版"
    elif c[0] > 120 and c[1] < 100 and c[2] < 100:
        kind = "红底 → 印章版"
    else:
        kind = f"其他 {c}"
    out.append(f"    {w:>3}px  corner={c}  {kind}")

open(r"D:\Dictionary\build\_embed.txt", "w", encoding="utf-8").write("\n".join(out))
print("ok")
