"""验证 v2：修正 VARIANT 结构体，用正确的 bstrVal/ulVal 成员。

VARIANT 内存布局（16 字节数据区）：
  union {
    LONGLONG llVal;        // offset 0
    LONG     lVal;         // offset 0
    ...
    BSTR     bstrVal;      // offset 8  (指针)
    IDispatch *pdispVal;   // offset 8
    ...
  }
所以 BSTR 要写在偏移 8 处，而不是 0。
"""
import ctypes
from ctypes import wintypes
import time

ole32 = ctypes.oledll.ole32

CLSCTX_ALL = 5
DISPATCH_METHOD = 1
DISPATCH_PROPERTYGET = 2
DISPATCH_PROPERTYPUT = 4


class GUID(ctypes.Structure):
    _fields_ = [("Data1", wintypes.DWORD), ("Data2", wintypes.WORD),
                ("Data3", wintypes.WORD), ("Data4", ctypes.c_ubyte * 8)]


def guid(s):
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


class _VUNION(ctypes.Union):
    _fields_ = [
        ("llVal", ctypes.c_longlong),
        ("lVal", ctypes.c_long),
        ("bstrVal", ctypes.c_void_p),
        ("pdispVal", ctypes.c_void_p),
        ("punkVal", ctypes.c_void_p),
        ("piVal", ctypes.POINTER(ctypes.c_int)),
        ("pbstrVal", ctypes.c_void_p),
    ]


class VARIANT(ctypes.Structure):
    _fields_ = [("vt", ctypes.c_ushort),
                ("wReserved1", ctypes.c_ushort),
                ("wReserved2", ctypes.c_ushort),
                ("wReserved3", ctypes.c_ushort),
                ("val", _VUNION)]


class DISPPARAMS(ctypes.Structure):
    _fields_ = [("rgvarg", ctypes.POINTER(VARIANT)),
                ("rgdispidNamedArgs", ctypes.POINTER(ctypes.c_long)),
                ("cArgs", ctypes.c_uint),
                ("cNamedArgs", ctypes.c_uint)]


VT_BSTR = 8
VT_I4 = 3
VT_DISPATCH = 9

ole32.CoInitialize(None)

clsid = guid("{96749377-3391-11D2-9EE3-00C04F797396}")
iid = guid("{00020400-0000-0000-C000-000000000046}")
p_unk = ctypes.c_void_p()
hr = ole32.CoCreateInstance(ctypes.byref(clsid), None, CLSCTX_ALL,
                            ctypes.byref(iid), ctypes.byref(p_unk))
print("SpVoice ptr =", p_unk.value, "hr =", hex(hr & 0xFFFFFFFF))

vtbl = ctypes.cast(p_unk, ctypes.POINTER(ctypes.c_void_p))[0]
funcs = ctypes.cast(vtbl, ctypes.POINTER(ctypes.c_void_p))

release = ctypes.WINFUNCTYPE(ctypes.c_ulong, ctypes.c_void_p)(funcs[2])
getids = ctypes.WINFUNCTYPE(
    ctypes.HRESULT, ctypes.c_void_p, ctypes.POINTER(GUID),
    ctypes.POINTER(ctypes.c_wchar_p), ctypes.c_uint, ctypes.c_ulong,
    ctypes.POINTER(ctypes.c_long))(funcs[5])
# Invoke 返回值也可能带 out 参数，用 c_long 接 HRESULT
invoke = ctypes.WINFUNCTYPE(
    ctypes.c_long, ctypes.c_void_p, ctypes.c_long, ctypes.POINTER(GUID),
    ctypes.c_ulong, ctypes.c_ushort, ctypes.POINTER(DISPPARAMS),
    ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p)(funcs[6])


def dispid(name):
    d = ctypes.c_long()
    g = GUID()
    hr = getids(p_unk, ctypes.byref(g),
                ctypes.byref(ctypes.c_wchar_p(name)), 1, 0,
                ctypes.byref(d))
    return d.value if hr == 0 else None


def set_prop(name, value):
    """设置属性：Rate / Volume 等。"""
    d = dispid(name)
    if d is None:
        return False
    put_id = ctypes.c_long(-3)      # DISPID_PROPERTYPUT
    v = VARIANT()
    v.vt = VT_I4
    v.val.lVal = int(value)
    dp = DISPPARAMS()
    arr = (VARIANT * 1)(v)
    dp.rgvarg = ctypes.cast(arr, ctypes.POINTER(VARIANT))
    dp.rgdispidNamedArgs = ctypes.cast(ctypes.byref(put_id),
                                       ctypes.POINTER(ctypes.c_long))
    dp.cArgs = 1
    dp.cNamedArgs = 1
    hr = invoke(p_unk, d, None, 0, DISPATCH_PROPERTYPUT,
                ctypes.byref(dp), None, None, None)
    return hr == 0


def speak(text, flags=1):
    """朗读。flags=1 异步。"""
    d = dispid("Speak")
    # 参数逆序：rgvarg[0] = Flags, rgvarg[1] = Text
    arr = (VARIANT * 2)()
    arr[0].vt = VT_I4
    arr[0].val.lVal = flags
    arr[1].vt = VT_BSTR
    arr[1].val.bstrVal = ctypes.cast(
        ctypes.create_unicode_buffer(text), ctypes.c_void_p).value
    dp = DISPPARAMS()
    dp.rgvarg = ctypes.cast(arr, ctypes.POINTER(VARIANT))
    dp.cArgs = 2
    dp.cNamedArgs = 0
    hr = invoke(p_unk, d, None, 0, DISPATCH_METHOD,
                ctypes.byref(dp), None, None, None)
    return hr == 0, hr


print("set Rate(1) ->", set_prop("Rate", 1))
print("set Volume(100) ->", set_prop("Volume", 100))

ok, hr = speak("hello, dog")
print("Speak hr =", hex(hr & 0xFFFFFFFF), "ok =", ok)
time.sleep(2.5)

# 再试中文
ok, hr = speak("这是一只狗")
print("Speak 中文 hr =", hex(hr & 0xFFFFFFFF), "ok =", ok)
time.sleep(3)

release(p_unk)
print("Done.")
