# -*- coding: utf-8 -*-
"""把指定目录/文件送进 Windows 回收站（不永久删除，可从回收站还原）。

用法：python _recycle.py <路径1> [路径2] ...

实现：
  · 首选 send2trash（IFileOperation，现代可靠 API）——
    装在隔离 venv（C:\\Users\\xix\\.workbuddy\\binaries\\python\\envs\\default）里，
    用该环境的 python 跑本脚本即可。
  · 兜底 ctypes SHFileOperationW（FOF_ALLOWUNDO）。
    ⚠ 该旧 API 会**假报** 0x2（文件未找到）—— 即使成功移入回收站也会报。
    所以判定以「源路径已消失」为准，返回码只作参考。

设计原则：一项一次调用、逐项验证（源路径必须消失才算成功），
任何一个失败立即停下报告，绝不在失败的情况下继续往后删。
"""
import os
import sys

try:
    from send2trash import send2trash as _send

    def recycle(path):
        """返回 (成功?, 说明)。"""
        try:
            _send(os.path.abspath(path))
        except Exception as e:
            return False, "%s: %s" % (type(e).__name__, e)
        return True, ""

    BACKEND = "send2trash (IFileOperation)"
except ImportError:
    import ctypes
    from ctypes import wintypes

    FO_DELETE = 0x0003
    FOF_ALLOWUNDO = 0x0040       # 关键：进回收站而不是永久删除
    FOF_NOCONFIRMATION = 0x0010
    FOF_NOERRORUI = 0x0400
    FOF_SILENT = 0x0004

    class SHFILEOPSTRUCTW(ctypes.Structure):
        _fields_ = [
            ("hwnd", wintypes.HWND),
            ("wFunc", wintypes.UINT),
            ("pFrom", wintypes.LPCWSTR),
            ("pTo", wintypes.LPCWSTR),
            ("fFlags", wintypes.USHORT),
            ("fAnyOperationsAborted", wintypes.BOOL),
            ("hNameMappings", wintypes.LPVOID),
            ("lpszProgressTitle", wintypes.LPCWSTR),
        ]

    def recycle(path):
        op = SHFILEOPSTRUCTW()
        op.wFunc = FO_DELETE
        op.pFrom = os.path.abspath(path) + "\0\0"   # 双 \0 结尾
        op.fFlags = (FOF_ALLOWUNDO | FOF_NOCONFIRMATION
                     | FOF_NOERRORUI | FOF_SILENT)
        rc = ctypes.windll.shell32.SHFileOperationW(ctypes.byref(op))
        # ⚠ 0x2 是已知的假报错：成功移入回收站也可能返回它。
        #   真正的判定在调用方（源路径是否消失）。
        if op.fAnyOperationsAborted:
            return False, "操作被中止"
        return True, "(rc=0x%x，仅供参考)" % rc

    BACKEND = "ctypes SHFileOperationW"


def size_of(p):
    if os.path.isfile(p):
        return os.path.getsize(p)
    tot = 0
    for r, _d, fs in os.walk(p):
        for f in fs:
            try:
                tot += os.path.getsize(os.path.join(r, f))
            except OSError:
                pass
    return tot


def main(paths):
    if not paths:
        print("没有传入任何路径")
        return 2
    print("后端：%s" % BACKEND)
    print("⚠ 本机 shell API 已知会「移完才报错」—— 判定一律以事后状态为准：")
    print("  源路径已消失 = 成功；源路径还在 = 真失败，立即停。")
    freed = 0
    done = 0
    for p in paths:
        if not os.path.exists(p):
            print("SKIP  %s  (不存在)" % p)
            continue
        sz = size_of(p)
        ok, why = recycle(p)
        if os.path.exists(p):
            # 本机 shell API 的另一种假失败：内容全部移走、但**顶层空壳**
            # 删不掉（实测 PermissionError，而里面 190 个文件已全进回收站）。
            # 空壳不含任何可恢复内容，直接 rmdir 收尾，不算数据损失。
            remain = 0
            if os.path.isdir(p):
                remain = sum(len(fs) for _, _, fs in os.walk(p))
            if os.path.isdir(p) and remain == 0:
                try:
                    os.rmdir(p)
                    print("      （内容已入回收站，空壳已顺手移除: %s）" % p)
                except OSError as e:
                    print("ERR   %s  空壳移除失败：%s" % (p, e))
                    print("★ 出错即停：剩余 %d 项未处理"
                          % (len(paths) - done - 1))
                    return 1
        if not os.path.exists(p):
            # ★ 成功 = 源路径消失。后端报错与否只作参考（实测两个后端
            #   都会假报：ctypes 报 0x2、send2trash 报 FileNotFoundError，
            #   但东西确实进了 $Recycle.Bin，见 _probe_recyclebin.py 的验证）。
            freed += sz
            done += 1
            note = "" if ok else ("  [API 假报错: %s]" % why[:60])
            print("OK    %s  -> 回收站 (%.2f MB)%s"
                  % (p, sz / 1048576, note))
        else:
            print("ERR   %s  源路径仍在，视为真失败：%s" % (p, why))
            print("★ 出错即停：剩余 %d 项未处理" % (len(paths) - done - 1))
            return 1
    print("本批完成 %d 项，释放 %.1f MB" % (done, freed / 1048576))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
