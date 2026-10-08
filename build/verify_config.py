# -*- coding: utf-8 -*-
"""配置层（dict_config.json）验证：读取 / 优先级 / 容错 / 无配置时零行为变化。

注意：本脚本会临时改写 app_dir() 返回值，把配置读到沙箱目录里，
      绝不触碰 D:\\Dictionary\\ 和 build 下的真实配置。
"""
import io, os, sys, json, tempfile, shutil
sys.path.insert(0, r"D:\Dictionary\build")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

log = io.StringIO()
def say(s=""): log.write(str(s) + "\n")
ok = fail = 0
def chk(c, label, extra=""):
    global ok, fail
    if c: ok += 1; say(f"  PASS  {label}")
    else: fail += 1; say(f"  FAIL  {label}  {extra}")

import app as A

sandbox = tempfile.mkdtemp(prefix="dictcfg_")

say("== 1. 无配置文件时回退默认 ==")
# ⚠ 不能硬断言「当前无配置文件」—— build 目录里可能残留测试产生的
#   dict_config.json，那是环境状态，不是产品行为。所以这里改成
#   在沙箱里模拟「没有配置文件」的场景，断言的是**回退逻辑本身**。
chk(A.CONFIG_PATH == "" or os.path.exists(A.CONFIG_PATH),
    "CONFIG_PATH 要么为空、要么指向真实文件", A.CONFIG_PATH)
# 2026-09-17：forvo_key 已废弃（Forvo 无法使用），换成 edge_accent
chk("forvo_key" not in A.CONFIG_TEMPLATE, "forvo_key 已从模板移除")
chk("edge_accent" in A.CONFIG_TEMPLATE, "edge_accent 在模板里")

_empty_cfg, _empty_path = None, None
_sb0 = tempfile.mkdtemp(prefix="dictcfg_empty_")
_od = A.app_dir
A.app_dir = lambda: _sb0            # 空目录 → 读不到任何配置文件
try:
    _empty_cfg, _empty_path = A.load_config()
finally:
    A.app_dir = _od
chk(_empty_path == "", "空目录读不到配置（path 为空）", _empty_path)
chk(_empty_cfg["edge_accent"] == "", "无配置时 edge_accent 为空串",
    repr(_empty_cfg.get("edge_accent")))
chk(_empty_cfg["proxy"] == "", "无配置时 proxy 为空串")

chk(A.CONFIG["proxy"] == "" or isinstance(A.CONFIG["proxy"], str),
    "proxy 默认空或字符串")
chk(A.Pronouncer.edge_accent() in {c for c, _ in A.EDGE_ACCENTS},
    "口音始终落在合法集合内", A.Pronouncer.edge_accent())
chk(A.youdao_key() == ("", "") or all(A.youdao_key()),
    "youdao_key() 要么全空要么全有", A.youdao_key())
# config_status() 现在返回 (整句翻译是否可用, 口音名)
_st = A.config_status()
chk(isinstance(_st[0], bool), "config_status 第一项是布尔", _st)
chk(isinstance(_st[1], str) and _st[1], "config_status 第二项是口音名", _st)
shutil.rmtree(_sb0, ignore_errors=True)

say("\n== 2. load_config 能读到沙箱里的配置 ==")
cfg_file = os.path.join(sandbox, A.CONFIG_FILE)
with open(cfg_file, "w", encoding="utf-8") as f:
    json.dump({"edge_accent": "en-GB-LibbyNeural",
               "youdao_app_key": "YK_TEST",
               "youdao_app_secret": "YS_TEST",
               "proxy": "http://127.0.0.1:7890"}, f)
_orig_app_dir = A.app_dir
A.app_dir = lambda: sandbox
try:
    cfg, path = A.load_config()
finally:
    A.app_dir = _orig_app_dir
