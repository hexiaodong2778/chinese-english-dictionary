# -*- coding: utf-8 -*-
"""发音功能测试套件。

覆盖：
  A. 音标清洗逻辑（clean_ipa）—— 核心回归，防止再犯「音节点被当分隔符」的错
  B. 数据库音标数据质量
  C. 在线发音引擎（下载 / 缓存 / 回退）
  D. GUI 集成（按钮 → 状态栏文案）
  E. 打包配置（QtMultimedia 未被排除）
"""
import os
import re
import sqlite3
import sys
import tempfile

sys.path.insert(0, r"D:\Dictionary\build")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

PASS = []
FAIL = []


def check(name, cond, detail=""):
    (PASS if cond else FAIL).append((name, detail))
    return cond


# =====================================================================
# A. clean_ipa 回归测试
# =====================================================================
from clean_ipa import clean_ipa

# A1 音节分隔的 '.' 必须保留（这是最关键的回归点）
check("音节点保留: ә.bri:viˈeiʃәn",
      clean_ipa("ә.bri:vi'eiʃәn") == "ә.bri:vi\u02c8eiʃәn",
      repr(clean_ipa("ә.bri:vi'eiʃәn")))
check("音节点保留: әk.selәˈreiʃәn",
      clean_ipa("әk.selә'reiʃәn") == "әk.selә\u02c8reiʃәn",
      repr(clean_ipa("әk.selә'reiʃәn")))
check("音节点保留: әb.sɒ:bәˈbiliti",
      clean_ipa("әb.sɒ:bә'biliti") == "әb.sɒ:bә\u02c8biliti",
      repr(clean_ipa("әb.sɒ:bә'biliti")))

# A2 前导点（音节省略标记）去掉
check("前导点去掉: .æbiˈniʃiәu",
      clean_ipa(".æbi'niʃiәu") == "æbi\u02c8niʃiәu",
      repr(clean_ipa(".æbi'niʃiәu")))
check("双前导点去掉: ..tʃeindʒәˈbiliti",
      clean_ipa("..tʃeindʒә'biliti") == "tʃeindʒә\u02c8biliti",
      repr(clean_ipa("..tʃeindʒә'biliti")))

# A3 多读音：按「点+空格」切
check("多读音(点+空格): dæns. dɑ:ns -> dæns",
      clean_ipa("dæns. dɑ:ns") == "dæns",
      repr(clean_ipa("dæns. dɑ:ns")))
check("多读音(点+空格): ˈɑ:ftә.mɑ:kit. ˈæf-",
      clean_ipa("'ɑ:ftә.mɑ:kit. 'æf-") == "\u02c8ɑ:ftә.mɑ:kit",
      repr(clean_ipa("'ɑ:ftә.mɑ:kit. 'æf-")))

# A4 多读音：空格+点
check("多读音(空格+点): әdˈvaizi:. .ædvai'zi:",
      clean_ipa("әd'vaizi:. .ædvai'zi:") == "әd\u02c8vaizi:",
      repr(clean_ipa("әd'vaizi:. .ædvai'zi:")))

# A5 多读音：空格+连字符（省略写法）
check("多读音(空格+连字符): disˈæɡriɡeit",
      clean_ipa("dis'æɡriɡeit. -ɡәt. -ɡeit") == "dis\u02c8æɡriɡeit",
      repr(clean_ipa("dis'æɡriɡeit. -ɡәt. -ɡeit")))
check("多读音(空格+连字符): di:.sælinaiˈzeiʃәn",
      clean_ipa("di:.sælinai'zeiʃәn. -ni'z-") ==
      "di:.sælinai\u02c8zeiʃәn",
      repr(clean_ipa("di:.sælinai'zeiʃәn. -ni'z-")))

# A6 括号注释清理
check("圆括号注释: lɪvd (for v.); 'laɪvd (for adj.)",
      clean_ipa("lɪvd (for v.); 'laɪvd (for adj.)") == "lɪvd",
      repr(clean_ipa("lɪvd (for v.); 'laɪvd (for adj.)")))
check("方括号脱壳: [ˈbʌtn]",
      clean_ipa("[\u02c8bʌtn]") == "\u02c8bʌtn",
      repr(clean_ipa("[\u02c8bʌtn]")))

# A7 重音符归一化
check("重音符归一: 'wɒ:tә -> ˈwɒ:tә",
      clean_ipa("'wɒ:tә") == "\u02c8wɒ:tә",
      repr(clean_ipa("'wɒ:tә")))
check("重音符不丢失: ri'kɒ:d",
      "\u02c8" in clean_ipa("ri'kɒ:d"),
      repr(clean_ipa("ri'kɒ:d")))

# A8 边界
check("空串 -> 空串", clean_ipa("") == "")
check("None -> 空串", clean_ipa(None) == "")
check("纯空格 -> 空串", clean_ipa("   ") == "")
check("无音标字符不受损: kʌp", clean_ipa("kʌp") == "kʌp")
check("斜杠残留被去掉: ˈɑɹənsən/",
      clean_ipa("ˈɑɹənsən/") == "ˈɑɹənsən",
      repr(clean_ipa("ˈɑɹənsən/")))

