"""验证 v3：用真正的 BSTR（SysAllocString）+ 保持引用，修正 Speak 参数。

v2 的两个问题：
  1. create_unicode_buffer 的对象在赋给 VARIANT 后被 GC，指针悬空
  2. 传的是 wchar* 而非真正的 BSTR（COM 要求 SysAllocString 分配）
修正：用 oleaut32.SysAllocString 分配，并保存到列表防止 GC。
"""
import ctypes
from ctypes import wintypes
import time

ole32 = ctypes.windll.ole32
oleaut32 = ctypes.windll.oleaut32

CLSCTX_ALL = 5
DISPATCH_METHOD = 1
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
    _fields_ = [("llVal", ctypes.c_longlong),
                ("lVal", ctypes.c_long),
                ("bstrVal", ctypes.c_void_p),
                ("pdispVal", ctypes.c_void_p)]


class VARIANT(ctypes.Structure):
    _fields_ = [("vt", ctypes.c_ushort), ("wReserved1", ctypes.c_ushort),
                ("wReserved2", ctypes.c_ushort), ("wReserved3", ctypes.c_ushort),
                ("val", _VUNION)]


class DISPPARAMS(ctypes.Structure):
    _fields_ = [("rgvarg", ctypes.POINTER(VARIANT)),
                ("rgdispidNamedArgs", ctypes.POINTER(ctypes.c_long)),
                ("cArgs", ctypes.c_uint),
                ("cNamedArgs", ctypes.c_uint)]


VT_BSTR, VT_I4 = 8, 3

# SysAllocString / SysFreeString 原型
# 注意：必须用 ctypes.windll（不自动推断 HRESULT），并显式声明
# restype=c_void_p，否则 64 位指针会被当成有符号 long 而溢出。
oleaut32.SysAllocString.restype = ctypes.c_void_p
oleaut32.SysAllocString.argtypes = [ctypes.c_wchar_p]
oleaut32.SysFreeString.restype = None
oleaut32.SysFreeString.argtypes = [ctypes.c_void_p]

ole32.CoInitialize.restype = ctypes.c_long
ole32.CoInitialize.argtypes = [ctypes.c_void_p]
ole32.CoCreateInstance.restype = ctypes.c_long
ole32.CoCreateInstance.argtypes = [
    ctypes.POINTER(GUID), ctypes.c_void_p, ctypes.c_ulong,
    ctypes.POINTER(GUID), ctypes.POINTER(ctypes.c_void_p)]

ole32.CoInitialize(None)
clsid = guid("{96749377-3391-11D2-9EE3-00C04F797396}")
iid = guid("{00020400-0000-0000-C000-000000000046}")
p_unk = ctypes.c_void_p()
ole32.CoCreateInstance(ctypes.byref(clsid), None, CLSCTX_ALL,
                       ctypes.byref(iid), ctypes.byref(p_unk))

vtbl = ctypes.cast(p_unk, ctypes.POINTER(ctypes.c_void_p))[0]
funcs = ctypes.cast(vtbl, ctypes.POINTER(ctypes.c_void_p))
release = ctypes.WINFUNCTYPE(ctypes.c_ulong, ctypes.c_void_p)(funcs[2])
getids = ctypes.WINFUNCTYPE(ctypes.HRESULT, ctypes.c_void_p,
                            ctypes.POINTER(GUID),
                            ctypes.POINTER(ctypes.c_wchar_p), ctypes.c_uint,
                            ctypes.c_ulong,
                            ctypes.POINTER(ctypes.c_long))(funcs[5])
invoke = ctypes.WINFUNCTYPE(
    ctypes.c_long, ctypes.c_void_p, ctypes.c_long, ctypes.POINTER(GUID),
    ctypes.c_ulong, ctypes.c_ushort, ctypes.POINTER(DISPPARAMS),
    ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p)(funcs[6])


def dispid(name):
    d = ctypes.c_long()
    g = GUID()
    hr = getids(p_unk, ctypes.byref(g), ctypes.byref(ctypes.c_wchar_p(name)),
                1, 0, ctypes.byref(d))
    return d.value if hr == 0 else None


def set_prop(name, value):
    d = dispid(name)
    if d is None:
        return False
    put_id = ctypes.c_long(-3)
    arr = (VARIANT * 1)()
    arr[0].vt = VT_I4
    arr[0].val.lVal = int(value)
    dp = DISPPARAMS()
    dp.rgvarg = ctypes.cast(arr, ctypes.POINTER(VARIANT))
    dp.rgdispidNamedArgs = ctypes.cast(ctypes.byref(put_id),
                                       ctypes.POINTER(ctypes.c_long))
    dp.cArgs, dp.cNamedArgs = 1, 1
    return invoke(p_unk, d, None, 0, DISPATCH_PROPERTYPUT,
                  ctypes.byref(dp), None, None, None) == 0


# 保持 BSTR 引用，防止中途被释放
_keep = []


def speak(text, flags=1):
    bstr = oleaut32.SysAllocString(text)
    _keep.append(bstr)
    d = dispid("Speak")
    arr = (VARIANT * 2)()
    arr[0].vt = VT_I4
    arr[0].val.lVal = flags
    arr[1].vt = VT_BSTR
    arr[1].val.bstrVal = bstr
    dp = DISPPARAMS()
    dp.rgvarg = ctypes.cast(arr, ctypes.POINTER(VARIANT))
    dp.cArgs, dp.cNamedArgs = 2, 0
    hr = invoke(p_unk, d, None, 0, DISPATCH_METHOD,
                ctypes.byref(dp), None, None, None)
    return hr == 0, hr


print("Rate(1) ->", set_prop("Rate", 1))
print("Volume(100) ->", set_prop("Volume", 100))

for txt in ("hello, this is a dog", "dog"):
    ok, hr = speak(txt)
    print(f"Speak({txt!r}) hr = {hex(hr & 0xFFFFFFFF)} ok = {ok}")
    time.sleep(2.2)

# 中文测试
ok, hr = speak("狗")
print(f"Speak('狗') hr = {hex(hr & 0xFFFFFFFF)} ok = {ok}")
time.sleep(2.5)

for b in _keep:
    oleaut32.SysFreeString(b)
release(p_unk)
print("Done.")
