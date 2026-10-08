# -*- coding: utf-8 -*-
"""直接解析 PE 文件的资源段，读 exe 内嵌图标的尺寸列表。

不依赖 Win32 API 回调（ctypes 回调签名容易出错），
改为手工解析 PE 结构：DOS 头 -> PE 头 -> 可选头 -> 数据目录[2] ->
资源目录（三层层级：类型 -> 名称 -> 语言），找出 RT_GROUP_ICON(14)。
"""
import io
import os
import struct
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

RT_ICON = 3
RT_GROUP_ICON = 14


def parse(path):
    data = open(path, "rb").read()

    # ---- DOS 头 ----
    if data[:2] != b"MZ":
        raise SystemExit("不是 PE 文件")
    e_lfanew = struct.unpack_from("<I", data, 0x3C)[0]
    if data[e_lfanew:e_lfanew + 4] != b"PE\0\0":
        raise SystemExit("PE 签名不对")
    coff = e_lfanew + 4
    nsec, = struct.unpack_from("<H", data, coff + 2)
    opt_size, = struct.unpack_from("<H", data, coff + 16)
    opt = coff + 20

    magic, = struct.unpack_from("<H", data, opt)
    pe32p = (magic == 0x20B)
    # 数据目录起始偏移：PE32+ 为 opt+112，PE32 为 opt+96
    ddir = opt + (112 if pe32p else 96)
    n_ddir, = struct.unpack_from("<I", data, ddir - 4)

    # 资源目录是第 2 项（index 2）
    rva, rsize = struct.unpack_from("<II", data, ddir + 2 * 8)

    # ---- 节表，做 RVA -> 文件偏移 换算 ----
    sh = opt + opt_size
    sections = []
    for i in range(nsec):
        o = sh + i * 40
        name = data[o:o + 8].rstrip(b"\0").decode("latin1")
        vsize, vaddr, rawsize, rawptr = struct.unpack_from("<IIII", data, o + 8)
        sections.append((vaddr, vsize, rawptr, rawsize, name))

    def rva_to_off(r):
        for vaddr, vsize, rawptr, rawsize, name in sections:
            if vaddr <= r < vaddr + max(vsize, rawsize):
                return rawptr + (r - vaddr)
        return None

    res_off = rva_to_off(rva)
    if res_off is None:
        raise SystemExit("资源段定位失败")

    def read_dir(off, level, path):
        """递归读资源目录。level 0=类型 1=名称 2=语言"""
        out = []
        n_named, n_id = struct.unpack_from("<HH", data, off + 12)
        total = n_named + n_id
        for i in range(total):
            e = off + 16 + i * 8
            name_id, data_off = struct.unpack_from("<II", data, e)
            if data_off & 0x80000000:
                sub = res_off + (data_off & 0x7FFFFFFF)
                out += read_dir(sub, level + 1, path + [(name_id & 0xFFFF)])
            else:
                # 叶子：指向 IMAGE_RESOURCE_DATA_ENTRY
                de = res_off + data_off
                doff, dsize = struct.unpack_from("<II", data, de)
                out.append((path, doff, dsize))
        return out

    entries = read_dir(res_off, 0, [])

    icons = []
    groups = []
    for path, doff, dsize in entries:
        if not path:
            continue
        typ = path[0]
        foff = rva_to_off(doff)
        if foff is None:
            continue
        blob = data[foff:foff + dsize]
        if typ == RT_ICON:
            icons.append((path[1] if len(path) > 1 else 0, dsize, blob))
        elif typ == RT_GROUP_ICON:
            groups.append((path[1] if len(path) > 1 else 0, dsize, blob))
    return icons, groups, len(data)


path = r"D:\Dictionary\build\dist\查单词.exe"
if not os.path.exists(path):
    path = r"D:\Dictionary\查单词.exe"

icons, groups, total = parse(path)
print(f"exe = {path}")
print(f"大小 = {total:,} bytes")
print(f"mtime = {__import__('datetime').datetime.fromtimestamp(os.path.getmtime(path))}")
print(f"\nRT_ICON 图像资源 {len(icons)} 个")
print(f"RT_GROUP_ICON 图标组 {len(groups)} 个\n")

for gid, gsize, blob in groups:
    res, itype, count = struct.unpack_from("<HHH", blob, 0)
    sizes = []
    for i in range(count):
        o = 6 + i * 14
        w, h, ncol, rsv, planes, bpp, nbytes, iid = struct.unpack_from(
            "<BBBBHHIH", blob, o)
        sizes.append(((w or 256), (h or 256), bpp))
    print(f"组 id={gid}: {count} 帧")
    for w, h, bpp in sorted(sizes):
        print(f"    {w}x{h}  bpp={bpp}")
    got = sorted(s[0] for s in sizes)
    exp = [16, 24, 32, 48, 64, 128, 256]
    print(f"  expected {exp}")
    print(f"  got      {got}")
    print("  " + ("MATCH" if got == exp else "MISMATCH"))
