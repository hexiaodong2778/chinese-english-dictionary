"""校验 app_icon.ico 的结构完整性与各帧参数。"""
import struct

p = r"D:\Dictionary\build\app_icon.ico"
data = open(p, "rb").read()
res, typ, cnt = struct.unpack("<HHH", data[:6])
print("ICO 头: reserved={} type={} count={}".format(res, typ, cnt))

off = 6
ok = True
for i in range(cnt):
    w, h, pal, rsv, planes, bpp, size, offset = struct.unpack(
        "<BBBBHHII", data[off:off + 16])
    w2 = w or 256
    h2 = h or 256
    # 校验该帧数据是否落在文件内
    inside = offset + size <= len(data)
    is_png = data[offset:offset + 8] == b"\x89PNG\r\n\x1a\n"
    print("  帧{}: {}x{}  {}bpp  {}字节  偏移={}  PNG={} 边界OK={}".format(
        i + 1, w2, h2, bpp, size, offset, is_png, inside))
    if not (inside and is_png):
        ok = False
    off += 16

print("文件总长:", len(data))
print("结构校验:", "PASS" if ok and cnt == 7 else "FAIL")
