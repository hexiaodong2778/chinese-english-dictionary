# -*- coding: utf-8 -*-
"""Edge 神经语音发音引擎 —— 回归测试。

覆盖：
  ① Sec-MS-GEC 令牌算法（可用已知输入校验，不依赖网络）
  ② WebSocket 帧编码（掩码是否正确、长度分档）
  ③ MP3 校验函数（正常/截断/非音频/空）
  ④ SSML 转义（含 & < > 的词不会破坏 XML）
  ⑤ 真实联网合成（网络不可用时自动 SKIP，不算失败）
  ⑥ 缓存命中不重复联网
  ⑦ 口音配置读写与非法值回退
"""
import io
import os
import struct
import sys
import time

# 路径自适应：本脚本所在目录即工作目录（克隆到任意位置都能跑）
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.chdir(HERE)

import app as A

PASS = []
FAIL = []


def check(name, cond, detail=""):
    if cond:
        PASS.append(name)
    else:
        FAIL.append("%s %s" % (name, detail))


# ============================================================ ① 令牌算法
gec = A.edge_sec_ms_gec(0)          # 固定时间，结果可复现
check("① 令牌是 64 位大写十六进制",
      len(gec) == 64 and gec == gec.upper() and all(
          c in "0123456789ABCDEF" for c in gec), gec)

# 手动复算一遍，确认算法与 edge-tts 包一致
import hashlib as _h
_t = 0 + A.EDGE_WIN_EPOCH
_t -= _t % 300
_t *= 1e9 / 100
_exp = _h.sha256(("%.0f%s" % (_t, A.EDGE_TRUSTED_TOKEN)).encode("ascii")
                 ).hexdigest().upper()
check("① 令牌算法与 edge-tts 包一致", gec == _exp, "%s != %s" % (gec, _exp))

# 同一 5 分钟窗口内令牌必须相同（否则服务端会拒）
# ⚠ 基准点要选在窗口起点，否则 t0 和 t0+299 会跨窗口，断言本身是错的
#   （第一版就踩了这个：t0=1700000000，t0%300=200，取 299 秒后已经翻窗）
t0 = 1700000000
t0 -= t0 % 300                      # 对齐到 5 分钟窗口起点
check("① 同时刻令牌稳定", A.edge_sec_ms_gec(t0) == A.edge_sec_ms_gec(t0))
# 跨 5 分钟窗口必须变化
check("① 跨窗口令牌变化",
      A.edge_sec_ms_gec(t0) != A.edge_sec_ms_gec(t0 + 300))
# 窗口内任意秒应归一到同一个令牌
check("① 窗口内归一",
      A.edge_sec_ms_gec(t0) == A.edge_sec_ms_gec(t0 + 299))
check("① 窗口内归一（末点）",
      A.edge_sec_ms_gec(t0 + 299) == A.edge_sec_ms_gec(t0 + 300 - 1))

# ============================================================ ② WebSocket 帧
for n, why in ((10, "短"), (200, "中"), (70000, "长")):
    frame = A._edge_ws_frame_text("x" * n)
    check("② %s帧 FIN+text 标志正确" % why, frame[0] == 0x81, hex(frame[0]))
    check("② %s帧 带掩码位" % why, frame[1] & 0x80, hex(frame[1]))
    ln = frame[1] & 0x7F
    if n < 126:
        check("② %s帧 长度用 7 位表示" % why, ln == n, ln)
        hdr = 2
    elif n < 65536:
        check("② %s帧 长度用 126 + 2字节" % why, ln == 126, ln)
        check("② %s帧 长度值正确" % why,
              struct.unpack(">H", frame[2:4])[0] == n)
        hdr = 4
    else:
        check("② %s帧 长度用 127 + 8字节" % why, ln == 127, ln)
        check("② %s帧 长度值正确" % why,
              struct.unpack(">Q", frame[2:10])[0] == n)
        hdr = 10
    mask = frame[hdr:hdr + 4]
    body = frame[hdr + 4:]
    check("② %s帧 载荷长度正确" % why, len(body) == n, len(body))
    check("② %s帧 载荷已掩码（不是明文 x）" % why,
          body[:4] != b"xxxx", body[:8])

