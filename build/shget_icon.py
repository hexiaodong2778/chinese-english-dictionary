# -*- coding: utf-8 -*-
"""① 读 .lnk 的 ICON_LOCATION / IconIndex 字段
② 若 IconLocation 为空或指向别处，Windows 会用目标 exe 的图标（我们想要的）
③ 直接对 exe 调用 SHGetFileInfo，拿到 Shell 真正会显示的图标并检查颜色
"""
import ctypes
import ctypes.wintypes as wt
import os
import struct

from PIL import Image

LNK = os.path.join(os.environ["USERPROFILE"], "Desktop", "查单词.lnk")
EXE = r"D:\Dictionary\查单词.exe"
out = []

# ---------- ① 解析 .lnk 的 IconLocation 与 IconIndex ----------
d = open(LNK, "rb").read()
flags = struct.unpack_from("<I", d, 0x14)[0]
icon_index = struct.unpack_from("<i", d, 0x3C)[0]

off = 0x4C
if flags & 0x1:
    idsize = struct.unpack_from("<H", d, off)[0]
    off += 2 + idsize
if flags & 0x2:
    li = struct.unpack_from("<I", d, off)[0]
    off += li

uni = bool(flags & 0x80)


def rd(o):
    c = struct.unpack_from("<H", d, o)[0]
    o += 2
    if uni:
        return d[o:o + c * 2].decode("utf-16-le", "replace"), o + c * 2
    return d[o:o + c].decode("latin1", "replace"), o + c


res = {}
for bit, nm in ((0x4, "NAME"), (0x8, "RELPATH"), (0x10, "WORKDIR"),
                (0x20, "ARGS"), (0x40, "ICON")):
    if flags & bit:
        res[nm], off = rd(off)

out.append(f".lnk flags=0x{flags:08X}  IconIndex={icon_index}")
out.append(f"  NAME  = {res.get('NAME')!r}")
out.append(f"  WORKDIR = {res.get('WORKDIR')!r}")
out.append(f"  ICON  = {res.get('ICON')!r}")
out.append("")

# ---------- ② 用 SHGetFileInfo 取 Shell 真实显示的图标 ----------
shell32 = ctypes.windll.shell32
user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32


class SHFILEINFO(ctypes.Structure):
    _fields_ = [("hIcon", ctypes.c_void_p), ("iIcon", ctypes.c_int),
                ("dwAttributes", wt.DWORD), ("szDisplayName", wt.WCHAR * 260),
                ("szTypeName", wt.WCHAR * 80)]


SHGFI_ICON = 0x000000100
SHGFI_LARGEICON = 0x000000000
SHGFI_SMALLICON = 0x000000001
SHGFI_USEFILEATTRIBUTES = 0x000000010
SHGFI_SYSICONINDEX = 0x00004000

shell32.SHGetFileInfoW.argtypes = [wt.LPCWSTR, wt.DWORD, ctypes.c_void_p,
                                   ctypes.c_uint, ctypes.c_uint]
shell32.SHGetFileInfoW.restype = ctypes.c_void_p
user32.GetIconInfo.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
user32.GetIconInfo.restype = wt.BOOL
user32.GetDC.argtypes = [wt.HWND]
user32.GetDC.restype = wt.HDC
user32.ReleaseDC.argtypes = [wt.HWND, wt.HDC]
user32.DestroyIcon.argtypes = [ctypes.c_void_p]
gdi32.GetObjectW.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p]
gdi32.GetObjectW.restype = ctypes.c_int
gdi32.CreateCompatibleDC.argtypes = [wt.HDC]
gdi32.CreateCompatibleDC.restype = wt.HDC
gdi32.DeleteDC.argtypes = [wt.HDC]
gdi32.GetDIBits.argtypes = [wt.HDC, ctypes.c_void_p, ctypes.c_uint,
                            ctypes.c_uint, ctypes.c_void_p, ctypes.c_void_p,
                            ctypes.c_uint]
gdi32.GetDIBits.restype = ctypes.c_int


