"""验证：用 ctypes 直接调 Windows SAPI COM 朗读，不启动任何外部进程。

思路：
  1. 用 ctypes 调 ole32.CoInitialize / CoCreateInstance 创建 SAPI.SpVoice
  2. 通过 IDispatch::Invoke 调用 Speak / Rate / Volume / Voice 等属性
  3. 全程在本进程内完成 —— 不 spawn powershell，不触发杀毒告警

SAPI.SpVoice 的 ProgID CLSID（系统固定）：
  {96749377-3391-11D2-9EE3-00C04F797396}  SpVoice
其默认接口为 IDispatch，所以用 Invoke 即可。
"""
import ctypes
from ctypes import wintypes
import sys

ole32 = ctypes.oledll.ole32
user32 = ctypes.windll.user32

# --- 基础类型 ---
CLSCTX_INPROC_SERVER = 1
CLSCTX_LOCAL_SERVER = 4
CLSCTX_ALL = CLSCTX_INPROC_SERVER | CLSCTX_LOCAL_SERVER
DISPATCH_METHOD = 1
DISPATCH_PROPERTYGET = 2
DISPATCH_PROPERTYPUT = 4

S_OK = 0


class GUID(ctypes.Structure):
    _fields_ = [("Data1", wintypes.DWORD),
                ("Data2", wintypes.WORD),
                ("Data3", wintypes.WORD),
                ("Data4", ctypes.c_ubyte * 8)]


def guid(s):
    """解析 {xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx}"""
    s = s.strip("{}")
    p = s.split("-")
    g = GUID()
    g.Data1 = int(p[0], 16)
    g.Data2 = int(p[1], 16)
    g.Data3 = int(p[2], 16)
    rest = p[3] + p[4]
    for i in range(8):
        g.Data4[i] = int(rest[i * 2:i * 2 + 2], 16)
    return g


class DISPPARAMS(ctypes.Structure):
    _fields_ = [("rgvarg", ctypes.POINTER(ctypes.c_void_p)),
                ("rgdispidNamedArgs", ctypes.POINTER(ctypes.c_long)),
                ("cArgs", ctypes.c_uint),
                ("cNamedArgs", ctypes.c_uint)]


class VARIANT(ctypes.Structure):
    _fields_ = [("vt", ctypes.c_ushort),
                ("wReserved1", ctypes.c_ushort),
                ("wReserved2", ctypes.c_ushort),
                ("wReserved3", ctypes.c_ushort),
                ("llVal", ctypes.c_longlong),
                ("_pad", ctypes.c_ubyte * 8)]


VARIANT_SIZE = ctypes.sizeof(VARIANT)
VT_BSTR = 8
VT_I4 = 3
VT_DISPATCH = 9
VT_EMPTY = 0

print("GUID/结构体定义 OK, VARIANT 大小 =", VARIANT_SIZE)

# --- 初始化 COM ---
hr = ole32.CoInitialize(None)
print("CoInitialize hr =", hr, "(0 或 1 都正常，1 表示已初始化)")

# --- 创建 SpVoice ---
clsid = guid("{96749377-3391-11D2-9EE3-00C04F797396}")   # SpVoice
iid_idispatch = guid("{00020400-0000-0000-C000-000000000046}")

p_unk = ctypes.c_void_p()
hr = ole32.CoCreateInstance(
    ctypes.byref(clsid), None, CLSCTX_ALL,
    ctypes.byref(iid_idispatch), ctypes.byref(p_unk))
print("CoCreateInstance(SpVoice) hr =", hex(hr & 0xFFFFFFFF),
      "ptr =", p_unk.value)

if p_unk.value:
    # 取 IDispatch 的 vtable
    vtbl = ctypes.cast(p_unk, ctypes.POINTER(ctypes.c_void_p))[0]
    funcs = ctypes.cast(vtbl, ctypes.POINTER(ctypes.c_void_p))
    # IDispatch: 0=QueryInterface 1=AddRef 2=Release
    #            3=GetTypeInfoCount 4=GetTypeInfo 5=GetIDsOfNames 6=Invoke
    release = ctypes.WINFUNCTYPE(ctypes.c_ulong, ctypes.c_void_p)(funcs[2])
    getids = ctypes.WINFUNCTYPE(
        ctypes.HRESULT, ctypes.c_void_p, ctypes.POINTER(GUID),
        ctypes.POINTER(ctypes.c_wchar_p), ctypes.c_uint, ctypes.c_ulong,
        ctypes.POINTER(ctypes.c_long))(funcs[5])
    invoke = ctypes.WINFUNCTYPE(
        ctypes.HRESULT, ctypes.c_void_p, ctypes.c_long,
        ctypes.POINTER(GUID), ctypes.c_ulong, ctypes.c_ushort,
        ctypes.POINTER(DISPPARAMS), ctypes.c_void_p,
        ctypes.c_void_p, ctypes.c_void_p)(funcs[6])

    def dispid(name):
        d = ctypes.c_long()
        g = GUID()
        hr = getids(p_unk, ctypes.byref(g),
                    ctypes.byref(ctypes.c_wchar_p(name)), 1, 0,
                    ctypes.byref(d))
        return d.value if hr == 0 else None

    for name in ("Speak", "Rate", "Volume", "Voice", "GetVoices",
                 "Status", "Pause", "Resume"):
        print(f"  dispid({name}) =", dispid(name))

    print("\n尝试朗读 'hello dog' ...")
    d_speak = dispid("Speak")
    if d_speak:
        # 参数：BSTR 文本, Flags(1=异步)
        buf = ctypes.create_unicode_buffer("hello, this is dog")
        args = (ctypes.c_void_p * 2)()
        # 参数按逆序压栈：最后一个参数在最前
        v_flags = VARIANT()
        v_flags.vt = VT_I4
        v_flags.llVal = 1
        v_txt = VARIANT()
        v_txt.vt = VT_BSTR
        v_txt.llVal = ctypes.cast(buf, ctypes.c_void_p).value
        args[0] = ctypes.cast(ctypes.byref(v_flags), ctypes.c_void_p)
        args[1] = ctypes.cast(ctypes.byref(v_txt), ctypes.c_void_p)
        dp = DISPPARAMS()
        dp.rgvarg = ctypes.cast(args, ctypes.POINTER(ctypes.c_void_p))
        dp.cArgs = 2
        dp.cNamedArgs = 0
        hr = invoke(p_unk, d_speak, None, 0, DISPATCH_METHOD,
                    ctypes.byref(dp), None, None, None)
        print("  Speak hr =", hex(hr & 0xFFFFFFFF))
        import time
        time.sleep(3)
    release(p_unk)

print("\nDone.")
