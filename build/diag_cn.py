"""诊断 cn_index 表：是否存在、行数、『狗』能否命中。"""
import sqlite3

DB = r"D:\Dictionary\build\dict.db"
con = sqlite3.connect(DB)
con.row_factory = sqlite3.Row

print("=== 所有表 ===")
for r in con.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"):
    print("  ", r["name"])

print("\n=== 所有索引 ===")
for r in con.execute(
        "SELECT name, tbl_name FROM sqlite_master WHERE type='index'"):
    print("  ", r["name"], "->", r["tbl_name"])

try:
    n = con.execute("SELECT COUNT(*) FROM cn_index").fetchone()[0]
    print(f"\n=== cn_index 行数: {n:,} ===")
    cols = [d[1] for d in con.execute("PRAGMA table_info(cn_index)")]
    print("  字段:", cols)

    print("\n=== cn_index 前 10 行 ===")
    for r in con.execute("SELECT * FROM cn_index LIMIT 10"):
        print("  ", dict(r))

    print("\n=== cn_index 里含『狗』的行 ===")
    rows = con.execute(
        "SELECT * FROM cn_index WHERE zh LIKE '%狗%' LIMIT 20").fetchall()
    print(f"  命中 {len(rows)} 行")
    for r in rows:
        print("  ", dict(r))

    print("\n=== dog 在 cn_index 里的记录 ===")
    rows = con.execute(
        "SELECT * FROM cn_index WHERE word='dog'").fetchall()
    print(f"  命中 {len(rows)} 行")
    for r in rows:
        print("  ", dict(r))
except Exception as e:
    print("\n!!! cn_index 不可用:", e)

con.close()