say(f"  cfg  = {cfg}")
say(f"  path = {path}")
chk(path == cfg_file, "定位到沙箱配置文件", path)
chk(cfg["edge_accent"] == "en-GB-LibbyNeural", "edge_accent 读到")
chk(cfg["youdao_app_key"] == "YK_TEST", "youdao_app_key 读到")
chk(cfg["youdao_app_secret"] == "YS_TEST", "youdao_app_secret 读到")
chk(cfg["proxy"] == "http://127.0.0.1:7890", "proxy 读到")

say("\n== 3. 优先级：配置文件 > 类内置常量 ==")
_orig_cfg = A.CONFIG
A.CONFIG = dict(cfg)
try:
    chk(A.Pronouncer.edge_accent() == "en-GB-LibbyNeural", "口音走配置",
        A.Pronouncer.edge_accent())
    A.CONFIG = {k: "" for k in A.CONFIG_TEMPLATE}
    chk(A.Pronouncer.edge_accent() == "en-US-AvaNeural", "无配置时回退默认",
        A.Pronouncer.edge_accent())
    # 非法口音值必须回退，不能把垃圾传给服务端
    A.CONFIG = dict(A.CONFIG_TEMPLATE, edge_accent="garbage")
    chk(A.Pronouncer.edge_accent() == "en-US-AvaNeural", "非法口音回退默认",
        A.Pronouncer.edge_accent())

    A.YOUDAO_APP_KEY = "YK_INNER"
    A.YOUDAO_APP_SECRET = "YS_INNER"
    A.CONFIG = dict(cfg)
    chk(A.youdao_key() == ("YK_TEST", "YS_TEST"), "有道走配置")
    A.CONFIG = {k: "" for k in A.CONFIG_TEMPLATE}
    chk(A.youdao_key() == ("YK_INNER", "YS_INNER"), "无配置回退内置")
    A.YOUDAO_APP_KEY = ""
    A.YOUDAO_APP_SECRET = ""
finally:
    A.CONFIG = _orig_cfg

say("\n== 4. 容错：损坏 / 非字典 / 部分键 / 空白值 ==")
with open(cfg_file, "w", encoding="utf-8") as f:
    f.write("{ 这不是合法 JSON ")
A.app_dir = lambda: sandbox
try:
    cfg2, p2 = A.load_config()
finally:
    A.app_dir = _orig_app_dir
chk(p2 == "" and cfg2["edge_accent"] == "", "损坏 JSON 安全回退", f"{p2} {cfg2}")

with open(cfg_file, "w", encoding="utf-8") as f:
    json.dump([1, 2, 3], f)
A.app_dir = lambda: sandbox
try:
    cfg3, p3 = A.load_config()
finally:
    A.app_dir = _orig_app_dir
chk(p3 == "" and cfg3["edge_accent"] == "", "非字典（数组）安全回退", f"{p3} {cfg3}")

with open(cfg_file, "w", encoding="utf-8") as f:
    json.dump({"edge_accent": "  ", "proxy": 123, "unknown_key": "x"}, f)
A.app_dir = lambda: sandbox
try:
    cfg4, p4 = A.load_config()
finally:
    A.app_dir = _orig_app_dir
chk(cfg4["edge_accent"] == "", "纯空白值视为未配")
chk(cfg4["proxy"] == "", "非字符串值被忽略")
chk("unknown_key" not in cfg4, "未知键不进配置")

# 兼容性：老的 forvo_key 不能导致报错（只是被忽略）
with open(cfg_file, "w", encoding="utf-8") as f:
    json.dump({"forvo_key": "OLD_LEGACY_KEY",
               "edge_accent": "en-AU-NatashaNeural"}, f)
A.app_dir = lambda: sandbox
try:
    cfg_old, p_old = A.load_config()
finally:
    A.app_dir = _orig_app_dir
chk(p_old == cfg_file, "含老 forvo_key 的文件仍能读", p_old)
chk("forvo_key" not in cfg_old, "老 forvo_key 被忽略")
chk(cfg_old["edge_accent"] == "en-AU-NatashaNeural",
    "同文件里的新键正常生效", cfg_old.get("edge_accent"))

