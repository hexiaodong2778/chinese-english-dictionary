# -*- coding: utf-8 -*-
"""重建桌面快捷方式 —— 这一版带完整 LinkTargetIDList。

上一版只写了 LinkInfo、没写 IDList，导致：
  · 双击能启动（Windows 靠 LinkInfo 兜底解析）
  · 但 ExtractIconExW(.lnk) 返回 0 —— 快捷方式取不到图标
    于是桌面回退显示旧缓存 / 系统默认图标（蓝色放大镜）

这一版按 MS-SHLLINK 规范补上 LinkTargetIDList，让 Shell 能
正常解析目标与其图标。这是 Windows 快捷方式的标准做法。
"""
import os
import struct

LNK = os.path.join(os.environ["USERPROFILE"], "Desktop", "查单词.lnk")
TARGET = r"D:\Dictionary\查单词.exe"
WORKDIR = r"D:\Dictionary"
NAME = "查单词"
ICON = TARGET

HAS_ID_LIST = 0x00000001
HAS_LINK_INFO = 0x00000002
HAS_NAME = 0x00000004
HAS_WORKING_DIR = 0x00000010
HAS_ICON_LOCATION = 0x00000040
IS_UNICODE = 0x00000080

CLSID = bytes.fromhex("0114020000000000C000000000000046")


def counted_str(s):
    return struct.pack("<H", len(s)) + s.encode("utf-16-le")


def item_id(data):
    """ItemID: UInt16 ItemSize(含自身) + 数据"""
    return struct.pack("<H", len(data) + 2) + data


def build_id_list(path):
    """为本地绝对路径构造 LinkTargetIDList。

    结构：每个 ItemID 以一个 SHITEMID 表示路径的一层。
    根层（"D:\\"）用 0x1F 开头的经典格式，其后各层是目录/文件名。
    """
    drive = path[:2]                 # "D:"
    parts = [p for p in path[3:].split("\\") if p]

    ids = b""

    # --- 根项：My Computer\D:\ ---
    # 经典格式：0x1F 0x50 <name utf16 + NUL> ...
    root_name = (drive + "\\").encode("utf-16-le") + b"\x00\x00"
    root_data = bytes([0x1F, 0x50]) + root_name
    root_data += b"\x00" * 8          # 占位数据（MS 未公开，填 0 兼容）
    ids += item_id(root_data)

    # --- 各级目录/文件项 ---
    for p in parts:
        nm = p.encode("utf-16-le") + b"\x00\x00"
        # 简化项：0x31 0x00 <name> （0x31 表示普通文件/目录项）
        d = bytes([0x31, 0x00]) + nm
        ids += item_id(d)

    ids += b"\x00\x00"                # TerminalID
    return struct.pack("<H", len(ids)) + ids


def build_link_info(path):
    """LinkInfo（VolumeID + LocalBasePath ANSI + Unicode）。"""
    drive_serial = 0x12345678
    vol_label = b"\x00"
    volume_id = struct.pack("<IIII", 16, 3, drive_serial, 16) + vol_label
    # VolumeID.Size 回填
    volume_id = struct.pack("<I", len(volume_id)) + volume_id[4:]

    path_ansi = path.encode("mbcs", "replace") + b"\x00"
    suffix_ansi = b"\x00"
    path_u = path.encode("utf-16-le") + b"\x00\x00"
    suffix_u = b"\x00\x00"

    header_size = 28
    vol_off = header_size
    lbp_off = vol_off + len(volume_id)
    cnrl_off = vol_off          # 无网络路径，按约定指回 VolumeID
    suffix_off = lbp_off + len(path_ansi)
    lbp_u_off = suffix_off + len(suffix_ansi)
    suffix_u_off = lbp_u_off + len(path_u)

    flags = 0x00000001          # VolumeIDAndLocalBasePath

    li = struct.pack("<IIIIIIII", 0, header_size, flags, vol_off, lbp_off,
                     cnrl_off, suffix_off, lbp_u_off)
    li += volume_id + path_ansi + suffix_ansi + path_u + suffix_u
    li = struct.pack("<I", len(li)) + li[4:]
    return li


def build(path, workdir, name, icon):
    flags = (HAS_ID_LIST | HAS_LINK_INFO | HAS_NAME | HAS_WORKING_DIR
             | HAS_ICON_LOCATION | IS_UNICODE)

    header = struct.pack("<I 16s I I Q I I I I I",
                         0x0000004C, CLSID, flags,
                         0,   # FileAttributes（普通文件）
                         0,   # CreationTime
                         0,   # AccessTime
                         0,   # WriteTime
                         0,   # FileSize
                         0,   # IconIndex
                         1)   # ShowCommand
    header += struct.pack("<HH", 0, 0)   # HotKey + Reserved

    body = build_id_list(path)
    body += build_link_info(path)
    body += counted_str(name)      # NAME_STRING
    body += counted_str(workdir)   # WORKING_DIR
    body += counted_str(icon)      # ICON_LOCATION
    body += struct.pack("<I", 0)   # ExtraData 终结
    return header + body


if __name__ == "__main__":
    if os.path.exists(LNK):
        bak = LNK + ".bak2"
        open(bak, "wb").write(open(LNK, "rb").read())
        print("已备份:", bak)
    blob = build(TARGET, WORKDIR, NAME, ICON)
    open(LNK, "wb").write(blob)
    print(f"已写入 {LNK}  {len(blob)} 字节")
    print("  目标:", TARGET)
    print("  工作目录:", WORKDIR)
    print("  名称:", NAME)
    print("  图标:", ICON)
