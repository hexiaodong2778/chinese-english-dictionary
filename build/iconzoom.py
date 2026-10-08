from PIL import Image

SRC = r"D:\Dictionary\build\app_icon.ico"
SCALE = 8

small = [16, 24, 32]
imgs = []
for s in small:
    im = Image.open(SRC)
    im.size = (s, s)
    imgs.append(im.convert("RGBA").resize((s * SCALE, s * SCALE), Image.NEAREST))

pad = 20
W = sum(i.width for i in imgs) + pad * (len(imgs) + 1)
H = max(i.height for i in imgs) + pad * 2
sheet = Image.new("RGB", (W, H), (245, 245, 248))
x = pad
for i in imgs:
    sheet.paste(i, (x, pad), i)
    x += i.width + pad

sheet.save(r"D:\Dictionary\build\icon_zoom.png")
print("zoom saved", sheet.size, "scale", SCALE)
