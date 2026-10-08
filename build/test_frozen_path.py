"""模拟 frozen 环境，验证 resource_path 定位正确。"""
import sys, os, types
sys.path.insert(0, r"D:\Dictionary\build")

import app as A

print("=== 开发模式 ===")
print("  app_dir():", A.app_dir())
for db in ["dict.db", "dict_ja.db", "dict_fr.db", "dict_yue.db"]:
    p = A.resource_path(db)
    print(f"  {db:14s} -> {p}  exists={os.path.exists(p)}")

print("\n=== 模拟 frozen（sys.frozen=True, _MEIPASS=临时目录）===")
# 伪造 frozen 状态：exe 在 D:\Dictionary
sys.frozen = True
sys._MEIPASS = r"C:\Users\xix\AppData\Local\Temp\_MEI12345"
sys.executable = r"D:\Dictionary\查单词.exe"
print("  app_dir():", A.app_dir())
for db in ["dict.db", "dict_ja.db", "dict_fr.db", "dict_yue.db"]:
    p = A.resource_path(db)
    print(f"  {db:14s} -> {p}  exists={os.path.exists(p)}")

print("\n=== 打开词库 ===")
for db in ["dict.db", "dict_ja.db", "dict_fr.db", "dict_yue.db"]:
    con = A.open_db(db)
    if con:
        n = con.execute("SELECT COUNT(*) FROM dict").fetchone()[0]
        print(f"  {db:14s} -> {n:,} 条")
        con.close()
    else:
        print(f"  {db:14s} -> FAIL")