# ============================================================ ③ MP3 校验
# 构造合法 MP3：48kbps 48000Hz → 帧长 144 字节
def make_mp3(frames=10, br_i=6, sr_i=1):
    BR = [0, 32, 40, 48, 56, 64, 80, 96, 112, 128, 160, 192,
          224, 256, 320, 0]
    SR = {0: 44100, 1: 48000, 2: 32000}
    br, sr = BR[br_i], SR[sr_i]
    flen = int(144000 * br / sr)
    out = b""
    for _ in range(frames):
        out += bytes([0xFF, 0xFB, (br_i << 4) | (sr_i << 2)])
        out += b"\x00" * (flen - 3)
    return out


good = make_mp3(12)
check("③ 合法 MP3 通过校验", A.edge_audio_ok(good), len(good))
check("③ 空数据被拒", not A.edge_audio_ok(b""))
check("③ None 被拒", not A.edge_audio_ok(None))
check("③ 太短被拒", not A.edge_audio_ok(b"\xff\xfb\x64" + b"\x00" * 100))
check("③ 纯零字节被拒", not A.edge_audio_ok(b"\x00" * 5000))
check("③ HTML 错误页被拒",
      not A.edge_audio_ok(b"<html>" + b"x" * 5000))
check("③ JSON 错误被拒",
      not A.edge_audio_ok(b'{"error":"bad"}' * 100))
# 带 ID3 头的合法 MP3
id3 = b"ID3\x04\x00\x00" + bytes([0, 0, 0, 0]) + make_mp3(12)
check("③ 带 ID3 头的 MP3 通过校验", A.edge_audio_ok(id3), len(id3))
# 帧数不足（只 2 帧）应被拒
check("③ 帧数不足被拒", not A.edge_audio_ok(make_mp3(2)[:600] + b"\x00" * 600))

# ============================================================ ④ SSML 转义
src = open(os.path.join(HERE, "app.py"), encoding="utf-8").read()
check("④ SSML 里做了 & 转义", 'replace("&", "&amp;")' in src)
check("④ SSML 里做了 < 转义", 'replace("<", "&lt;")' in src)
check("④ SSML 里做了 > 转义", 'replace(">", "&gt;")' in src)

# ============================================================ ⑤ 口音配置
check("⑤ 默认口音有效",
      A.Pronouncer.edge_accent() in {c for c, _ in A.EDGE_ACCENTS},
      A.Pronouncer.edge_accent())
check("⑤ 默认口音是美音 Ava",
      A.Pronouncer.edge_accent() == "en-US-AvaNeural",
      A.Pronouncer.edge_accent())
# 非法值必须回退，不能把垃圾传给服务端
_old = A.CONFIG.get("edge_accent")
A.CONFIG["edge_accent"] = "not-a-real-voice"
check("⑤ 非法口音回退默认",
      A.Pronouncer.edge_accent() == "en-US-AvaNeural",
      A.Pronouncer.edge_accent())
A.CONFIG["edge_accent"] = "en-GB-LibbyNeural"
check("⑤ 合法口音被采纳",
      A.Pronouncer.edge_accent() == "en-GB-LibbyNeural",
      A.Pronouncer.edge_accent())
A.CONFIG["edge_accent"] = _old

check("⑤ 口音表非空且代号唯一",
      len(A.EDGE_ACCENTS) >= 10 and
      len({c for c, _ in A.EDGE_ACCENTS}) == len(A.EDGE_ACCENTS),
      len(A.EDGE_ACCENTS))
check("⑤ 口音标签可查",
      "Ava" in A.Pronouncer.edge_accent_label("en-US-AvaNeural"),
      A.Pronouncer.edge_accent_label("en-US-AvaNeural"))
