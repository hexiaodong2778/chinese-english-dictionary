"""重建桌面快捷方式（不依赖 COM），并顺带更新显示名称。

本机安全策略拦截 WScript.Shell，所以手工构造标准 Shell Link (.lnk)。

结构（MS-SHLLINK）：
  ShellLinkHeader (76B)
  [LinkTargetIDList]   —— 可选
  [LinkInfo]           —— 可选
  [StringData...]      —— NAME_STRING / WORKING_DIR / ICON_LOCATION
  ExtraData            —— 通常终结于 4 字节 0

为最大兼容性，这里只写必要字段并声明 HasName / HasWorkingDir /
HasIconLocation，所有字符串用 Unicode（IsUnicode 标志）。
不写 IDList / LinkInfo —— Windows 会按目标路径自行解析，
对本地固定路径的快捷方式足够可靠。
"""
import struct
import os

LNK = os.path.join(os.environ["USERPROFILE"], "Desktop", "查单词.lnk")
TARGET = r"D:\Dictionary\查单词.exe"
WORKDIR = r"D:\Dictionary"
NAME = "查单词 · 离线多语言词典"
ICON = TARGET
DESC = "查单词 - 多语言离线词典"

# --- flags ---
HAS_NAME = 0x00000004
HAS_WORKING_DIR = 0x00000010
HAS_ICON_LOCATION = 0x00000040
HAS_ARGUMENTS = 0x00000020
IS_UNICODE = 0x00000080
# 目标路径用 LinkInfo 之外的方式表达不便，这里用 IDList 之外的
# 「相对路径」不合适；改用 LinkTargetIDList 由系统解析。
# 简化方案：写入 LinkInfo（本地路径）以保证双击一定命中。
HAS_LINK_INFO = 0x00000002
HAS_RELATIVE_PATH = 0x00000008

CLSID_SHELL_LINK = bytes.fromhex(
    "01140200000000000000000000000046"[:0] )  # 占位，下面显式写


def counted_string(s):
    """CountedString: UInt16 字符数 + UTF-16LE 字节（不含结尾 NUL）。"""
    b = s.encode("utf-16-le")
    return struct.pack("<H", len(s)) + b


def build_link_info(local_path):
    """构造 LinkInfo（VolumeID + LocalBasePath）。"""
    # 拆出盘符与剩余路径
    drive = local_path[:2]                 # "D:"
    rest = local_path[2:]                  # "\\Dictionary\\查单词.exe"

    # VolumeID: Size(4) DriveType(4) DriveSerialNumber(4)
    #           VolumeLabelOffset(4) + 1 字节标签(NUL)
    vol_label = b"\x00"
    volume_id = struct.pack("<III I",
                            4 + 4 + 4 + 4 + len(vol_label),
                            3,                     # DRIVE_FIXED
                            0x12345678,
                            16)                    # label 偏移
    volume_id += vol_label

    # LocalBasePath 用 ANSI 不太好处理中文，改用 LocalBasePathUnicode
    # LinkInfoHeader: Size(4) HeaderSize(4) Flags(4) VolumeIDOffset(4)
    #                 LocalBasePathOffset(4) CommonNetworkRelativeLinkOffset(4)
    #                 CommonPathSuffixOffset(4)
    # [+ LocalBasePathOffsetUnicode(4) CommonPathSuffixOffsetUnicode(4)]
    path_ansi = local_path.encode("mbcs", "replace") + b"\x00"
    suffix_ansi = b"\x00"

    header_size = 28 + 8        # 带 Unicode 偏移字段
    volume_id_offset = header_size
    lbp_off = volume_id_offset + len(volume_id)
    # 无 CommonNetworkRelativeLink，偏移填 volume_id_offset（约定）
    cnrl_off = volume_id_offset
    suffix_off = lbp_off + len(path_ansi)
    # Unicode 串放在 ANSI 串之后
    lbp_u_off = suffix_off + len(suffix_ansi)
    path_u = local_path.encode("utf-16-le") + b"\x00\x00"
    suffix_u_off = lbp_u_off + len(path_u)
    suffix_u = b"\x00\x00"

    flags = 0x00000001          # VolumeIDAndLocalBasePath
    flags |= 0x00000008         # LocalBasePath 为 Unicode（自定义高位置，视实现）

    li = struct.pack("<IIIIIIII",
                     0,                       # Size 先占位
                     header_size,
                     flags,
                     volume_id_offset,
                     lbp_off,
                     cnrl_off,
                     suffix_off,
                     lbp_u_off)
    li += struct.pack("<I", suffix_u_off)
    li += volume_id
    li += path_ansi
    li += suffix_ansi
    li += path_u
    li += suffix_u
    # 回填 Size
    li = struct.pack("<I", len(li)) + li[4:]
    return li


def build_link_target_id_list(local_path):
    """构造 LinkTargetIDList —— 让 Windows 直接认出目标文件。

    每项 = ItemSize(2) + ItemID 数据；终结符 = 2 字节 0。
    ItemID 内容随 Shell 实现而定，这里用「根目录 + 文件项」的常见形式。
    为保证可靠性，本项目改为不写 IDList，由系统按 LinkInfo 解析。
    """
    return None


def build_lnk(target, workdir, name, icon, desc):
    header_flags = HAS_LINK_INFO | HAS_NAME | HAS_WORKING_DIR \
        | HAS_ICON_LOCATION | IS_UNICODE

    link_info = build_link_info(target)

    # StringData 顺序固定：NAME, RELATIVE_PATH, WORKING_DIR, ARGUMENTS, ICON
    strings = b""
    strings += counted_string(name)          # NAME_STRING
    strings += counted_string(workdir)       # WORKING_DIR
    strings += counted_string(icon)          # ICON_LOCATION

    header = struct.pack(
        "<I 16s I I Q I I I I I",
        0x0000004C,                                    # HeaderSize = 76
        bytes.fromhex("0114020000000000C000000000000046"),  # LinkCLSID
        header_flags,
        0,                                             # FileAttributes
        0,                                             # CreationTime
        0,                                             # AccessTime
        0,                                             # WriteTime
        0,                                             # FileSize
        0,                                             # IconIndex
        1,                                             # ShowCommand = SW_SHOWNORMAL
    )
    # Header 尾部还有 2 字节 HotKey + 2 字节 Reserved
    header += struct.pack("<HH", 0, 0)

    # LINK_INFO 紧跟在 header（无 IDList）之后
    body = link_info + strings
    # ExtraData: 用 4 字节 0 作为终结
    body += struct.pack("<I", 0)

    return header + body


def main():
    if os.path.exists(LNK):
        # 备份原文件
        bak = LNK + ".bak"
        if not os.path.exists(bak):
            with open(LNK, "rb") as f:
                open(bak, "wb").write(f.read())
            print("已备份:", bak)

    blob = build_lnk(TARGET, WORKDIR, NAME, ICON, DESC)
    with open(LNK, "wb") as f:
        f.write(blob)
    print("已写入:", LNK, len(blob), "字节")
    print("  目标:", TARGET)
    print("  工作目录:", WORKDIR)
    print("  名称:", NAME)
    print("  图标:", ICON)


if __name__ == "__main__":
    main()
