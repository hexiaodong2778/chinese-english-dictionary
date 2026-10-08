# -*- coding: utf-8 -*-
"""检查 Windows 图标缓存里是否已收录新图标（红底印章）。

Windows 的 iconcache_*.db 是 ESE 数据库格式，但图标位图以原始位图数据
嵌在其中，可以直接按像素特征搜索：找「红底 + 白字」的小位图。

更实用的办法：直接读 .lnk 的 icon 来源，并用 Windows API 提取图标。
这里用最稳的方式 —— 调用 ExtractIconEx 拿 32px 图标，转成像素判断颜色。
"""
import ctypes
import ctypes.wintypes as wt
import os
from PIL import Image

EXE = r"D:\Dictionary\查单词.exe"
LNK = os.path.join(os.path.expanduser("~"), "Desktop", "查单词.lnk")
out = []

# 只读的方式：用 shell32 的 ExtractIconExW 取大/小图标
shell32 = ctypes.windll.shell32
user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32

# 显式声明签名，避免 64 位句柄被截断成 int
shell32.ExtractIconExW.argtypes = [wt.LPCWSTR, ctypes.c_int,
                                   ctypes.POINTER(ctypes.c_void_p),
                                   ctypes.POINTER(ctypes.c_void_p),
                                   ctypes.c_uint]
shell32.ExtractIconExW.restype = ctypes.c_uint
user32.GetIconInfo.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
user32.GetIconInfo.restype = wt.BOOL
user32.GetDC.argtypes = [wt.HWND]
user32.GetDC.restype = wt.HDC
user32.ReleaseDC.argtypes = [wt.HWND, wt.HDC]
user32.DestroyIcon.argtypes = [ctypes.c_void_p]
gdi32.CreateCompatibleDC.argtypes = [wt.HDC]
gdi32.CreateCompatibleDC.restype = wt.HDC
gdi32.DeleteDC.argtypes = [wt.HDC]
gdi32.GetObjectW.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p]
gdi32.GetDIBits.argtypes = [wt.HDC, ctypes.c_void_p, ctypes.c_uint,
                            ctypes.c_uint, ctypes.c_void_p, ctypes.c_void_p,
                            ctypes.c_uint]

for label, target in (("exe", EXE), ("lnk", LNK)):
    if not os.path.exists(target):
        out.append(f"{label}: 不存在 {target}")
        continue
    large = ctypes.c_void_p()
    small = ctypes.c_void_p()
    n = shell32.ExtractIconExW(target, 0, ctypes.byref(large),
                               ctypes.byref(small), 1)
    out.append(f"\n{label}: {target}")
    out.append(f"  ExtractIconExW 返回 {n}")
    for tag, h in (("large", large.value), ("small", small.value)):
        if not h:
            out.append(f"  {tag}: 空句柄")
            continue
        # GetIconInfo -> 位图
        class ICONINFO(ctypes.Structure):
            _fields_ = [("fIcon", wt.BOOL), ("xHotspot", wt.DWORD),
                        ("yHotspot", wt.DWORD), ("hbmMask", wt.HBITMAP),
                        ("hbmColor", wt.HBITMAP)]
        ii = ICONINFO()
        if not user32.GetIconInfo(h, ctypes.byref(ii)):
            out.append(f"  {tag}: GetIconInfo 失败")
            continue

        class BITMAP(ctypes.Structure):
            _fields_ = [("bmType", wt.LONG), ("bmWidth", wt.LONG),
                        ("bmHeight", wt.LONG), ("bmWidthBytes", wt.LONG),
                        ("bmPlanes", wt.WORD), ("bmBitsPixel", wt.WORD),
                        ("bmBits", ctypes.c_void_p)]
        bm = BITMAP()
        gdi32.GetObjectW(ctypes.c_void_p(int(ii.hbmColor)),
                         ctypes.sizeof(bm), ctypes.byref(bm))
        out.append(f"  {tag}: {bm.bmWidth}x{bm.bmHeight} {bm.bmBitsPixel}bpp")

        # 取像素
        hdc = user32.GetDC(None)
        memdc = gdi32.CreateCompatibleDC(hdc)

        class BITMAPINFOHEADER(ctypes.Structure):
            _fields_ = [("biSize", wt.DWORD), ("biWidth", wt.LONG),
                        ("biHeight", wt.LONG), ("biPlanes", wt.WORD),
                        ("biBitCount", wt.WORD), ("biCompression", wt.DWORD),
                        ("biSizeImage", wt.DWORD),
                        ("biXPelsPerMeter", wt.LONG),
                        ("biYPelsPerMeter", wt.LONG),
                        ("biClrUsed", wt.DWORD), ("biClrImportant", wt.DWORD)]
        bi = BITMAPINFOHEADER()
        bi.biSize = ctypes.sizeof(bi)
        bi.biWidth = bm.bmWidth
        bi.biHeight = -bm.bmHeight   # top-down
        bi.biPlanes = 1
        bi.biBitCount = 32
        bi.biCompression = 0
        buf = ctypes.create_string_buffer(bm.bmWidth * bm.bmHeight * 4)
        got = gdi32.GetDIBits(memdc, wt.HANDLE(int(ii.hbmColor)), 0,
                              bm.bmHeight, buf, ctypes.byref(bi), 0)
        if got:
            im = Image.frombuffer("RGBA", (bm.bmWidth, bm.bmHeight), buf,
                                  "raw", "BGRA", 0, 1)
            red = 0
            for y in range(im.height):
                for x in range(im.width):
                    c = im.getpixel((x, y))
                    if c[3] > 128 and c[0] > 120 and c[0] - c[1] > 40:
                        red += 1
            tot = im.width * im.height
            out.append(f"        红像素占比 {red/tot*100:.1f}%  "
                       f"中心={im.getpixel((im.width//2, im.height//2))}")
        gdi32.DeleteDC(memdc)
        user32.ReleaseDC(None, hdc)
        user32.DestroyIcon(h)

open(r"D:\Dictionary\build\_extract.txt", "w", encoding="utf-8").write("\n".join(out))
print("ok")
