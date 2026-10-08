# -*- coding: utf-8 -*-
"""包装 skill-creator 的打包脚本，修掉它自身的 import 路径问题。"""
import os
import sys

SCRIPT_DIR = (r"D:\Program Files\com.tencent.pcgame.workbuddy\resources"
              r"\app.asar.unpacked\resources\plugins\workbuddy-builtin"
              r"\skills\skill-creator\scripts")
sys.path.insert(0, SCRIPT_DIR)

from package_skill import package_skill  # noqa: E402

skill = r"C:\Users\xix\.workbuddy\skills\sqlite-field-cleanup"
outdir = r"D:\Dictionary\build"

res = package_skill(skill, outdir)
print("RESULT:", res)
