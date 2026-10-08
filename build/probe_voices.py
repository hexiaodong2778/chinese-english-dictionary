# -*- coding: utf-8 -*-
"""列出本机所有可用 TTS 语音，并演示当前发音引擎对同一个词
在「美式 / 英式」两种模式下分别喂给 TTS 的字符串。

用法：python probe_voices.py
输出写到 _voices.txt（UTF-8），避免 PowerShell 管道转码乱码。
"""
import os
import sys

sys.path.insert(0, r"D:\Dictionary\build")

out = []

# ---------- ① 系统已安装的语音（SAPI 视角，注册表） ----------
out.append("=" * 68)
out.append("① 系统已安装语音（注册表 SAPI Voices）")
out.append("=" * 68)
try:
    import winreg
    seen = []
    for root, path in (
        (winreg.HKEY_LOCAL_MACHINE,
         r"SOFTWARE\Microsoft\Speech\Voices\Tokens"),
        (winreg.HKEY_LOCAL_MACHINE,
         r"SOFTWARE\Microsoft\Speech_OneCore\Voices\Tokens"),
        (winreg.HKEY_LOCAL_MACHINE,
         r"SOFTWARE\WOW6432Node\Microsoft\Speech\Voices\Tokens"),
    ):
        try:
            k = winreg.OpenKey(root, path)
        except OSError:
            continue
        n = winreg.QueryInfoKey(k)[0]
        for i in range(n):
            try:
                sub = winreg.EnumKey(k, i)
                sk = winreg.OpenKey(k, sub)
                nm = winreg.QueryValueEx(sk, "")[0] if True else ""
                try:
                    lang = winreg.QueryValueEx(
                        winreg.OpenKey(sk, "Attributes"), "Language")[0]
                except OSError:
                    lang = "?"
                seen.append((path.split("\\")[-2], nm, lang))
            except OSError:
                pass
    # 去重
    uniq = []
    for a, b, c in seen:
        if (b, c) not in [(x[1], x[2]) for x in uniq]:
            uniq.append((a, b, c))
    out.append(f"共 {len(uniq)} 个语音条目：")
    for src, nm, lang in sorted(uniq, key=lambda x: (x[2], x[1])):
        out.append(f"    [{lang:<8}] {nm}   <{src}>")
    if not uniq:
        out.append("    （读注册表没拿到，可能权限受限）")
except Exception as e:
    out.append(f"    读取失败: {e}")

# ---------- ② QtTextToSpeech 实际能用的语音 ----------
out.append("")
out.append("=" * 68)
out.append("② QtTextToSpeech 实际可用语音（程序真正用的那条路）")
out.append("=" * 68)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
try:
    from PySide6.QtWidgets import QApplication
    from PySide6.QtTextToSpeech import QTextToSpeech

    app = QApplication.instance() or QApplication([])

    for eng in ("winrt", "sapi", ""):
        try:
            t = QTextToSpeech(eng) if eng else QTextToSpeech()
        except Exception as e:
            out.append(f"  引擎 {eng or 'default'}: 构造异常 {e}")
            continue
        st = t.state()
        out.append(f"  引擎 {eng or 'default'}: state={st}")
        try:
            vs = list(t.availableVoices())
        except Exception as e:
            vs = []
            out.append(f"      枚举语音异常: {e}")
        out.append(f"      可用语音 {len(vs)} 个")
        for v in vs:
            out.append(f"        · {v.name()}  [{v.locale().name()}]")
        # 尝试选一个英文语音
        for v in vs:
            if "en" in v.locale().name().lower():
                t.setVoice(v)
                out.append(f"      已选中英文语音: {v.name()} "
                           f"[{v.locale().name()}]")
                break
        else:
            out.append("      ⚠ 没有找到任何 en 开头 locale 的语音！")
except Exception as e:
    out.append(f"  QtTextToSpeech 不可用: {e}")

# ---------- ③ 当前引擎会把音标变成什么串 ----------
out.append("")
out.append("=" * 68)
out.append("③ 当前 _ipa_to_words 的转换结果（这就是问题所在）")
out.append("=" * 68)
try:
    from app import Pronouncer
    # 直接从部署库里取几个词的英美音标
    import sqlite3
    con = sqlite3.connect(r"D:\Dictionary\dict.db")
    con.row_factory = sqlite3.Row
    words = ["water", "can't", "tomato", "schedule", "either", "record",
             "bath", "dance", "hot", "better", "student", "cup",
             "world", "girl", "go", "no", "know", "about", "know",
             "thought", "this", "sing", "cat", "very", "zoo"]
    out.append(f"{'word':<10} {'英式音标':<18} {'→喂给TTS(uk)':<22} "
               f"{'美式音标':<18} {'→喂给TTS(us)'}")
    out.append("-" * 100)
    for w in words:
        r = con.execute("SELECT word, phonetic, phonetic_us FROM dict "
                        "WHERE lower=? LIMIT 1", (w,)).fetchone()
        if not r:
            continue
        uk = r["phonetic"] or ""
        us = r["phonetic_us"] or ""
        a = Pronouncer._ipa_to_words(uk)
        b = Pronouncer._ipa_to_words(us)
        flag = ""
        if not uk:
            flag += " [无英式音标]"
        if not us:
            flag += " [无美式音标]"
        if uk and us and uk == us:
            flag += " [英美音标相同]"
        if a and b and a == b and uk != us:
            flag += " [★转换后相同=听不出区别]"
        if a == w.lower() or b == w.lower():
            flag += " [★转回原词=变成拼读]"
        out.append(f"{w:<10} {uk:<18} {a:<22} {us:<18} {b}{flag}")
    con.close()
except Exception as e:
    out.append(f"  失败: {e}")
    import traceback
    out.append(traceback.format_exc())

# ---------- ④ 统计全库英美音标覆盖率 ----------
out.append("")
out.append("=" * 68)
out.append("④ 词库音标字段覆盖率（决定三种模式能不能真的有区别）")
out.append("=" * 68)
try:
    import sqlite3
    con = sqlite3.connect(r"D:\Dictionary\dict.db")
    tot = con.execute("SELECT COUNT(*) FROM dict").fetchone()[0]
    uk = con.execute("SELECT COUNT(*) FROM dict "
                     "WHERE phonetic IS NOT NULL AND phonetic != ''"
                     ).fetchone()[0]
    us = con.execute("SELECT COUNT(*) FROM dict "
                     "WHERE phonetic_us IS NOT NULL AND phonetic_us != ''"
                     ).fetchone()[0]
    same = con.execute(
        "SELECT COUNT(*) FROM dict WHERE phonetic!='' AND phonetic_us!='' "
        "AND phonetic=phonetic_us").fetchone()[0]
    both = con.execute(
        "SELECT COUNT(*) FROM dict WHERE phonetic!='' AND phonetic_us!=''"
    ).fetchone()[0]
    out.append(f"总词条          : {tot:,}")
    out.append(f"有英式音标      : {uk:,}  ({uk/tot*100:.1f}%)")
    out.append(f"有美式音标      : {us:,}  ({us/tot*100:.1f}%)")
    out.append(f"英美音标都有    : {both:,}")
    if both:
        out.append(f"其中英美完全相同: {same:,}  ({same/both*100:.1f}%)")
    con.close()
except Exception as e:
    out.append(f"  失败: {e}")

open(r"D:\Dictionary\build\_voices.txt", "w", encoding="utf-8").write(
    "\n".join(out))
print("ok")