with open(cfg_file, "w", encoding="utf-8") as f:
    json.dump({"edge_accent": "  en-GB-SoniaNeural  "}, f)
A.app_dir = lambda: sandbox
try:
    cfg5, _ = A.load_config()
finally:
    A.app_dir = _orig_app_dir
chk(cfg5["edge_accent"] == "en-GB-SoniaNeural", "首尾空白自动去掉",
    repr(cfg5["edge_accent"]))

say("\n== 5. 代理出口 _open_url 逻辑 ==")
import urllib.request
calls = []
_real_build = urllib.request.build_opener
_real_open = urllib.request.urlopen
class _FakeOp:
    def open(self, req, timeout=None):
        calls.append(("proxy", req.full_url if hasattr(req, "full_url") else req, timeout))
        return "PROXY_RESP"
def _fake_build(handler):
    calls.append(("build", handler.proxies if hasattr(handler, "proxies") else None))
    return _FakeOp()
def _fake_urlopen(req, timeout=None):
    calls.append(("direct", req.full_url if hasattr(req, "full_url") else req, timeout))
    return "DIRECT_RESP"
urllib.request.build_opener = _fake_build
urllib.request.urlopen = _fake_urlopen
try:
    A.CONFIG = {k: "" for k in A.CONFIG_TEMPLATE}
    r1 = A._open_url("http://example.com/a", 5)
    chk(r1 == "DIRECT_RESP", "无代理时走直连", r1)
    chk(calls[-1][0] == "direct", "直连分支被调用", str(calls[-1]))

    A.CONFIG = dict(A.CONFIG_TEMPLATE, proxy="http://127.0.0.1:7890")
    r2 = A._open_url("https://example.com/b", 7)
    chk(r2 == "PROXY_RESP", "配置代理时走 ProxyHandler", r2)
    chk(calls[-2][0] == "build", "build_opener 被调用", str(calls[-2]))
    chk(calls[-2][1] == {"http": "http://127.0.0.1:7890",
                         "https": "http://127.0.0.1:7890"},
        "http/https 都走同一代理", str(calls[-2][1]))
finally:
    urllib.request.build_opener = _real_build
    urllib.request.urlopen = _real_open
    A.CONFIG = _orig_cfg

say("\n== 6. 模板写出不覆盖已有文件 ==")
sb2 = tempfile.mkdtemp(prefix="dictcfg2_")
A.app_dir = lambda: sb2
try:
    p_new = A.write_config_template()
    chk(os.path.exists(p_new), "模板已写出", p_new)
    with open(p_new, encoding="utf-8") as f:
        tpl = json.load(f)
    chk(set(tpl.keys()) == set(A.CONFIG_TEMPLATE.keys()), "模板键齐全", str(list(tpl.keys())))
    with open(p_new, "w", encoding="utf-8") as f:
        json.dump({"edge_accent": "KEEP_ME"}, f)
    A.write_config_template()
    with open(p_new, encoding="utf-8") as f:
        after = json.load(f)
    chk(after.get("edge_accent") == "KEEP_ME", "默认不覆盖用户已填内容", str(after))
    A.write_config_template(force=True)
    with open(p_new, encoding="utf-8") as f:
        after2 = json.load(f)
    chk(after2.get("edge_accent") == "", "force=True 才重置")
finally:
    A.app_dir = _orig_app_dir
    shutil.rmtree(sb2, ignore_errors=True)

say("\n== 7. 无配置时在线功能照常（回归） ==")
d = A.fetch_online_def("water")
chk(bool(d.get("english")), "联网词典增强仍可用", str(list(d.keys())))
r, src = A.translate_text("Hello, how are you today?")
chk(r is not None, "翻译兜底仍可用", f"{r!r} / {src}")

shutil.rmtree(sandbox, ignore_errors=True)
say(f"\nRESULT  ok={ok} fail={fail}")
open(r"D:\Dictionary\build\_verify_config.txt", "w", encoding="utf-8").write(log.getvalue())
print("done")