def inspect(path, label):
    out.append(f"--- SHGetFileInfo: {label}")
    for size_flag, sname in ((SHGFI_LARGEICON, "large"),
                             (SHGFI_SMALLICON, "small")):
        sfi = SHFILEINFO()
        r = shell32.SHGetFileInfoW(path, 0, ctypes.byref(sfi),
                                   ctypes.sizeof(sfi),
                                   SHGFI_ICON | size_flag | SHGFI_SYSICONINDEX)
        if not r or not sfi.hIcon:
            out.append(f"    {sname}: 无图标 (r={r})")
            continue
        idx = sfi.iIcon
        # 取像素
        class ICONINFO(ctypes.Structure):
            _fields_ = [("fIcon", wt.BOOL), ("xHotspot", wt.DWORD),
                        ("yHotspot", wt.DWORD), ("hbmMask", ctypes.c_void_p),
                        ("hbmColor", ctypes.c_void_p)]
        ii = ICONINFO()
        user32.GetIconInfo(ctypes.c_void_p(sfi.hIcon), ctypes.byref(ii))
        hbmColor = ii.hbmColor

        class BITMAP(ctypes.Structure):
            _fields_ = [("bmType", wt.LONG), ("bmWidth", wt.LONG),
                        ("bmHeight", wt.LONG), ("bmWidthBytes", wt.LONG),
                        ("bmPlanes", wt.WORD), ("bmBitsPixel", wt.WORD),
                        ("bmBits", ctypes.c_void_p)]
        bm = BITMAP()
        gdi32.GetObjectW(hbmColor, ctypes.sizeof(bm), ctypes.byref(bm))

        class BIH(ctypes.Structure):
            _fields_ = [("biSize", wt.DWORD), ("biWidth", wt.LONG),
                        ("biHeight", wt.LONG), ("biPlanes", wt.WORD),
                        ("biBitCount", wt.WORD), ("biCompression", wt.DWORD),
                        ("biSizeImage", wt.DWORD),
                        ("biXPelsPerMeter", wt.LONG),
                        ("biYPelsPerMeter", wt.LONG),
                        ("biClrUsed", wt.DWORD),
                        ("biClrImportant", wt.DWORD)]
        bi = BIH()
        bi.biSize = ctypes.sizeof(bi)
        bi.biWidth = bm.bmWidth
        bi.biHeight = -bm.bmHeight
        bi.biPlanes = 1
        bi.biBitCount = 32
        buf = ctypes.create_string_buffer(bm.bmWidth * bm.bmHeight * 4)
        hdc = user32.GetDC(None)
        memdc = gdi32.CreateCompatibleDC(hdc)
        got = gdi32.GetDIBits(memdc, hbmColor, 0, bm.bmHeight, buf,
                              ctypes.byref(bi), 0)
        if got:
            im = Image.frombuffer("RGBA", (bm.bmWidth, bm.bmHeight), buf,
                                  "raw", "BGRA", 0, 1)
            red = sum(1 for y in range(im.height) for x in range(im.width)
                      if im.getpixel((x, y))[3] > 128
                      and im.getpixel((x, y))[0] > 120
                      and im.getpixel((x, y))[0] - im.getpixel((x, y))[1] > 40)
            tot = max(1, im.width * im.height)
            c = im.getpixel((im.width // 2, im.height // 2))
            rp = red / tot * 100
            # 判定依据（当前图标方案已改为「全尺寸统一完整版」）：
            #   完整版（摊开的书 + 金色放大镜 + 右下典章）：红占比约 11~16%，
            #       中心像素落在书页浅灰/米色上（三通道都 > 150 且接近）。
            #   印章版（红底白「典」）：红占比 > 45%，中心是深红或纯白。
            if rp > 45:
                verdict = "印章版"
            elif c[0] > 150 and c[1] > 150 and c[2] > 150:
                verdict = "完整版（书+放大镜+典章）"
            else:
                verdict = f"其他（中心{c}）"
            out.append(f"    {sname}: sysiconidx={idx} {bm.bmWidth}x{bm.bmHeight}"
                       f" 红占比{rp:.1f}% 中心{c} -> {verdict}")
        gdi32.DeleteDC(memdc)
        user32.ReleaseDC(None, hdc)
        user32.DestroyIcon(ctypes.c_void_p(sfi.hIcon))
    out.append("")


inspect(EXE, "查单词.exe")
inspect(LNK, "桌面快捷方式 查单词.lnk")

open(r"D:\Dictionary\build\_shget.txt", "w", encoding="utf-8").write("\n".join(out))
print("ok")
