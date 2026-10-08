# -*- coding: utf-8 -*-
"""手工组装多尺寸 .ico（图标写入）

为什么不用 PIL 的 save(format="ICO")：
    PIL 的 ICO 写出插件只接受一张基准图，然后用它自己重采样出各尺寸帧，
    会完全忽略我们精心绘制的「16px 印章版 / 32px 书本版 / 64px 完整版」。
    实测 16px 帧被替换成了缩糊的书本图。

因此这里直接按 ICO 文件格式手工封装 PNG 负载：
    ICONDIR(6B) + ICONDIRENTRY(16B * n) + 各帧 PNG 数据
Windows 从 Vista 起原生支持 PNG 压缩的 ICO，且能正确取用每个尺寸。
"""
import os
import struct


def write_ico(path, frames):
    """frames: [(size, PIL.Image)]，按尺寸升序。"""
    frames = sorted(frames, key=lambda kv: kv[0])

    # 先把每帧编码成 PNG 字节
    blobs = []
    for size, im in frames:
        tmp = os.path.join(os.environ.get("TEMP", "."), f"_ico_{size}.png")
        im.convert("RGBA").save(tmp, format="PNG", optimize=True)
        with open(tmp, "rb") as f:
            blobs.append(f.read())
        try:
            os.remove(tmp)
        except OSError:
            pass

    n = len(frames)
    # ICONDIR: reserved(2)=0, type(2)=1(icon), count(2)
    header = struct.pack("<HHH", 0, 1, n)

    # 数据区起始偏移 = header + 每个目录项 16 字节
    offset = 6 + 16 * n
    entries = b""
    for (size, _), blob in zip(frames, blobs):
        w = 0 if size >= 256 else size      # 256 用 0 表示
        h = 0 if size >= 256 else size
        entries += struct.pack(
            "<BBBBHHII",
            w, h,          # 宽、高
            0,             # 调色板数（真彩为 0）
            0,             # 保留
            1,             # 色彩平面
            32,            # 位深
            len(blob),     # 数据长度
            offset,        # 数据偏移
        )
        offset += len(blob)

    with open(path, "wb") as f:
        f.write(header)
        f.write(entries)
        for blob in blobs:
            f.write(blob)

    return os.path.getsize(path)
