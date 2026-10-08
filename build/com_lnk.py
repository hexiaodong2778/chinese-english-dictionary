# -*- coding: utf-8 -*-
"""用 IShellLink COM 解析快捷方式（最权威的方式）。
若 COM 被安全策略拦截，退回到直接读取 .lnk 的 ICON_LOCATION 字段。
"""
import os
import struct

LNK = os.path.join(os.environ["USERPROFILE"], "Desktop", "查单词.lnk")
out = []

# --- 路径 A：COM IShellLink ---
try:
    import ctypes
    from ctypes import wintypes as wt

    ole32 = ctypes.windll.ole32
    ole32.CoInitialize(None)

    CLSID_ShellLink = ctypes.c_buffer(
        bytes.fromhex("0114020000000000C000000000000046"))
    IID_IShellLinkW = ctypes.c_buffer(
        bytes.fromhex("F2149DF0D0C04B9D9581B8D0D0D0D0D0"))

    psl = ctypes.c_void_p()
    # 用 CoCreateInstance
    class GUID(ctypes.Structure):
        _fields_ = [("d1", ctypes.c_uint32), ("d2", ctypes.c_uint16),
                    ("d3", ctypes.c_uint16), ("d4", ctypes.c_ubyte * 8)]

    def guid(s):
        b = bytes.fromhex(s)
        g = GUID()
        g.d1, g.d2, g.d3 = struct.unpack_from("<IHH", b, 0)
        g.d4 = (ctypes.c_ubyte * 8)(*b[8:16])
        return g

    clsid_shelllink = guid("0114020000000000C000000000000046")
    iid_ishelllinkw = guid("000214F900000000C000000000000046")
    CLSCTX_INPROC_SERVER = 0x1
    hr = ole32.CoCreateInstance(ctypes.byref(clsid_shelllink), None,
                                CLSCTX_INPROC_SERVER,
                                ctypes.byref(iid_ishelllinkw),
                                ctypes.byref(psl))
    out.append(f"CoCreateInstance hr=0x{hr & 0xFFFFFFFF:08X}")
    if hr == 0 and psl:
        # vtable: QueryInterface, AddRef, Release, GetPath, ...
        vt = ctypes.cast(psl, ctypes.POINTER(ctypes.c_void_p))[0]
        funcs = ctypes.cast(vt, ctypes.POINTER(ctypes.c_void_p))

        def call(idx, *args):
            proto = ctypes.WINFUNCTYPE(ctypes.c_long, ctypes.c_void_p,
                                       *[ctypes.c_void_p if a is None else type(a)
                                         for a in args])
            return proto(funcs[idx])

        # IPersistFile 是另一个接口，需先 QueryInterface
        iid_pf = guid("0000010B00000000C000000000000046")
        pf = ctypes.c_void_p()
        QI = ctypes.WINFUNCTYPE(ctypes.c_long, ctypes.c_void_p,
                                ctypes.c_void_p, ctypes.c_void_p)(funcs[0])
        hr2 = QI(psl, ctypes.byref(iid_pf), ctypes.byref(pf))
        out.append(f"QueryInterface(IPersistFile) hr=0x{hr2 & 0xFFFFFFFF:08X}")
        if hr2 == 0 and pf:
            pvt = ctypes.cast(pf, ctypes.POINTER(ctypes.c_void_p))[0]
            pfuncs = ctypes.cast(pvt, ctypes.POINTER(ctypes.c_void_p))
            Load = ctypes.WINFUNCTYPE(ctypes.c_long, ctypes.c_void_p,
                                      ctypes.c_wchar_p,
                                      ctypes.c_uint)(pfuncs[5])
            hr3 = Load(pf, LNK, 0)
            out.append(f"Load hr=0x{hr3 & 0xFFFFFFFF:08X}")
            if hr3 == 0:
                buf = ctypes.create_unicode_buffer(600)
                # GetPath(vtable idx 3 of IShellLinkW)
                GetPath = ctypes.WINFUNCTYPE(
                    ctypes.c_long, ctypes.c_void_p, ctypes.c_wchar_p,
                    ctypes.c_int, ctypes.c_void_p, ctypes.c_uint)(funcs[3])
                GetPath(psl, buf, 600, None, 0)
                out.append(f"  GetPath -> {buf.value!r}")
                ibuf = ctypes.create_unicode_buffer(600)
                idx = ctypes.c_int()
                # GetIconLocation(idx 16)
                GetIconLocation = ctypes.WINFUNCTYPE(
                    ctypes.c_long, ctypes.c_void_p, ctypes.c_wchar_p,
                    ctypes.c_int, ctypes.POINTER(ctypes.c_int))(
                        funcs[16])
                GetIconLocation(psl, ibuf, 600, ctypes.byref(idx))
                out.append(f"  GetIconLocation -> {ibuf.value!r} idx={idx.value}")
                wdbuf = ctypes.create_unicode_buffer(600)
                GetWorkingDirectory = ctypes.WINFUNCTYPE(
                    ctypes.c_long, ctypes.c_void_p, ctypes.c_wchar_p,
                    ctypes.c_int)(funcs[9])
                GetWorkingDirectory(psl, wdbuf, 600)
                out.append(f"  GetWorkingDirectory -> {wdbuf.value!r}")
        # Release
        Rel = ctypes.WINFUNCTYPE(ctypes.c_ulong, ctypes.c_void_p)(funcs[2])
        Rel(psl)
    ole32.CoUninitialize()
except Exception as e:
    out.append(f"COM 方式失败: {e!r}")

open(r"D:\Dictionary\build\_lnkcom.txt", "w", encoding="utf-8").write("\n".join(out))
print("ok")