# A9 关键：不能变空
for raw in ["[ˈbʌtn]", "['bækkɔ:t]", "[gi'lespi]", "[ ˈdʒeɪwɔːkə(r) ]",
            "[ˌɪndɪsaɪsɪvnɪs]"]:
    check(f"方括号音标不变空: {raw!r}", clean_ipa(raw) != "", repr(clean_ipa(raw)))


# =====================================================================
# B. 数据库音标质量
# =====================================================================
DEPLOY_DB = r"D:\Dictionary\dict.db"
con = sqlite3.connect(DEPLOY_DB)
con.row_factory = sqlite3.Row
cur = con.cursor()

tot = cur.execute("SELECT COUNT(*) FROM dict").fetchone()[0]
has = cur.execute("SELECT COUNT(*) FROM dict "
                  "WHERE phonetic!='' AND phonetic IS NOT NULL").fetchone()[0]
check("部署库有音标条目 > 250,000", has > 250000, f"实际 {has:,}")
check("部署库覆盖率 > 33%", has / tot > 0.33,
      f"{has/tot*100:.1f}%")

# 音节点应该保留（清洗前 7,175 条含点，其中约 5,940 条是前导点标记、
# 约 1,200 条是多读音混装，都已按规则处理；剩下的是真正的音节分隔）
syl = cur.execute("SELECT COUNT(*) FROM dict WHERE phonetic LIKE '%.%'"
                  ).fetchone()[0]
check("音节点保留（>1000 条）", syl > 1000, f"实际 {syl:,}")

# 关键：音节分隔必须还在（抽查具体条目）
for w, must_contain in [("abbreviation", "ә.bri:vi"),
                        ("acceleration", "әk.selә"),
                        ("aboveboard", "ә.bʌv")]:
    r = cur.execute("SELECT phonetic FROM dict WHERE lower=? LIMIT 1",
                    (w,)).fetchone()
    got = r["phonetic"] if r else ""
    check(f"音节点未被误删: {w}", must_contain in got,
          f"期望含 {must_contain!r}，实得 {got!r}")

# 不应再有前导点
lead = cur.execute("SELECT COUNT(*) FROM dict WHERE phonetic LIKE '.%'"
                   ).fetchone()[0]
check("无前导点残留", lead == 0, f"实际 {lead:,}")

# 不应再有注释残留
paren = cur.execute("SELECT COUNT(*) FROM dict WHERE phonetic LIKE '%(for%'"
                    ).fetchone()[0]
check("无 (for ...) 注释残留", paren == 0, f"实际 {paren:,}")

# 不应有斜杠残留
slash = cur.execute("SELECT COUNT(*) FROM dict WHERE phonetic LIKE '%/%'"
                    ).fetchone()[0]
check("无斜杠残留", slash == 0, f"实际 {slash:,}")

# 重音符统一
ascii_stress = cur.execute(
    "SELECT COUNT(*) FROM dict WHERE phonetic LIKE '%''%'").fetchone()[0]
check("重音符已统一（无 ASCII 撇号）", ascii_stress == 0,
      f"实际 {ascii_stress:,}")

# 关键样本
samples = {
    "abbreviation": "ә.bri:vi\u02c8eiʃәn",
    "water": "\u02c8wɒ:tә",
    "abandon": "ә\u02c8bændәn",
}
for w, expect_uk in samples.items():
    r = cur.execute("SELECT phonetic FROM dict WHERE lower=? LIMIT 1",
                    (w,)).fetchone()
    got = r["phonetic"] if r else None
    check(f"{w} 音标正确", got == expect_uk, f"期望 {expect_uk!r} 实得 {got!r}")

con.close()


# =====================================================================
# C. 发音引擎
# =====================================================================
from PySide6.QtWidgets import QApplication
app = QApplication.instance() or QApplication([])
import app as A

tmp = os.path.join(tempfile.gettempdir(), "cdc_pron_test")
os.makedirs(tmp, exist_ok=True)
p = A.Pronouncer(cache_dir=tmp)

check("Pronouncer 可构造", p is not None)
check("缓存目录已创建", os.path.isdir(p._cache_dir))

# 在线下载
path_us = p._fetch_online("water", "us")
path_uk = p._fetch_online("water", "uk")
check("在线下载美音成功", bool(path_us), path_us)
check("在线下载英音成功", bool(path_uk), path_uk)

if path_us and path_uk:
    import hashlib
    ha = hashlib.sha256(open(path_us, "rb").read()).hexdigest()
    hb = hashlib.sha256(open(path_uk, "rb").read()).hexdigest()
    check("英美录音内容不同", ha != hb, f"{ha[:12]} vs {hb[:12]}")

    # mp3 格式校验
    with open(path_us, "rb") as f:
        head = f.read(4)
    check("下载内容是 mp3", head[:3] == b"ID3" or head[:2] == b"\xff\xfb",
          repr(head))

