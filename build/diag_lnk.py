# -*- coding: utf-8 -*-
"""诊断 .lnk：逐字段解析，找出 Shell 不认的原因。

同时检查 .lnk.bak（旧版）作对比，看差异在哪。
"""
import os
import struct

LNK = os.path.join(os.environ["USERPROFILE"], "Desktop", "查单词.lnk")
LNK_BAK = LNK + ".bak"
LNK_BAK2 = LNK + ".bak2"

out = []


def look(path, tag):
    if not os.path.exists(path):
        out.append(f"\n### {tag}: 不存在 {path}")
        return
    d = open(path, "rb").read()
    out.append(f"\n### {tag}  {len(d)} 字节  {path}")
    hs = struct.unpack_from("<I", d, 0)[0]
    clsid = d[4:20].hex()
    flags = struct.unpack_from("<I", d, 0x14)[0]
    attr = struct.unpack_from("<I", d, 0x18)[0]
    out.append(f"  HeaderSize={hs}  CLSID={clsid}")
    out.append(f"  flags=0x{flags:08X}  attrs=0x{attr:08X}")
    names = [(0x1, "HasLinkTargetIDList"), (0x2, "HasLinkInfo"),
             (0x4, "HasName"), (0x8, "HasRelativePath"),
             (0x10, "HasWorkingDir"), (0x20, "HasArguments"),
             (0x40, "HasIconLocation"), (0x80, "IsUnicode"),
             (0x1000, "ForceNoLinkInfo"), (0x2000, "HasExpString")]
    for bit, nm in names:
        if flags & bit:
            out.append(f"    + {nm}")
    if hs != 0x4C:
        out.append(f"  !! HeaderSize 应为 0x4C")

    off = hs
    # IDList
    if flags & 0x1:
        idsize = struct.unpack_from("<H", d, off)[0]
        out.append(f"  IDList: size={idsize} @0x{off:X}")
        seg = d[off + 2:off + 2 + idsize]
        out.append(f"    seg[:40]={seg[:40].hex()}")
        # 逐项
        p = 0
        n = 0
        while p + 2 <= len(seg):
            isz = struct.unpack_from("<H", seg, p)[0]
            if isz == 0:
                out.append(f"    [终结符] @{p}")
                break
            out.append(f"    item{n}: size={isz} type=0x{seg[p+2]:02X} "
                       f"data={seg[p+3:p+isz][:24]!r}")
            p += isz
            n += 1
            if n > 12:
                out.append("    ...")
                break
        off += 2 + idsize
    else:
        out.append("  IDList: 无")

    # LinkInfo
    if flags & 0x2:
        li_size = struct.unpack_from("<I", d, off)[0]
        li_hdr = struct.unpack_from("<I", d, off + 4)[0]
        li_flags = struct.unpack_from("<I", d, off + 8)[0]
        out.append(f"  LinkInfo: size={li_size} hdr={li_hdr} "
                   f"flags=0x{li_flags:08X}")
        if off + li_size > len(d):
            out.append("    !! LinkInfo 越界")
            return
        # 尝试读本地路径
        lbp = struct.unpack_from("<I", d, off + 16)[0]
        if lbp:
            p = off + lbp
            e = d.find(b"\x00", p)
            out.append(f"    LocalBasePath={d[p:e]!r}")
        off += li_size
    else:
        out.append("  LinkInfo: 无")

    # StringData
    uni = bool(flags & 0x80)
    out.append(f"  StringData (unicode={uni}) @0x{off:X}, 余 {len(d)-off} 字节")

    def rd(o):
        c = struct.unpack_from("<H", d, o)[0]
        o += 2
        if uni:
            s = d[o:o + c * 2].decode("utf-16-le", "replace")
            return s, o + c * 2
        s = d[o:o + c].decode("latin1", "replace")
        return s, o + c

    for bit, nm in ((0x4, "NAME"), (0x8, "RELPATH"), (0x10, "WORKDIR"),
                    (0x20, "ARGS"), (0x40, "ICON")):
        if flags & bit:
            if off + 2 > len(d):
                out.append(f"    {nm}: !! 越界")
                break
            s, off = rd(off)
            out.append(f"    {nm} = {s!r}")
    out.append(f"  尾部: {d[off:off+16].hex()}")


look(LNK_BAK2, "旧版（仅 LinkInfo，ExtractIconEx=0）")
look(LNK, "新版（LinkInfo + IDList）")
look(LNK_BAK, "最早备份")

open(r"D:\Dictionary\build\_lnkdiag.txt", "w", encoding="utf-8").write("\n".join(out))
print("ok")
