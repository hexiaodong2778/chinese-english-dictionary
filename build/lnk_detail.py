# -*- coding: utf-8 -*-
"""解析 .lnk（Shell Link）二进制，按 MS-SHLLINK 规范逐段走。

关键：LinkInfo 段内还有 VolumeID / LocalBasePath / CommonPathSuffix 等
子结构，直接按固定偏移跳会错位。这里严格按 size 字段递进。
"""
import io
import os
import re
import struct
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")


def u(s):
    return s.decode("latin1", "replace")


def parse(path):
    d = open(path, "rb").read()
    out = {}
    hdr_size, = struct.unpack_from("<I", d, 0)
    flags, = struct.unpack_from("<I", d, 0x14)
    attr, = struct.unpack_from("<I", d, 0x18)
    out["header_size"] = hdr_size
    out["flags"] = f"0x{flags:08X}"
    out["has_target_idlist"] = bool(flags & 0x01)
    out["has_linkinfo"] = bool(flags & 0x02)
    out["has_name"] = bool(flags & 0x04)
    out["has_relpath"] = bool(flags & 0x08)
    out["has_workdir"] = bool(flags & 0x10)
    out["has_args"] = bool(flags & 0x20)
    out["has_iconloc"] = bool(flags & 0x40)
    out["is_unicode"] = bool(flags & 0x80)

    off = hdr_size

    # --- LinkTargetIDList ---
    if out["has_target_idlist"]:
        idsize, = struct.unpack_from("<H", d, off)
        out["_idlist_off"] = off
        out["_idlist_size"] = idsize
        # ItemID 里可能藏着目标路径（尤其是可执行文件）
        seg = d[off + 2:off + 2 + idsize]
        # 提取其中的 ASCII / UTF-16 片段
        frags = []
        for m in re.finditer(rb"[\x20-\x7e]{3,}", seg):
            frags.append(m.group(0).decode("latin1"))
        out["_idlist_frags"] = frags
        off += 2 + idsize

    # --- LinkInfo ---
    if out["has_linkinfo"]:
        li_start = off
        li_size, = struct.unpack_from("<I", d, li_start)
        li_hdr = li_start + 4
        li_hdr_size, = struct.unpack_from("<I", d, li_hdr)
        li_flags, = struct.unpack_from("<I", d, li_hdr + 4)
        vol_id_off, = struct.unpack_from("<I", d, li_hdr + 8)
        local_base_off, = struct.unpack_from("<I", d, li_hdr + 12)
        out["linkinfo_size"] = li_size
        out["linkinfo_flags"] = f"0x{li_flags:08X}"

        base = li_hdr  # 相对基准是 LinkInfo 头起始（含自身 4 字节 size 前的位置）

        # LocalBasePath：从 li_start + local_base_off 开始的 ANSI 字符串
        if local_base_off:
            p = li_start + local_base_off
            end = d.find(b"\x00", p)
            out["local_base_path"] = u(d[p:end])
        # CommonPathSuffix
        if li_size:
            pass
        # Unicode 版本（LinkInfo 里通常还带一个 UTF-16 的 BasePath）
        seg = d[li_start:li_start + li_size]
        uni = []
        for m in re.finditer(rb"(?:[\x20-\x7e]\x00){3,}", seg):
            uni.append(m.group(0).decode("utf-16-le", "replace"))
        out["_linkinfo_unicode"] = uni
        off = li_start + li_size

    # --- StringData 段（按 flags 顺序）---
    def read_strdata(o, unicode_):
        cnt, = struct.unpack_from("<H", d, o)
        o += 2
        if unicode_:
            raw = d[o:o + cnt * 2]
            s = raw.decode("utf-16-le", "replace")
            o += cnt * 2
        else:
            raw = d[o:o + cnt]
            s = u(raw)
            o += cnt
        return s, o

    uni = out["is_unicode"]
    for key, present in (("name", out["has_name"]),
                         ("relpath", out["has_relpath"]),
                         ("workdir", out["has_workdir"]),
                         ("args", out["has_args"])):
        if present:
            s, off = read_strdata(off, uni)
            out[key] = s

    if out["has_iconloc"]:
        s, off = read_strdata(off, uni)
        out["icon_location"] = s

    return out


DESK = os.path.join(os.path.expanduser("~"), "Desktop")
PUBLIC = r"C:\Users\Public\Desktop"

print("=== 桌面快捷方式 ===")
found = []
for dd in (DESK, PUBLIC):
    if os.path.isdir(dd):
        for f in os.listdir(dd):
            if f.lower().endswith(".lnk") and "查单词" in f:
                found.append(os.path.join(dd, f))
if not found:
    print("  （未找到「查单词」快捷方式）")

for lnk in found:
    print(f"\n>>> {lnk}")
    r = parse(lnk)
    for k in ("flags", "has_iconloc", "local_base_path", "name", "relpath",
              "workdir", "args", "icon_location"):
        if k in r:
            print(f"   {k:18} = {r[k]!r}")
    if r.get("_idlist_frags"):
        print(f"   idlist frags       = {r['_idlist_frags'][:6]}")
    if r.get("_linkinfo_unicode"):
        print(f"   linkinfo unicode   = {r['_linkinfo_unicode'][:4]}")
