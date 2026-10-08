# -*- coding: utf-8 -*-
"""生成 Windows 版本信息资源文件 (version_info.txt)。

让 exe 在「属性 -> 详细信息」与任务管理器中显示中文名称、说明与版本号。
"""
import os

OUT = r"D:\Dictionary\build\version_info.txt"

CONTENT = """# UTF-8
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=(1, 0, 0, 0),
    prodvers=(1, 0, 0, 0),
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo(
      [
        StringTable(
          u'080404B0',
          [StringStruct(u'CompanyName', u''),
           StringStruct(u'FileDescription', u'查单词 - 多语言离线词典'),
           StringStruct(u'FileVersion', u'1.0.0.0'),
           StringStruct(u'InternalName', u'\u67e5\u5355\u8bcd'),
           StringStruct(u'LegalCopyright', u''),
           StringStruct(u'OriginalFilename', u'\u67e5\u5355\u8bcd.exe'),
           StringStruct(u'ProductName', u'\u67e5\u5355\u8bcd'),
           StringStruct(u'ProductVersion', u'1.0.0.0')])
      ]),
    VarFileInfo([VarStruct(u'Translation', [2052, 1200])])
  ]
)
"""


def main():
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(CONTENT)
    print("version info ->", OUT, os.path.getsize(OUT), "bytes")


if __name__ == "__main__":
    main()