check("⑤ 标签含性别标记",
      "女" in A.Pronouncer.edge_accent_label("en-US-AvaNeural"),
      A.Pronouncer.edge_accent_label("en-US-AvaNeural"))
check("⑤ 标签够短（不挤压状态栏）",
      max(len(lb) for _, lb in A.EDGE_ACCENTS) <= 14,
      max(len(lb) for _, lb in A.EDGE_ACCENTS))
check("⑤ 未知代号返回原串（不崩）",
      A.Pronouncer.edge_accent_label("zzz") == "zzz")

# ============================================================ ⑥ 配置兼容
check("⑥ 老配置里的 forvo_key 被忽略（模板已无此键）",
      "forvo_key" not in A.CONFIG_TEMPLATE)
check("⑥ 模板含 edge_accent", "edge_accent" in A.CONFIG_TEMPLATE)
check("⑥ config_status 返回两项",
      len(A.config_status()) == 2, A.config_status())
_status = A.config_status()
check("⑥ config_status 第二项是口音名",
      isinstance(_status[1], str) and len(_status[1]) > 0, _status)

# ============================================================ ⑦ 联网合成
print("开始联网合成测试…")
try:
    t0 = time.time()
    audio = A.edge_tts_synth("hello", "en-US-AvaNeural")
    dt = int((time.time() - t0) * 1000)
    if audio and A.edge_audio_ok(audio):
        PASS.append("⑦ 真实合成 hello 成功（%dms / %d bytes）" % (dt, len(audio)))
        # 换口音应得到不同音频（长度或内容不同）
        b2 = A.edge_tts_synth("hello", "en-GB-LibbyNeural")
        if b2 and A.edge_audio_ok(b2):
            PASS.append("⑦ 英音合成成功（%d bytes）" % len(b2))
            check("⑦ 不同口音产出不同音频", b2 != audio)
    else:
        # 网络问题不算产品缺陷，但必须明确标出来
        FAIL.append("⑦ 联网合成失败（可能是网络问题，需人工确认）"
                    " len=%d" % len(audio))
except Exception as e:
    FAIL.append("⑦ 联网合成抛异常 %r" % (e,))

# ============================================================ ⑧ 缓存
try:
    A.CONFIG["edge_accent"] = "en-US-AvaNeural"
    pr = A.Pronouncer()
    p1 = pr._fetch_edge("cachedtest")
    if p1 and os.path.exists(p1):
        PASS.append("⑧ 合成后落盘缓存 %s" % os.path.basename(p1))
        sz1 = os.path.getsize(p1)
        t0 = time.time()
        p2 = pr._fetch_edge("cachedtest")
        dt = int((time.time() - t0) * 1000)
        check("⑧ 第二次命中缓存返回同一路径", p1 == p2)
        check("⑧ 缓存命中耗时 < 200ms（未联网）", dt < 200, "%dms" % dt)
        check("⑧ 缓存文件大小一致", os.path.getsize(p2) == sz1)
        # 换口音不能复用旧缓存
        A.CONFIG["edge_accent"] = "en-GB-LibbyNeural"
        p3 = pr._fetch_edge("cachedtest")
        check("⑧ 换口音不复用旧缓存", p3 and p3 != p1,
              "%r vs %r" % (p3, p1))
    else:
        FAIL.append("⑧ 无法生成缓存文件（可能是网络问题）")
except Exception as e:
    FAIL.append("⑧ 缓存测试抛异常 %r" % (e,))
finally:
    A.CONFIG["edge_accent"] = _old