# 缓存命中要快
import time
t0 = time.time()
p._fetch_online("water", "us")
dt = (time.time() - t0) * 1000
check("缓存命中 < 50ms", dt < 50, f"{dt:.1f}ms")

# 缓存文件名安全（含特殊字符的词）
p2 = A.Pronouncer(cache_dir=tmp)
cp = p2._cache_path("don't", "us")
check("缓存文件名不含非法字符",
      "/" not in os.path.basename(cp) and "\\" not in os.path.basename(cp),
      cp)

# speak 各模式
w_ = A.Pronouncer(cache_dir=tmp)
ok = w_.speak("water", accent="us", lang="en")
check("speak(us) 成功", ok, f"来源={w_._last_source}")
check("speak(us) 用真人录音", w_._last_source == "真人录音",
      w_._last_source)

ok = w_.speak("water", accent="uk", lang="en")
check("speak(uk) 成功", ok, f"来源={w_._last_source}")
check("speak(uk) 用真人录音", w_._last_source == "真人录音",
      w_._last_source)

# 兼容旧的 "global" 参数：现在一律走 Edge 神经语音（Forvo 已于 2026-09-17 移除）
ok = w_.speak("water", accent="global", lang="en")
check("speak(global) 成功", ok, f"来源={w_._last_source}")
check("speak(global) 走在线音源",
      w_._last_source in ("Forvo 全球发音", "真人录音（美音）")
      or w_._last_source.startswith("Edge "),
      w_._last_source)

# Edge 口音模式：必须走 Edge（或更差的回退，但不能啥都没有）
ok = w_.speak("water", accent="edge", lang="en")
check("speak(edge) 成功", ok, f"来源={w_._last_source}")
check("speak(edge) 来源合理",
      w_._last_source.startswith("Edge ") or "真人录音" in w_._last_source
      or "本地语音" in w_._last_source,
      w_._last_source)

# 离线回退
w2 = A.Pronouncer(cache_dir=tmp)
w2.ONLINE_TPL = "https://127.0.0.1:9/x?audio={w}&type={t}"
w2.ONLINE_TIMEOUT = 1
ok = w2.speak("zzzneverheard", accent="us", lang="en")
check("离线回退不失败", ok, f"来源={w2._last_source}")
check("离线回退标记正确", "离线" in w2._last_source, w2._last_source)

# 非英语
ok = w2.speak("bonjour", accent="global", lang="fr")
check("法语路径可用", ok, f"来源={w2._last_source}")

# 关键回归：不调用已删除的 _ipa_to_words
check("_ipa_to_words 已移除（不再自行拼读音标）",
      not hasattr(A.Pronouncer, "_ipa_to_words"))
check("IPA_MAP 已移除（不再做音标替换）",
      not hasattr(A.Pronouncer, "IPA_MAP"))


# =====================================================================
# D. 打包配置
# =====================================================================
spec = open(r"D:\Dictionary\build\app.spec", "r", encoding="utf-8").read()
# 取出 excludes=[ ... ] 之间的内容再判断，避免注释里提到 QtMultimedia 造成误判
import re as _re
_m = _re.search(r"excludes=\[(.*?)\]", spec, _re.S)
_excl = _m.group(1) if _m else ""
# 去掉注释行后再判断
_excl_code = "\n".join(ln for ln in _excl.split("\n")
                       if not ln.strip().startswith("#"))
check("app.spec excludes 中未排除 QtMultimedia",
      "QtMultimedia" not in _excl_code,
      _excl_code.strip()[:120].replace("\n", " "))
check("app.spec 保留图标配置", "app_icon.ico" in spec)

# exe 实际包含 QtMultimedia（比读 spec 更可信）
_exe = r"D:\Dictionary\build\dist\查单词.exe"
if os.path.exists(_exe):
    _blob = open(_exe, "rb").read()
    check("exe 内已打入 QtMultimedia", b"QtMultimedia" in _blob)
    check("exe 内已打入 ffmpeg（mp3 解码）", b"ffmpeg" in _blob.lower())


# =====================================================================
# 结果
# =====================================================================
out = []
out.append("=" * 72)
out.append(f"发音测试：通过 {len(PASS)} / 失败 {len(FAIL)}")
out.append("=" * 72)
if FAIL:
    out.append("")
    out.append("失败项：")
    for n, d in FAIL:
        out.append(f"  ✗ {n}")
        if d:
            out.append(f"      {d}")
out.append("")
out.append("全部结果：")
for n, d in PASS:
    out.append(f"  ✓ {n}" + (f"   [{d}]" if d else ""))

open(r"D:\Dictionary\build\_test_pron.txt", "w", encoding="utf-8").write(
    "\n".join(out))
print(f"PASS={len(PASS)} FAIL={len(FAIL)}")
