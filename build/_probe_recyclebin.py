# -*- coding: utf-8 -*-
"""直接看回收站底层目录（$Recycle.Bin），确认被删的东西到底进没进去。"""
import os
import datetime

CUT = datetime.datetime(2026, 9, 18, 16, 0)

for drive in ["D:\\$Recycle.Bin", "C:\\$Recycle.Bin"]:
    if not os.path.isdir(drive):
        print(drive, "-> 不存在或无权限")
        continue
    try:
        sids = os.listdir(drive)
    except PermissionError:
        print(drive, "-> 权限不足")
        continue
    for sid in sids:
        d = os.path.join(drive, sid)
        if not os.path.isdir(d):
            continue
        try:
            items = os.listdir(d)
        except PermissionError:
            print(d, "-> 权限不足")
            continue
        recent = []
        for f in items:
            p = os.path.join(d, f)
            try:
                mt = os.path.getmtime(p)
                sz = os.path.getsize(p) if os.path.isfile(p) else -1
            except OSError:
                continue
            if datetime.datetime.fromtimestamp(mt) > CUT:
                recent.append((mt, f, sz))
        if recent:
            print(d, "-> 今天 16:00 后共 %d 项:" % len(recent))
            for mt, f, sz in sorted(recent)[-25:]:
                print("    %s  %-28s %12d"
                      % (datetime.datetime.fromtimestamp(mt).strftime("%H:%M:%S"),
                         f, sz))
        else:
            print(d, "-> 今天 16:00 后无新项目（共 %d 项旧物）" % len(items))