# ============================================================ ⑨ speak 入口
try:
    A.CONFIG["edge_accent"] = "en-US-AvaNeural"
    pr = A.Pronouncer()

    # 空文本必须安全返回 False
    check("⑨ 空文本返回 False", pr.speak("", "edge") is False)
    # 非英语走本地语音分支，不应崩
    pr.speak("テスト", "edge", lang="ja")
    PASS.append("⑨ 非英语分支不抛异常")
    # 老的 global 参数仍能工作（向后兼容）
    pr.speak("compat", "global")
    PASS.append("⑨ 旧 global 参数向后兼容")
    # _last_source 有值（说明确实走到了某个音源）
    check("⑨ _last_source 被设置",
          isinstance(pr._last_source, str), repr(pr._last_source))
except Exception as e:
    FAIL.append("⑨ speak 入口抛异常 %r" % (e,))
finally:
    A.CONFIG["edge_accent"] = _old

# ============================================================ 汇总
out = []
out.append("=" * 62)
out.append("Edge 神经语音回归测试")
out.append("=" * 62)
out.append("")
out.append("PASS = %d   FAIL = %d" % (len(PASS), len(FAIL)))
out.append("")
if FAIL:
    out.append("---- 失败明细 ----")
    for f in FAIL:
        out.append("  ✗ " + f)
    out.append("")
out.append("---- 通过明细 ----")
for p in PASS:
    out.append("  ✓ " + p)

io.open(os.path.join(HERE, "test_edge_tts.txt"), "w",
        encoding="utf-8").write("\n".join(out) + "\n")

print("PASS=%d FAIL=%d" % (len(PASS), len(FAIL)))
for f in FAIL:
    print("FAIL:", f)

# ⚠ 退出方式（2026-09-18 结论，三轮实测后才写准）
#   —— 先记下 09-17 和 09-18 两次**没量到底就动手**的错误判断：
#     09-17「必须 os._exit，否则挂在解释器关闭阶段」→ 写反了
#     09-18「改成 sys.exit 就行」                  → 探针里侥幸过了，跑真脚本照样卡
#
#   实测（每级独立子进程 + 硬超时，只改退出方式这一个变量；
#         见 _probe_edge_exit2.py / _probe_edge_hang.py）：
#     QApplication + os._exit(0)（没播过音）        → 干净退出 0.34s
#     QApplication + speak() 后 os._exit(0)         → ★卡死 >45s
#     同一场景改走 sys.exit(0)                       → 探针过(1.6s)，真脚本 ★卡死 >420s
#     同一场景 + 停播放器/deleteLater 再 os._exit     → 仍然卡死
#     同一场景 + TerminateProcess 硬杀               → 仍然卡死
#     （TerminateProcess 也不管用，说明卡点**不在**退出函数本身）
#
#   **真凶**：第 ⑨ 节真的播放音频，Qt 的 FFmpeg 媒体后端会在自己的
#   线程上异步探测 mp3，日志长这样（注意它出现在 "PASS=60" **之后**）：
#       [mp3 @ 0x...] Estimating duration from bitrate, this may be inaccurate
#       Input #0, mp3, from '.../edge_en-US-Ava_compat.mp3'
#   那个媒体线程停在一个原生调用里，并且**持着 GIL 不放** ——
#   主线程从最后一次 print 之后就再也拿不回 GIL，于是后面每一行
#   Python 代码（os._exit、sys.exit、TerminateProcess）都执行不到，
#   faulthandler 连一个栈都打不出来（watchdog 线程同样拿不到 GIL）。
#
#   → 所以「跑完但退不出」**在进程内部无解**。权威判定依据是
#     本脚本写下的产物文件 test_edge_tts.txt，
#     _run_all2.py 会在超时时读它并按产物判定
#     （单列一档「超时未退出·按产物判定」，且有护栏防止把真卡死洗绿，
#       对应测试见 test_runner_fallback.py）。
#   下面这两行保留：万一没踩中那个竞态，它能让进程干脆退出。
sys.stdout.flush()
_code = 1 if FAIL else 0
try:
    import ctypes
    ctypes.windll.kernel32.TerminateProcess(
        ctypes.windll.kernel32.GetCurrentProcess(), _code)
except Exception:
    os._exit(_code)
