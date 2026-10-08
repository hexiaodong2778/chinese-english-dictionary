# -*- coding: utf-8 -*-
"""确认新功能字符串已打进 exe（PyInstaller pyc 里字符串是明文）。"""
marks = [
    b"dict_config.json",
    b"forvo_key",
    b"youdao_app_key",
    b"youdao_app_secret",
    b"load_config",
    b"config_status",
    b"write_config_template",
    b"forvo_key()",
    b"_open_url",
    b"UnicodeDecodeError_not_used",
]
p = r"D:\Dictionary\查单词.exe"
data = open(p, "rb").read()
out = [f"exe size = {len(data)}", ""]
for m in marks:
    n = data.count(m)
    out.append(f"{'OK  ' if n else 'MISS'}  {m.decode():32s} count={n}")
open(r"D:\Dictionary\build\_exe_marks_cfg.txt", "w", encoding="utf-8").write("\n".join(out))
print("ok")
