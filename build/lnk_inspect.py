"""重写桌面快捷方式的图标路径（不用 COM）。

背景：本机安全策略拦截了 WScript.Shell（COM），无法用常规方式建快捷方式。
.lnk 是二进制格式，但「图标位置」以 UTF-16LE 明文存在文件里，
可以在不破坏其它字段的前提下原地替换等长或更短的字符串。

策略：
  1. 读出 .lnk 全部字节
  2. 找到 IconLocation 的 UTF-16LE 串
  3. 用新路径覆盖（新的更短则补 \\0，更长则需要重建 —— 这里用重建法）
最稳妥的做法：直接构造一个最小可用的 .lnk，或用 Shell Link 结构重写。

本脚本采用「原地替换 + 必要时重建」的方式：
  · 先尝试原地替换（新串长度 <= 旧串长度）
  · 不行就整体重建一个标准 Shell Link
"""
import struct
import os

LNK = os.path.join(os.environ["USERPROFILE"], "Desktop", "查单词.lnk")
EXE = r"D:\Dictionary\查单词.exe"
WORKDIR = r"D:\Dictionary"

data = open(LNK, "rb").read()
print(f"原 .lnk 大小: {len(data)} 字节")

# --- 解析 ShellLinkHeader ---
hdr_size = struct.unpack_from("<I", data, 0)[0]
flags = struct.unpack_from("<I", data, 20)[0]
print(f"HeaderSize={hdr_size}  Flags=0x{flags:08X}")

HAS_LINK_TARGET_ID_LIST = 0x00000001
HAS_LINK_INFO = 0x00000002
HAS_NAME = 0x00000004
HAS_RELATIVE_PATH = 0x00000008
HAS_WORKING_DIR = 0x00000010
HAS_ARGUMENTS = 0x00000020
HAS_ICON_LOCATION = 0x00000040
IS_UNICODE = 0x00000080

for name, bit in (("HasLinkTargetIDList", HAS_LINK_TARGET_ID_LIST),
                  ("HasLinkInfo", HAS_LINK_INFO),
                  ("HasName", HAS_NAME),
                  ("HasRelativePath", HAS_RELATIVE_PATH),
                  ("HasWorkingDir", HAS_WORKING_DIR),
                  ("HasArguments", HAS_ARGUMENTS),
                  ("HasIconLocation", HAS_ICON_LOCATION),
                  ("IsUnicode", IS_UNICODE)):
    print(f"  {name:22s} = {bool(flags & bit)}")


def read_str(off):
    """读一个 CountedString（2字节长度 + UTF-16 内容）。"""
    n = struct.unpack_from("<H", data, off)[0]
    s = data[off + 2:off + 2 + n * 2].decode("utf-16-le", "replace")
    return s, off + 2 + n * 2


off = hdr_size
if flags & HAS_LINK_TARGET_ID_LIST:
    idl_size = struct.unpack_from("<H", data, off)[0]
    print(f"\nIDList 大小 = {idl_size}")
    off += 2 + idl_size

if flags & HAS_LINK_INFO:
    li_size = struct.unpack_from("<I", data, off)[0]
    print(f"LinkInfo 大小 = {li_size}")
    off += li_size

if flags & HAS_NAME:
    s, off = read_str(off)
    print(f"Name = {s!r}")
if flags & HAS_RELATIVE_PATH:
    s, off = read_str(off)
    print(f"RelativePath = {s!r}")
if flags & HAS_WORKING_DIR:
    s, off = read_str(off)
    print(f"WorkingDir = {s!r}")
if flags & HAS_ARGUMENTS:
    s, off = read_str(off)
    print(f"Arguments = {s!r}")

icon_off = None
if flags & HAS_ICON_LOCATION:
    icon_off = off
    s, off = read_str(off)
    print(f"IconLocation = {s!r}")
else:
    print("没有 IconLocation 字段 —— 需要重建")

print(f"\n文件剩余 {len(data) - off} 字节")
print("目标图标路径:", EXE)
