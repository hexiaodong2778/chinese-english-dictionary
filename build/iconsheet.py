from PIL import Image

# 用 ico 里真实的各尺寸帧来对比。
# 注意：不能复用同一个 Image 句柄改 .size —— PIL 只解一次帧，会拿到同一张图。
# 必须每个尺寸重新 open 一次，并用 ico.getimage()。
SRC = r"D:\Dictionary\build\app_icon.ico"

ico = Image.open(SRC)
sizes = sorted(ico.info.get("sizes", set()))
print("ico frames:", sizes)

sheet = Image.new("RGB", (820, 360), (255, 255, 255))
x = 16
for (w, h) in sizes:
    try:
        im = Image.open(SRC)          # 每次重新打开，拿到独立句柄
        im.size = (w, h)
        fr = im.convert("RGBA")
        sheet.paste(fr, (x, 48), fr)
        x += w + 16
        print("pasted", w, "at", x - w - 16)
    except Exception as e:
        print("frame", w, "err", e)

sheet.save(r"D:\Dictionary\build\icon_sizes.png")
print("sheet saved, width used:", x)
