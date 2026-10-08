# -*- coding: utf-8 -*-
"""把已有 .lnk 的 IconIndex 从 1 改为 0（原地改，不动其它字段）。

exe 只有 1 组图标，正确索引是 0。之前写的是 1，
虽然系统会容错回退到 0，但不严谨 —— 某些场景（如「更改图标」
对话框、第三方文件管理器）可能因此取不到图标。
"""
import os
import struct

LNK = os.path.join(os.environ["USERPROFILE"], "Desktop", "查单词.lnk")
d = bytearray(open(LNK, "rb").read())

old = struct.unpack_from("<i", d, 0x3C)[0]
struct.pack_into("<i", d, 0x3C, 0)
new = struct.unpack_from("<i", d, 0x3C)[0]

open(LNK, "wb").write(bytes(d))
print(f"IconIndex: {old} -> {new}   (文件 {len(d)} 字节)")
