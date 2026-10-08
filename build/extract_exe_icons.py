# -*- coding: utf-8 -*-
"""提取 exe 内嵌的各尺寸帧，确认小尺寸是印章、大尺寸是书本。"""
import io
import os
import struct
import sys

EXE = r"D:\Dictionary\build\dist\查单词.exe"
OUTDIR = r"D:\Dictionary\build\_exeframes"
os.makedirs(OUTDIR, exist_ok=True)
blob = open(EXE, "rb").read()
out = [f"exe {len(blob):,} 字节"]

# --- 手工解析 PE 资源目录，取 RT_ICON(3) ---
e_lfanew = struct.unpack_from("<I", blob, 0x3C)[0]
assert blob[e_lfanew:e_lfanew + 4] == b"PE\0\0"
coff = e_lfanew + 4
nsec = struct.unpack_from("<H", blob, coff + 2)[0]
opt_size = struct.unpack_from("<H", blob, coff + 16)[0]
opt = coff + 20
magic = struct.unpack_from("<H", blob, opt)[0]
dd = opt + (112 if magic == 0x20B else 96)
rsrc_rva, rsrc_sz = struct.unpack_from("<II", blob, dd + 2 * 8)

sec = opt + opt_size
secs = []
for i in range(nsec):
    o = sec + i * 40
    name = blob[o:o + 8].rstrip(b"\0")
    vsz, va, rsz, ra = struct.unpack_from("<IIII", blob, o + 8)
    secs.append((name, va, vsz, ra, rsz))


def rva2off(rva):
    for _n, va, vsz, ra, _rsz in secs:
        if va <= rva < va + max(vsz, 1) + 0x1000:
            return ra + (rva - va)
    return None


base = rva2off(rsrc_rva)
out.append(f"资源段 rva=0x{rsrc_rva:X} sz={rsrc_sz:,} -> off=0x{base:X}")


def walk(off, depth, path):
    nnamed, nid = struct.unpack_from("<HH", blob, off + 12)
    total = nnamed + nid
    ents = []
    for i in range(total):
        eo = off + 16 + i * 8
        nid_v, dataoff = struct.unpack_from("<II", blob, eo)
        if dataoff & 0x80000000:
            ents.append((nid_v & 0xFFFF, dataoff & 0x7FFFFFFF, True))
        else:
            ents.append((nid_v & 0xFFFF, dataoff & 0x7FFFFFFF, False))
    for nid_v, sub, is_dir in ents:
        if depth == 0 and nid_v != 3:
            continue
        p = path + [nid_v]
        if is_dir:
            walk(base + sub, depth + 1, p)
        else:
            do = base + sub
            rva, size = struct.unpack_from("<II", blob, do)
            foff = rva2off(rva)
            payload = blob[foff:foff + size]
            if depth == 2 and len(path) >= 2:
                px = path[2] if len(path) > 2 else 0
                h = px or 256
                name = os.path.join(OUTDIR, f"exe_{h:03d}.png")
                open(name, "wb").write(payload)
                out.append(f"  帧 id={px or 256} ({h}px) {size:,} 字节 -> {os.path.basename(name)}")


walk(base, 0, [])
open(r"D:\Dictionary\build\_exeframes.txt", "w", encoding="utf-8").write("\n".join(out))
print("ok")
