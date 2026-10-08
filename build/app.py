"""
极简查单词 · MinimalDict  —  主程序
====================================
一个离线、免安装的极简查单词软件。

功能:
  · 五部词典: 简明 / 牛津 / 四六级 / 高考 / 全部
  · 三种发音模式: 美式 / 英式 / 全球
  · 多语言模式: 英语 / 日语 / 法语 / 粤语  (默认英语)
  · 中译英反查
  · 词形自动还原 (went -> go)
  · 英美双音标并列显示

设计: 纸张质感 + 字典阅读意象，简洁、克制、有书卷气。
"""
import base64
import difflib
import hashlib
import html
import json
import os
import re
import socket
import sqlite3
import ssl
import struct
import sys
import threading
import time
import traceback
import urllib.error
import urllib.parse
import urllib.request
import uuid

from PySide6.QtCore import (Qt, QTimer, QSize, Signal, QPoint, QRectF, QUrl,
                            QObject)
from PySide6.QtGui import (
    QColor, QFont, QFontDatabase, QFontMetrics, QIcon, QLinearGradient, QPainter,
    QPainterPath, QPen, QBrush, QPixmap, QTextCursor, QTextCharFormat,
    QDesktopServices, QGuiApplication,
)
from PySide6.QtWidgets import (
    QApplication, QFrame, QGraphicsDropShadowEffect, QHBoxLayout, QLabel,
    QLineEdit, QListWidget, QListWidgetItem, QMainWindow, QPushButton,
    QScrollArea, QSizePolicy, QSplitter, QStackedWidget, QTextBrowser,
    QTextEdit, QVBoxLayout, QWidget, QComboBox, QButtonGroup,
    QGraphicsOpacityEffect, QMenu, QTabWidget, QInputDialog, QMessageBox,
    QFileDialog, QDialog,
)

# =================================================================== 品牌
# 软件名集中在这里 —— 日后想改名，只改这一处即可全处生效。
#   APP_NAME      窗口标题 / 界面标题 / 应用名 / 日志与缓存目录名
#   APP_NAME_EN   英文名与副标题用
#   APP_SUBTITLE  界面标题下方那行小字
#   APP_SEAL_CHAR 图标上那枚红章里的单字（改字需同步 make_icon.py）
APP_NAME       = "查单词"
APP_NAME_EN    = "MinimalDict"
APP_SUBTITLE   = "离线词典 · 发音需联网"
APP_SEAL_CHAR  = "典"
# 一次打包内不再变动，供 exe / spec / 版本信息共用
APP_EXE_NAME   = APP_NAME

# =================================================================== 配色
# 以纸张 / 墨水为基调的书卷气配色
INK        = "#1f2430"   # 主文字（墨）
INK_SOFT   = "#5c6272"   # 次级文字
INK_FAINT  = "#9aa1b2"   # 弱化文字
PAPER      = "#fbfaf7"   # 纸面
PAPER_ALT  = "#f4f2ec"   # 纸面（略深）
LINE       = "#e6e3da"   # 分割线
RULE_RED   = "#c0392b"   # 字典红（书签/强调）
SEAL       = "#b3352c"   # 印章红
BLUE       = "#2b5fd9"   # 链接蓝
GOLD       = "#b08d4f"   # 烫金

ACCENT = SEAL

LANG_DEFS = {
    "en": {"label": "英语", "flag": "EN", "db": "dict.db"},
    "ja": {"label": "日语", "flag": "あ", "db": "dict_ja.db"},
    "fr": {"label": "法语", "flag": "FR", "db": "dict_fr.db"},
    "yue": {"label": "粤语", "flag": "粵", "db": "dict_yue.db"},
}

# 词典（词表）定义 —— 顺序即界面顺序
DICTS = [
    {"key": "simple", "label": "简明", "desc": "音标 + 中文核心释义"},
    {"key": "oxford", "label": "牛津", "desc": "英文释义 + 中文释义"},
    {"key": "cet",    "label": "四六级", "desc": "CET-4 / CET-6 / 考研"},
    {"key": "gk",     "label": "高考", "desc": "高考考纲词汇"},
    {"key": "all",    "label": "全部", "desc": "全部 77 万词条"},
]


# =================================================================== AI 助手
# 默认保持零配置：点击 AI 按钮时，在系统默认浏览器中打开用户选定的 AI 问答页，
# 并把「预设好的提问」复制到剪贴板，用户 Ctrl+V 即可发送。
# 另提供可选的「DeepSeek 站内」模式：用户主动填写 API Key 后，可直接在软件内
# 对话、追问，并把回答保存到单词笔记；不填 Key 时原浏览器流程完全不受影响。
#
# 为什么是「复制剪贴板」而不是「URL 预填」：
#   实测各国产 AI 站（DeepSeek/豆包/Kimi/元宝/通义）的原生网页**都不认**
#   ?q= 这类预填参数——网上那些「带参直填」教程全是靠浏览器插件（油猴脚本）
#   注入 JS 才生效的。所以直接带参打开只会「打开了但没带上问题」。
#   唯一原生支持 ?q= 预填的是 ChatGPT，因此给它单独保留 prefill 字段（双保险）。
# 好处：零配置、零联网依赖、零隐私风险；代价：结果显示在浏览器里而非软件内。
AI_SERVICES = [
    {
        "key": "doubao",
        "label": "豆包",
        "url": "https://www.doubao.com/chat/",
    },
    {
        "key": "deepseek",
        "label": "DeepSeek",
        "url": "https://chat.deepseek.com/",
    },
    {
        "key": "deepseek_api",
        "label": "DeepSeek 站内",
        "url": "https://chat.deepseek.com/",
        "internal": "deepseek",
    },
    {
        "key": "yuanbao",
        "label": "腾讯元宝",
        "url": "https://yuanbao.tencent.com/chat",
    },
    {
        "key": "kimi",
        "label": "Kimi",
        # Kimi 官方域名已从 kimi.moonshot.cn 迁到 www.kimi.com
        "url": "https://www.kimi.com/",
    },
    {
        "key": "tongyi",
        "label": "通义千问",
        "url": "https://www.qianwen.com/",
    },
    {
        "key": "chatgpt",
        "label": "ChatGPT",
        "url": "https://chatgpt.com/",
        # ChatGPT 是少数原生支持 ?q= 预填的站点
        "prefill": "https://chatgpt.com/?q={q}",
    },
]

# 四类 AI 用途 —— 对应 AskUserQuestion 里用户多选的四项
AI_TASKS = [
    {
        "key": "explain",
        "label": "AI 释义讲解",
        "tip": "用大白话讲解这个词的意思、用法和易混点",
        "prompt": "请用中文讲解{lang}词语「{w}」：1) 核心含义 2) 常见用法与搭配 "
                  "3) 容易混淆的近义词辨析 4) 一个地道例句并附中文翻译。"
                  "请分点作答，简明扼要。",
    },
    {
        "key": "example",
        "label": "例句生成",
        "tip": "为这个词生成贴合语境的例句并附翻译",
        "prompt": "请为{lang}词语「{w}」生成 5 个不同语境的地道例句"
                  "（涵盖日常、正式、书面等场景），每个例句后附中文翻译，"
                  "并标注适用的语体。",
    },
    {
        "key": "writing",
        "label": "造句/写作检查",
        "tip": "把你在搜索框里写的中英文句子交给 AI 纠错润色",
        "prompt": "请检查并润色下面这句话，指出语法或用词问题，"
                  "给出修改后的地道版本和简要说明：\n\n{sentence}",
    },
    {
        "key": "ask",
        "label": "AI 答疑",
        "tip": "围绕这个词自由提问语法、用法、词汇辨析",
        "prompt": "我想了解关于{lang}词语「{w}」的用法。"
                  "请先简要介绍，然后回答我接下来的问题。",
    },
]


# ---------------------------------------------------------- 官方词典直达
# 各类正规词典的官方网址。点击后直接在系统浏览器打开该词的官方页面，
# 看到的就是该词典的原始释义与例句（版权内容不落地到本软件，只做跳转）。
#
# 说明：之所以不做「软件内抓取网页」，是因为抓取会随对方网页改版随时失效，
# 且把受版权保护的正文搬进本软件存在合规风险。跳转最稳、最干净。
OFFICIAL_DICTS = [
    {
        "key": "oxford",
        "label": "牛津",
        "full": "Oxford Learner's Dictionaries",
        "url": "https://www.oxfordlearnersdictionaries.com/definition/english/{w}",
        "note": "英英释义 · 分级例句 · 搭配",
    },
    {
        "key": "cambridge",
        "label": "剑桥",
        "full": "Cambridge Dictionary",
        "url": "https://dictionary.cambridge.org/dictionary/english-chinese-simplified/{w}",
        "note": "英汉双解 · 例句 · 发音",
    },
    {
        "key": "collins",
        "label": "柯林斯",
        "full": "Collins Dictionary",
        # 柯林斯不支持路径式查询，走其站内搜索
        "url": "https://www.collinsdictionary.com/dictionary/english/{w}",
        "note": "语料库释义 · 星级词频",
    },
    {
        "key": "longman",
        "label": "朗文",
        "full": "Longman Dictionary of Contemporary English",
        # 朗文官网已并入 Pearson，用其站内查询
        "url": "https://www.ldoceonline.com/dictionary/{w}",
        "note": "当代英语 · 2000 核心词标注",
    },
    {
        "key": "merriam",
        "label": "韦氏",
        "full": "Merriam-Webster",
        "url": "https://www.merriam-webster.com/dictionary/{w}",
        "note": "美式权威 · 词源考据",
    },
    {
        "key": "vocab",
        "label": "词源",
        "full": "Online Etymology Dictionary",
        "url": "https://www.etymonline.com/word/{w}",
        "note": "词根词源 · 历史演变",
    },
]


# ---------------------------------------------------------------------------
# 常用短语：筛选规则
# ---------------------------------------------------------------------------
# 只有「第二词是小品词 / 常用介词」的多词词条才算短语。
# 这一条是整套筛选的核心 —— 词库里 36.6 万个多词条目中绝大多数是
# 专业术语（break address 中断点地址、call analyzer 呼叫分析器、
# hold area 邮件暂存区），只有靠小品词才能把真正的固定搭配捞出来。
PHRASE_PARTICLES = {
    "up", "off", "on", "out", "in", "into", "away", "back", "down", "over",
    "through", "along", "across", "after", "for", "to", "with", "about",
    "around", "at", "by", "from", "of", "upon", "against", "aside", "apart",
    "ahead", "aboard", "behind", "beyond", "forward", "together", "under",
    "forth", "round", "onto", "aback", "before", "above", "below", "within",
    "without", "past", "toward", "towards", "amid", "among", "between",
}


def _clean_phrase_tr(t):
    """清洗短语译文：去掉换行、领域标记、残余词性缩写，并适度截断。

    ECDICT 的短语译文常常又长又杂（"拿掉, 取消, 脱下, 领走, 减去, 复制,
    起飞, 离开, 岔开\\n[经] 取消"），全部铺出来会把词条撑爆。这里的做法是
    只保留「主要义项」：优先在第一个分号处断，其次在中间逗号处断，
    保证截断点落在义项边界上，不会把某个义项从中间劈开。
    """
    t = (t or "").replace("\\n", " ").replace("\n", " ")
    t = re.sub(r"\[[^\]]{0,12}\]", " ", t)          # [网络] [法] [经]
    t = re.sub(r"^(un|vt|vi|adj|adv|prep|abbr|n|v|num|pron)\.\s*", "",
               t, flags=re.I)                        # 开头词性缩写
    t = re.sub(r"\s+", " ", t).strip(" ,;.\u00b7")

    if len(t) <= 40:
        return t
    # 在 12-40 字之间的分号处断
    for sep in (";", "\uff1b"):
        cut = t.find(sep)
        if 12 <= cut <= 40:
            return t[:cut].strip(" ,;.\u00b7")
    # 退一步：在 16-40 字之间的逗号/顿号处断
    for i in range(len(t) - 1, 15, -1):
        if t[i] in ",\uff0c\u3001" and i <= 40:
            return t[:i].strip(" ,;.\u00b7")
    return t[:38].strip(" ,;.\u00b7") + "\u2026"


PHRASE_SOURCE_NOTE = "词库自带固定搭配 · 按牛津/柯林斯收录度排序"


def ai_build_prompt(task_key, word, sentence="", lang="en"):
    """按用途生成要交给 AI 的提问文本。"""
    lang_name = LANG_DEFS.get(lang, LANG_DEFS["en"]).get("label", "英语")
    for t in AI_TASKS:
        if t["key"] == task_key:
            try:
                return t["prompt"].format(
                    w=word, sentence=sentence or word, lang=lang_name)
            except Exception:
                return t["prompt"]
    return f"请讲解{lang_name}词语「{word}」。"


# =================================================================== 联网词典增强
# 有道词典公开 jsonapi：能拿到英英释义(ee)、柯林斯释义(collins)、同义词(syno)、
# 双语例句(blng_sents_part)。webster/oxford 字段是加密数据(encryptedData)，
# 无法直接解析，故不使用。
# 合规说明：只在联网时实时抓取展示，不把版权正文落盘进本地词库（和「跳转」同理）。
ONLINE_DICT_URL = "https://dict.youdao.com/jsonapi?q={w}"
ONLINE_DICT_TIMEOUT = 3   # 秒；超时静默放弃，不阻塞离线词典

# 有道「建议词条」接口：data.entries[].{entry, explain}。
# entry 与输入一致时，explain 就是这句的中文（形如「我爱你：表达…」）。
SUGGEST_URL = ("https://dict.youdao.com/suggest?num=5&ver=3.0&doctype=json"
               "&cache=false&le=en&q={q}")

# MyMemory 公共翻译接口：**免 key、双向整句**，是「没有有道 key 时」
# 唯一能真正翻译任意长短句的通道（实测 ~1.3~1.6s，见 _translate_mymemory）。
# 匿名额度按 IP 计（约 5000 词/天），个人查句足够。
MYMEMORY_URL = ("https://api.mymemory.translated.net/get"
                "?q={q}&langpair={pair}")
TRANSLATE_TIMEOUT = 8     # 秒；整句翻译比词典查询慢，给足余量

def _strip_html(s):
    return re.sub(r"<[^>]+>", "", s or "").strip()


def _as_list(v):
    """把可能为 None / 标量 / 字典 / 列表的字段统一成列表。

    有道 jsonapi 的同一字段在不同词条下会返回不同形状：
    例如 exam.i.f 有时是 {"l": [...]}，有时直接是字符串或列表。
    不统一处理会在渲染时抛 AttributeError，导致整条词条联网增强失败。
    """
    if v is None:
        return []
    if isinstance(v, str):
        return [v]
    if isinstance(v, dict):
        return [v]
    if isinstance(v, (list, tuple)):
        return list(v)
    return [v]


def _dig(obj, *keys):
    """沿 keys 逐层取值，任一环节缺失/类型不符都安全返回 None。"""
    for k in keys:
        if isinstance(obj, dict):
            obj = obj.get(k)
        elif isinstance(obj, (list, tuple)):
            try:
                obj = obj[k]
            except Exception:
                return None
        else:
            return None
    return obj

def _open_url(req, timeout):
    """统一出口：按配置决定是否走代理。req 可为 Request 或 URL 字符串。

    proxy 留空时行为与之前完全一致（不传 ProxyHandler → 用系统默认）。
    """
    url = req.full_url if hasattr(req, "full_url") else req
    if CONFIG.get("proxy"):
        op = urllib.request.build_opener(urllib.request.ProxyHandler({
            "http": CONFIG["proxy"], "https": CONFIG["proxy"]}))
        return op.open(req, timeout=timeout)
    return urllib.request.urlopen(req, timeout=timeout)


# ================================================================ 真·异步
# ⚠ 为什么需要它（2026-09-17）：
#   本项目原先三处「异步」都是 `QTimer.singleShot(...)` —— 那只把回调
#   **推迟到下一个事件循环**，回调仍然跑在 UI 主线程上。联网请求放进去
#   就等于界面冻结整个请求时长。实测（本机网络）：
#     fetch_cn_en       330~416ms（超时上限 3s）
#     fetch_online_def  417~513ms（超时上限 3s）
#     Edge 语音合成     最坏 EDGE_TIMEOUT = 12s
#   而 `_render` 每次都排一个 fetch_online_def —— 打字时每预览一个词
#   就冻 0.5 秒，这就是用户说的「单词打得很慢」的第三个来源。
#   真异步必须换线程；下面的桥负责把结果安全送回主线程。

class _AsyncBridge(QObject):
    """跨线程回调桥。worker 线程 emit，主线程收。"""
    done = Signal(object)


# 活引用集合：回调送达前不能让桥被 GC 掉，否则信号丢失、回调永不执行。
_ASYNC_ALIVE = set()


def run_async(fn, on_done):
    """在后台线程执行 fn()，完成后在**主线程**调用 on_done(result)。

    Qt 信号跨线程默认走队列连接（QueuedConnection），这里显式指定以
    确保回调一定落在主线程 —— worker 里绝不能碰 Qt 控件。
    fn 抛异常时传 None 给 on_done，不让后台线程静默死掉。
    """
    bridge = _AsyncBridge()
    _ASYNC_ALIVE.add(bridge)

    def _deliver(result):
        try:
            on_done(result)
        except Exception:
            pass
        finally:
            _ASYNC_ALIVE.discard(bridge)

    bridge.done.connect(_deliver, Qt.QueuedConnection)

    def _work():
        try:
            r = fn()
        except Exception:
            r = None
        # ⚠ emit 必须护住：进程正在收尾时，桥的 C++ 对象可能已被销毁
        #   （QApplication 先于本线程析构），此时 emit 会抛
        #   RuntimeError: Signal source has been deleted。
        #   线程是 daemon，这个异常只会在 stderr 打一段吓人的 traceback，
        #   不影响结果 —— 但它会污染测试输出、把真正的错误埋掉
        #   （test_layout2 收尾时就会出现）。回调本来就不该在被销毁的
        #   对象上送达，直接吞掉即正确语义。
        try:
            bridge.done.emit(r)
        except RuntimeError:
            pass

    threading.Thread(target=_work, daemon=True).start()


def fetch_online_def(word):
    """联网获取有道的英文释义/柯林斯/同义词/双语例句，返回 dict；失败返回 {}。"""
    try:
        url = ONLINE_DICT_URL.format(w=urllib.parse.quote(word))
        req = urllib.request.Request(
            url, headers={"User-Agent": "Mozilla/5.0"})
        with _open_url(req, ONLINE_DICT_TIMEOUT) as r:
            obj = json.loads(r.read().decode("utf-8", "replace"))
    except Exception:
        return {}

    out = {"english": [], "collins": [], "synos": [], "examples": []}

    # 英英释义（ee）+ 释义自带例句
    # 注意：这里全程用 _as_list/_dig 做容错遍历 —— 有道的同一字段
    # 可能返回 str / list / dict 三种形状，硬取 .get 会抛 AttributeError。
    ee = obj.get("ee") or {}
    for tr in _as_list(_dig(ee, "word", "trs")):
        pos = (tr or {}).get("pos") or "" if isinstance(tr, dict) else ""
        for t in _as_list(_dig(tr, "tr")):
            l = _dig(t, "l") or {}
            text = "".join(_as_list(_dig(l, "i")))
            if text:
                out["english"].append((pos, text))
            exam = _dig(t, "exam") or {}
            for f in _as_list(_dig(exam, "i", "f")):
                for line in _as_list(_dig(f, "l")):
                    for s in _as_list(_dig(line, "i")):
                        s = (s or "").strip()
                        if s:
                            out["examples"].append(s)
            break
        break

    # 柯林斯释义（collins）
    ce = obj.get("collins") or {}
    for entry in _as_list(_dig(ce, "collins_entries")):
        for e in _as_list(_dig(entry, "entries", "entry")):
            for te in _as_list(_dig(e, "tran_entry")):
                if not isinstance(te, dict):
                    continue
                pe = te.get("pos_entry") or {}
                pos = (pe or {}).get("pos") or "" if isinstance(pe, dict) else ""
                tran = _strip_html(te.get("tran"))
                if tran:
                    out["collins"].append((pos, tran))
                for s in _as_list(_dig(te, "exam_sents", "sent")):
                    if not isinstance(s, dict):
                        continue
                    en = _strip_html(s.get("eng_sent"))
                    cn = s.get("chn_sent") or ""
                    if en:
                        out["examples"].append((en, cn))
                break
            break
        break

    # 同义词（syno）
    syno = obj.get("syno") or {}
    for s in _as_list(_dig(syno, "synos")):
        syn = _dig(s, "syno") or {}
        pos = (syn or {}).get("pos") or "" if isinstance(syn, dict) else ""
        ws = [w["w"] for w in _as_list(_dig(syn, "ws"))
              if isinstance(w, dict) and w.get("w")]
        if ws:
            out["synos"].append((pos, ws))

    # 双语例句（blng_sents_part）
    blng = obj.get("blng_sents_part") or {}
    for s in _as_list(_dig(blng, "sentence-pair"))[:4]:
        if not isinstance(s, dict):
            continue
        en = _strip_html(s.get("sentence-eng"))
        cn = s.get("sentence-translation") or ""
        if en:
            out["examples"].append((en, cn))

    return out


# ======================================================= 中译英（补缺义项）
# 为什么需要这个：
#   ECDICT 是「英文词 → 中文释义」的词表，反向查询只能靠中文释义的字面匹配。
#   查「开心」出不来 happy，不是因为排序错，而是因为词库里 happy 的释义是
#   「快乐的, 幸福的, 愉快的, 恰当的」—— 压根没有「开心」这两个字。
#   词库缺失的是「中文近义词映射」，任何纯离线排序都救不了。
#
#   有道的 ce（汉英）词表正好补上这一层：它给出中文词对应的英文表达，
#   例如「开心」→ feel happy / be delighted / have a good time。
#   拿到这些英文表达后，再回本地词库查完整词条，就能给出规范的英文词
#   加上权威释义，而不是凭空捏造。
#
# 与现网增强一样走异步，绝不阻塞打字。
CN_EN_URL = ("https://dict.youdao.com/jsonapi?q={q}"
             "&dicts=%7B%22count%22%3A99%2C%22dicts%22%3A%5B%5B%22ce%22%5D%5D%7D")

# ce 返回的英文表达里混着这些虚词，单独出现时没有查询价值
_CN_EN_STOP = {
    "be", "a", "an", "the", "to", "of", "in", "on", "at", "for", "with",
    "have", "get", "make", "do", "take", "go", "and", "or", "is", "are",
    "was", "were", "it", "that", "this", "feel", "feeling", "one", "s",
}


def fetch_cn_en(word):
    """查中文词的英文表达候选，返回去重后的英文单词列表（保持原顺序）。

    只保留「像单词/短语」的项：纯字母、可含空格连字符、长度 2~24。
    过滤掉 "feel"、"be" 这类虚词 —— 它们单独查出来毫无意义，
    但 "feel happy" / "be delighted" 这种整体是有价值的，所以
    先按整串判断，只有当整串是单个虚词时才丢。
    """
    try:
        url = CN_EN_URL.format(q=urllib.parse.quote(word))
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with _open_url(req, ONLINE_DICT_TIMEOUT) as r:
            obj = json.loads(r.read().decode("utf-8", "replace"))
    except Exception:
        return []

    ce = obj.get("ce") or {}
    if not isinstance(ce, dict):
        return []

    out, seen = [], set()
    for wd in _as_list(ce.get("word")):
        for trs in _as_list(_dig(wd, "trs")):
            for tr in _as_list(_dig(trs, "tr")):
                l = _dig(tr, "l") or {}
                if not isinstance(l, dict):
                    continue
                items = _as_list(l.get("i"))
                buf = []
                for it in items:
                    if isinstance(it, dict):
                        t = (it.get("#text") or "").strip()
                        if t:
                            buf.append(t)
                    elif isinstance(it, str):
                        t = it.strip()
                        # 纯分隔符（空格/标点）不参与拼接，但要保留断词信息
                        if t and not t.isascii():
                            buf.append(t)
                        elif t:
                            buf.append(t)
                word_en = " ".join(buf).strip()
                word_en = _strip_html(word_en)
                word_en = re.sub(r"\s+", " ", word_en).strip()
                if not word_en or len(word_en) > 28:
                    continue
                low = word_en.lower()
                # 纯单虚词丢弃（"feel" / "be"），整体短语保留
                if low in _CN_EN_STOP:
                    continue
                if low in seen:
                    continue
                if not re.fullmatch(r"[A-Za-z][A-Za-z '\-]*", word_en):
                    continue
                seen.add(low)
                out.append(word_en)
    return out[:12]


# =================================================================== 翻译
# 有道官方翻译 API（需 appKey/appSecret，免费版每天约 500 次，注册可拿）。
# 无 key 时用有道 jsonapi 做「词典式」兜底（对词/常见句有效，整句需 key）。
#
# key 从 exe 同目录 dict_config.json 读（见「本地配置」一节），
# 也可直接把值填在下面两行 —— 配置优先级高于此处。
YOUDAO_APP_KEY = ""
YOUDAO_APP_SECRET = ""

def youdao_key():
    """返回 (appKey, appSecret)：配置文件优先，其次源码内置常量。"""
    k = CONFIG.get("youdao_app_key") or YOUDAO_APP_KEY
    s = CONFIG.get("youdao_app_secret") or YOUDAO_APP_SECRET
    return k.strip(), s.strip()

def _truncate_q(q):
    if len(q) <= 20:
        return q
    return q[:10] + str(len(q)) + q[-10:]

def _has_cjk(text):
    """含任意中日韩统一表意文字。

    ⚠ 它**不等于**「是中文」—— 日语也用汉字（学校、水），见 _is_zh_text。
    """
    for ch in text or "":
        if "\u4e00" <= ch <= "\u9fff":
            return True
    return False


def _has_kana(text):
    """含平假名 / 片假名 → 是日语。用来把「日语汉字词」从「中文」里分出来。"""
    for ch in text or "":
        if "\u3040" <= ch <= "\u30ff":
            return True
    return False


def _is_zh_text(text):
    """是不是中文：含汉字且**不含假名**。

    只看汉字不够 —— 日语里「学校」「水」跟中文同形，必须靠假名分开：
        学校        → 中文（日语里同形，无法用字符区分，按中文处理）
        学校へ行く   → 日语（有假名）
        私は学生です → 日语
    """
    return _has_cjk(text) and not _has_kana(text)


# ---------------------------------------------------------- 多语言翻译语言对
# 2026-09-18 新增。此前 translate_text 把语言对写死成 zh-CN|en，
# 于是切到日语/法语模式下点「翻译」，翻的仍是中英 —— 用户反馈
# 「除了英语的其他语言为啥不能双向翻译」。
#
# 免费通道的能力边界（本机实测 2026-09-18，见 _tr_probe6.py / _tr_probe7.py）：
#   MyMemory  ✓ 多语言双向都通，整句质量好：
#               ja|zh-CN 「これは本です」→「这是一本书」
#               zh-CN|ja 「今天天气很好」→「今日はいい天気ですね」
#               yue|zh-CN「點解」→「为什么」／ zh-CN|yue「吃饭」→「食飯」
#               （词级：日语多数可用，「食べる」→「吃」；
#                粤语几乎全对；法语偏差，「je」→「Bruh」）
#   有道 suggest / web_trans / blng_sents
#             ✗ 只有中英。实测 suggest 查日语词「食べる」返回 0 条，
#               查「eau」返回的是**英文词** eau 的释义（不是法语）。
#               所以非英语语言对只有 MyMemory 一条通道，别去试注定为空的通道。
TR_MYMEMORY = {"en": "en", "ja": "ja", "fr": "fr", "yue": "yue"}
ZH_MM = "zh-CN"          # MyMemory 的中文码
ZH_YD = "zh-CHS"         # 有道智云的中文码


def tr_lang_pair(text, lang="en"):
    """按输入内容 + 当前语言模式决定 (源语言, 目标语言)。

    规则只有一条，与查词的自动识别方向保持一致：
        输入是中文     → 译成当前语言
        输入不是中文   → 译成中文
    于是「中 ⇄ 日」「中 ⇄ 法」「中 ⇄ 粤」全都是自动的，无需手动切方向。
    """
    code = TR_MYMEMORY.get(lang, "en")
    if _is_zh_text(text):
        return ZH_MM, code
    return code, ZH_MM


def _norm_sent(s):
    """句子归一化：去 HTML、去空格与标点、转小写。仅供相似度比较。"""
    s = _strip_html(s or "").lower()
    s = re.sub(r"[\s\u3000]+", "", s)
    return re.sub(r"[^\w\u4e00-\u9fff]", "", s)


def _sim(a, b):
    """两个**已归一化**字符串的相似度 0~1（相同 = 1.0）。"""
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0
    return difflib.SequenceMatcher(None, a, b).ratio()


def _same_sentence(cand, inp):
    """cand 是否就是 inp 这句**本身**（而不是「碰巧包含 inp 的另一句」）。

    这是「例句冒充译文」的**闸门**，判定必须严：
      · 完全相同 → 通过
      · 一方几乎完全包含另一方（占比 ≥ 0.9）→ 通过
        （容忍标点/大小写差异，例如 "I love you" vs "I love you."）
      · 其余一律不通过。例如
          inp  = "I love you."
          cand = "Oh, Amy, I love you."   → 「iloveyou」占 13 字符中的 9
                                           = 0.69 < 0.9 → **拒绝**
        正是这一条，把旧版吐出的「啊，埃米，我爱你。」挡在了门外。
    """
    a, b = _norm_sent(cand), _norm_sent(inp)
    if not a or not b:
        return False
    if a == b:
        return True
    short, long_ = (a, b) if len(a) <= len(b) else (b, a)
    if len(short) < 4:          # 太短没有判别力（"ok" 之类）
        return False
    return len(short) / len(long_) >= 0.9


def _is_phrase_like(text):
    """短且无句末标点 → 视为短语/词，而非整句。用于决定通道顺序。"""
    t = (text or "").strip()
    if len(t) > 24:
        return False
    return not any(c in t for c in "。！？!?；;，,.")


def _tr_candidates(text):
    """把机翻结果切成「可能命中本地词库」的候选片段。

    机翻返回的东西往往不是干净的一个词：
        「ありがとうございます）。」  → ['ありがとうございます']
        'eau， 水'                  → ['eau', '水']
        '今日はいい天気ですね'        → ['今日はいい天気ですね']
    这里只做**去噪**（括号注释、标点、空白），不做任何猜测，
    切出来的片段原样交给本地词库去匹配。
    """
    s = (text or "").strip()
    if not s:
        return []
    s = re.sub(r"[（(【\[][^）)】\]]*[）)】\]]", " ", s)      # 去括号注释
    out = []
    for part in re.split(r"[，,、；;。/／|]+", s):
        # ⚠ 括号也要从两端剥掉：机翻常给出**落单的一半**括号，例如
        #   「ありがとうございます）。」—— 开括号在前一段里被切走或本来
        #   就没有，上面那条「去括号注释」的正则要求成对，匹配不到。
        #   不剥的话这个「）」会跟着一起交给词库，必然查不到。
        p = part.strip().strip("。！？!?“”‘’\"'.·-—… \t"
                               "（）()【】[]〔〕「」『』")
        p = p.strip()
        p = re.sub(r"\s+", " ", p).strip()
        if p and len(p) <= 40 and p not in out:
            out.append(p)
    if not out:
        out = [s[:40]]
    return out


def _mymemory_raw(text, pair, allow_same=False):
    """MyMemory 底层查询：pair 形如 'ja|zh-CN'。返回 (译文, 来源) 或 (None, None)。

    allow_same=True 时允许「译文 == 原文」（同形词，如日语「水」→中文「水」）。
    翻译对话框那条路径必须保持 False —— 否则服务端把原文回显回来
    就会被当成译文（旧版「例句冒充译文」的同类陷阱）。
    词条释义那条路径则要用 True：日语汉字与中文同形是常态，
    同形恰恰说明意思一致，直接丢弃反而让用户看到「未取到」。
    """
    url = MYMEMORY_URL.format(q=urllib.parse.quote(text),
                              pair=urllib.parse.quote(pair))
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with _open_url(req, TRANSLATE_TIMEOUT) as r:
            obj = json.loads(r.read().decode("utf-8", "replace"))
    except Exception:
        return None, None
    if str(obj.get("responseStatus")) != "200":
        return None, None
    t = _strip_html((obj.get("responseData") or {}).get("translatedText"))
    t = re.sub(r"\s+", " ", t or "").strip()
    # 译文与原文一模一样说明它没翻（MyMemory 对未知内容会回显原文）
    if not t:
        return None, None
    if not allow_same and _norm_sent(t) == _norm_sent(text):
        return None, None
    return t, "MyMemory 在线翻译"


def _translate_mymemory(text, lang="en"):
    """通道：MyMemory 公共翻译接口（免 key、双向整句、多语言）。

    实测（2026-09-18，本机 ~1.3~1.9s）：
      EN→CN "The weather is really nice today, so I want to go out for a walk."
            → 今天天气非常好，所以我想出去散步。
      CN→EN 「我今天早上起晚了，所以没赶上公交车，只好打车去公司。」
            → I got up late this morning, so I didn't catch the bus, so I
              had to take a taxi to the company.
      JA→CN 「これは本です」→ 这是一本书
      CN→JA 「今天天气很好」→ 今日はいい天気ですね
      YUE→CN「點解」→ 为什么　　CN→YUE「吃饭」→ 食飯

    语言对由 tr_lang_pair 按输入内容与当前语言模式算出，
    所以它同时承担 en/ja/fr/yue 四种模式的主通道。
    返回 (译文, 来源) 或 (None, None)。
    """
    src, dst = tr_lang_pair(text, lang)
    return _mymemory_raw(text, "%s|%s" % (src, dst))


def _translate_youdao_phrase(text):
    """通道：有道 suggest（建议词条）+ web_trans（网络释义）。

    免 key、快（实测 ~230ms），**对词/短语/成语质量最好**：
      「一举两得」 → kill two birds with one stone
      "I love you." → 我爱你
    对整句会返回空，此时返回 (None, None) 交给下一条通道。

    ⚠ 顺序：**suggest 在前**。两者都能命中短语，但实测 web_trans 会给出
      被截断的条目（「一举两得」的第一条是 'Kill two birds'，完整说法
      在第四条），而 suggest 直接给完整表达。suggest 未命中才退回 web_trans。
    """
    want_cn = not _has_cjk(text)

    # ① suggest：建议词条，explain 形如「我爱你：表达对某人深深的爱意」
    #    只有 entry 与输入一致时，explain 才是这句的翻译
    try:
        req = urllib.request.Request(
            SUGGEST_URL.format(q=urllib.parse.quote(text)),
            headers={"User-Agent": "Mozilla/5.0"})
        with _open_url(req, ONLINE_DICT_TIMEOUT) as r:
            obj = json.loads(r.read().decode("utf-8", "replace"))
    except Exception:
        obj = {}
    for e in _as_list(_dig(obj, "data", "entries")):
        if not isinstance(e, dict):
            continue
        if not _same_sentence(e.get("entry"), text):
            continue
        ex = _strip_html(e.get("explain"))
        ex = re.sub(r"\s+", " ", ex or "").strip()
        if not ex:
            continue
        # 「译文：补充说明」→ 只取冒号前那一段（那才是译文）
        for sep in ("：", ":", "。"):
            if sep in ex:
                head = ex.split(sep, 1)[0].strip()
                if head:
                    ex = head
                break
        if ex and _has_cjk(ex) == want_cn:
            return ex, "有道词典"

    # ② web_trans：网络释义，按社区投票排序，取第一条异语言项
    try:
        req = urllib.request.Request(
            ONLINE_DICT_URL.format(w=urllib.parse.quote(text)),
            headers={"User-Agent": "Mozilla/5.0"})
        with _open_url(req, ONLINE_DICT_TIMEOUT) as r:
            obj = json.loads(r.read().decode("utf-8", "replace"))
    except Exception:
        return None, None
    out = None
    wt = obj.get("web_trans") or {}
    for x in _as_list(wt.get("web-translation")):
        for tr in _as_list(_dig(x, "trans")):
            v = _strip_html(tr.get("value") if isinstance(tr, dict) else tr)
            v = re.sub(r"\s+", " ", v or "").strip()
            if not v or len(v) > 60:
                continue
            # 只要与输入「异语言」的那一条（英输入要中文释义，反之亦然）
            if _has_cjk(v) == want_cn:
                out = v
                break
        if out:
            break
    if out:
        return out, "有道网络释义"
    return None, None


def _translate_youdao_example(text):
    """通道：有道双语例句，**最佳匹配 + 原句闸门**。

    这是唯一天然免 key 的英文对照来源，但它给的是「例句」不是「翻译」。
    只有输入本身跟例句的**源语言侧**几乎一致时，例句的译文才等于
    输入的译文 —— 此时才采用；否则返回 (None, None) 让上层诚实报错。

    ⚠ 旧版就是错在这里：它取 sents[0] 且不校验。实测
        "I love you." 的 sents[0] 是 "Oh, Amy, I love you."
        → 吐给用户的是「啊，埃米，我爱你。」
      而正确答案就在同一个数组的 sents[1]（sentence-eng 恰为
      "I love you."）。本函数遍历全部候选、过闸门、取相似度最高者，
      所以拿到的会是 sents[1]。
    """
    try:
        req = urllib.request.Request(
            ONLINE_DICT_URL.format(w=urllib.parse.quote(text)),
            headers={"User-Agent": "Mozilla/5.0"})
        with _open_url(req, ONLINE_DICT_TIMEOUT) as r:
            obj = json.loads(r.read().decode("utf-8", "replace"))
    except Exception:
        return None, None

    blng = obj.get("blng_sents_part") or {}
    best, best_sc = None, 0.0
    for s in _as_list(_dig(blng, "sentence-pair")):
        if not isinstance(s, dict):
            continue
        src_side = _strip_html(s.get("sentence-eng"))
        tgt_side = _strip_html(s.get("sentence-translation"))
        if not src_side or not tgt_side:
            continue
        if not _same_sentence(src_side, text):
            continue
        sc = _sim(_norm_sent(src_side), _norm_sent(text))
        if sc > best_sc:
            best_sc, best = sc, re.sub(r"\s+", " ", tgt_side).strip()
    if best:
        return best, "有道词典（原句对照）"
    return None, None


def translate_text(text, lang="en", strict=True):
    """翻译句子/段落（自动检测方向，中文 ⇄ 当前语言）。

    返回 (译文, 来源) 或 (None, 错误信息)。

    lang = 当前语言模式（en / ja / fr / yue），决定了「中文的那一半
    要换成什么语言」：
        英语模式：中文 ⇄ 英语      日语模式：中文 ⇄ 日语
        法语模式：中文 ⇄ 法语      粤语模式：中文 ⇄ 粤语

    多通道链，**任何一条拿不到结果就换下一条**，绝不再拿例句冒充译文
    （见文件上方「整句翻译」段的说明）。

    ⚠ 通道顺序按语言分开（2026-09-18）：
      中英 → 短语型先有道（成语/搭配质量最好），整句型先 MyMemory
      其他语言 → 只有 MyMemory 一条。有道那三条通道只覆盖中英，
                 对日语词实测返回 0 条、对法语词返回的是**英文词**的
                 释义，拿去用只会再次产出「莫名其妙的句子」。

    strict=True（默认，供翻译对话框用）时，**结果还要过语言闸门**：
    免 key 的 MyMemory 是众包翻译记忆库，短句经常串语言 ——
    实测「我爱你」中→法返回 "I Love You"（英语冒充法语）、
    「Je suis ton ami」法→中返回「你什么也别愁」（语义完全错）、
    中→粤只做简→繁转换（点解→點解，等于没翻）。
    与其把这些当译文给用户，不如按项目原则**如实报错 + 给网页翻译退路**。

    strict=False 用于「中文反查外语词」那条路径：那里要的就是
    简→繁转换（粤词库收的是繁体字形），不能拿闸门把它挡掉。
    """
    text = (text or "").strip()
    if not text:
        return None, "请输入要翻译的内容"

    src, dst = tr_lang_pair(text, lang)
    dst_yd = ZH_YD if dst == ZH_MM else dst
    api_err = ""
    bad = ""

    # 通道 1：配了有道智云 key 就用它 —— 最准，且能翻任意长句。
    #   源语言交给 auto：用户输入的是中文还是外语由服务端判断，
    #   比正则猜可靠（法语的拉丁字母跟英语没法用字符区分）。
    if all(youdao_key()):
        r, s = _translate_api(text, dst_yd)
        if r:
            return r, s
        api_err = s

    # 通道 2~4：中英专用通道（suggest / web_trans / 双语例句）。
    #   非英语模式一条都不试 —— 它们对日语词返回空、对法语词返回英文释义。
    mm = lambda t: _translate_mymemory(t, lang)
    if lang == "en":
        if _is_phrase_like(text):
            chain = (_translate_youdao_phrase, mm, _translate_youdao_example)
        else:
            chain = (mm, _translate_youdao_phrase, _translate_youdao_example)
    else:
        chain = (mm,)

    for fn in chain:
        r, s = fn(text)
        if not r:
            continue
        if lang != "en" and strict:
            ok, why = _tr_result_ok(text, r, lang)
            if not ok:
                bad = why          # 记下拒收原因，继续试下一条通道
                continue
        return r, s

    lab = LANG_DEFS.get(lang, {}).get("label", "")
    if bad:
        return None, (bad + "  可点「网页翻译」在浏览器里翻译"
                      "（中文 ⇄ %s），或在 dict_config.json 填入 "
                      "youdao_app_key 获得稳定的整句翻译。" % lab)
    if api_err and all(youdao_key()):
        return None, api_err
    if lang == "en":
        return None, ("翻译暂不可用（网络不通或额度用尽）。"
                      "可点「网页翻译」在浏览器里翻译，"
                      "或在 dict_config.json 填入 youdao_app_key 获得稳定整句翻译。")
    return None, ("翻译暂不可用（网络不通或额度用尽）。"
                  "可点「网页翻译」在浏览器里翻译"
                  "（中文 ⇄ %s）。" % lab)


# --- 译文质量闸门（2026-10-08）------------------------------------------
# MyMemory 是**众包翻译记忆库**，命中质量看运气，短句尤其容易串语言。
# 下面这组判据都是「粗判据，宁可放过也不误杀」——
# 判据只用来拦住「明显不是目标语言」的结果，不用来评价译文好坏。
_FR_MARK = set("éèêëàâçîôûùœïÉÈÊËÀÇ")
# 法语高频虚词/常用词。⚠ 必须**按词**比对，不能拿 "ou " 这类带空格的
#   串做子串匹配 —— "I love you" 里就有个 "ou "（y**ou** ），
#   第一版因此把英语当法语放行了（本项目实测数据）。
_FR_WORDS = set("""le la les un une des est suis je tu vous il elle nous
ils elles et ou ne pas ce cette avec pour dans sur bonjour merci amour
jour heure tout plus bien tres mon ma mes ton ta tes son sa ses notre vos
leur sont etre avoir fait aussi comme entre chez sans sous dont peut""".split())
# 英语高频词：用来抓「英语冒充法语」（实测 "I Love You" 冒充法语译文）
_EN_WORDS = set("""i you he she it we they the a an is are am was were
love this that these those my your have has do does to of in on and or but
with for be been will can not me him her them us""".split())
# 粤式特有字（繁体中文里不会有的那些）
_YUE_CHARS = set("係唔嘅咗喺佢哋冇嘢咩攞邊度乜噉唞冚啱睇搵嗰啲諗嘟咪")


def _fr_tokens(t):
    return set(re.findall(r"[a-zà-ÿ]+", t.lower()))


def _looks_like_target(out, lang, src_text=""):
    """译文看起来确实是 lang 吗？lang 用 en/ja/fr/yue（zh 一律放行）。"""
    t = (out or "").strip()
    if not t:
        return False
    # 原文回显 = 根本没翻
    if src_text and _norm_sent(t) == _norm_sent(src_text):
        return False
    if lang in ("en", "zh"):
        return True
    if lang == "ja":
        # 日语几乎必有假名；但「大好き」这种无假名的熟词表达也认，
        # 所以规则是：含假名，或完全不含拉丁字母。
        return bool(re.search(r"[\u3040-\u30ff]", t)) \
            or not re.search(r"[A-Za-z]", t)
    if lang == "fr":
        if any(c in t for c in _FR_MARK):
            return True
        words = _fr_tokens(t)
        if words & _FR_WORDS:
            return True
        # 没有法语特征、却塞满英语虚词 → 多半是英语冒充法语
        return not (words & _EN_WORDS)
    if lang == "yue":
        # 中→粤实测只做简繁转换，所以「有粤式字」才算真的翻了
        return any(c in t for c in _YUE_CHARS)
    return True


def _roundtrip_ok(src_text, translated, lang, thresh=0.5):
    """回译校验：把译文再翻回原语言，对不上就说明它不忠实于原文。

    只对实测翻过车的那一类用（法语 → 中文：MyMemory 会从记忆库里
    捞一条语义无关的句子）。校验通道自己失败时**不连坐**好译文。
    """
    try:
        back, _ = _translate_mymemory(translated, lang)
    except Exception:
        return True
    if not back:
        return True
    return _sim(_norm_sent(back), _norm_sent(src_text)) >= thresh


def _tr_result_ok(src_text, out, lang):
    """免 key 通道的结果够不够格当译文。返回 (ok, 拒收原因)。"""
    if not _looks_like_target(out, lang, src_text):
        if lang == "yue":
            return False, ("免费通道的「粤语」目前只做简→繁转换"
                           "（点解→點解），给不出粤式表达。")
        if lang == "fr":
            return False, "通道返回的内容不像法语，已拒收。"
        if lang == "ja":
            return False, "通道返回的内容不像日语，已拒收。"
        return False, "通道返回的内容与目标语言不符，已拒收。"
    # 法→中方向实测会捞到语义无关的句子，加一道回译校验
    if lang == "fr" and not _is_zh_text(src_text):
        if not _roundtrip_ok(src_text, out, lang):
            return False, ("译文未通过回译校验（通道返回了不相关的"
                           "句子），已拒收。")
    return True, ""


def _translate_api(text, to_code=ZH_YD):
    """有道智云翻译 API（需 key）。to_code 是**目标语言**的有道码。"""
    import hashlib
    app_key, app_secret = youdao_key()
    salt = str(int(time.time() * 1000))
    curtime = str(int(time.time()))
    sign_str = (app_key + _truncate_q(text) + salt + curtime + app_secret)
    sign = hashlib.sha256(sign_str.encode("utf-8")).hexdigest()
    body = urllib.parse.urlencode({
        "q": text, "from": "auto", "to": to_code or ZH_YD,
        "appKey": app_key, "salt": salt, "sign": sign,
        "signType": "v3", "curtime": curtime,
    }).encode()
    try:
        req = urllib.request.Request(
            "https://openapi.youdao.com/api", data=body,
            headers={"Content-Type": "application/x-www-form-urlencoded"})
        with _open_url(req, 6) as r:
            obj = json.loads(r.read().decode("utf-8", "replace"))
    except Exception:
        return None, "网络不可用，请稍后重试"
    if str(obj.get("errorCode")) == "0":
        return "".join(obj.get("translation") or []), "有道翻译"
    return None, f"翻译失败（错误码 {obj.get('errorCode')}）"

def _translate_fallback(text):
    """【已废弃 2026-09-18】保留函数名仅为兼容外部引用。

    ⚠ 原实现把**整句**丢进 ONLINE_DICT_URL（词典查询接口）并取
      blng_sents_part 里**第一条**例句的译文 —— 那是「例句的译文」，
      不是「输入的译文」，于是吐出一堆莫名其妙的句子：
        「一举两得」→ "If you enjoy the coast and the country, ..."
        「我要买 a new computer」→ "My computer sucks!"
        "Where are you from?" → 「顺便问一下，你来自哪里？」
      现在这条路径由 _translate_youdao_example（带原句闸门）承担。
    """
    return _translate_youdao_example(text)


def app_dir():
    """返回程序所在目录。

    打包成 exe 后，sys._MEIPASS 指向临时解包目录，不能用来找外置词库；
    必须用 sys.executable 所在目录，才能真正定位到 exe 同级的 .db 文件。
    """
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


def resource_path(name):
    """定位资源文件：优先程序同目录，其次打包内嵌目录。"""
    # 1) 程序同目录（词库外置方案）
    p = os.path.join(app_dir(), name)
    if os.path.exists(p):
        return p
    # 2) 打包内嵌目录（若词库被打进 exe）
    base = getattr(sys, "_MEIPASS", None)
    if base:
        p2 = os.path.join(base, name)
        if os.path.exists(p2):
            return p2
    # 3) 开发模式：build 子目录
    p3 = os.path.join(app_dir(), "build", name)
    if os.path.exists(p3):
        return p3
    return os.path.join(app_dir(), name)


def open_db(name):
    p = resource_path(name)
    if not os.path.exists(p):
        return None
    try:
        con = sqlite3.connect(p, check_same_thread=False)
        con.row_factory = sqlite3.Row
        # ⚠ 性能调优（2026-09-17）：词库有 399MB，而 SQLite 默认只给
        #   约 8MB 页缓存（cache_size=-2000）—— 前缀/区间扫描每碰到
        #   一个新页就要读盘，实测某些前缀「首次」输入要 130ms+，
        #   表现为「头几次打字明显顿一下，之后顺了」。
        #   这是一份**只读**词库（程序从不写它），所以：
        #     cache_size 64MB + mmap_size 256MB + temp_store 内存
        #   三项都是纯收益。mmap 在只读场景尤其划算：省掉 read() 拷贝。
        #   放在 try 里单独兜底：老 SQLite 或特殊文件系统上 PRAGMA
        #   不被支持时不能因此打不开词库。
        try:
            con.execute("PRAGMA cache_size=-64000")     # 64MB 页缓存
            con.execute("PRAGMA mmap_size=268435456")   # 256MB 内存映射
            con.execute("PRAGMA temp_store=MEMORY")     # 排序用内存临时表
        except Exception:
            pass
        return con
    except Exception:
        return None


# ================================================================ 本地配置
# 可选功能的密钥 / 偏好放在 exe 同目录的 dict_config.json，**改完不必重新打包**。
# 之所以不写死在源码里：源码会被复制分发，密钥写在 py 里容易跟着泄露；
# 放 JSON 后由用户自己填、自己保管。程序读不到文件一律用内置默认值，绝不报错。
#
# 支持的键（都可省略，值为空串等同于没配）：
#   "edge_accent"       Edge 口音代号，如 "en-US-AvaNeural"（见 EDGE_ACCENTS）
#   "youdao_app_key"    有道翻译 appKey        → 启用整句/整段翻译（须与下一条成对）
#   "youdao_app_secret" 有道翻译 appSecret
#   "deepseek_api_key"  DeepSeek API Key      → 启用软件内 AI 助手
#   "deepseek_model"    DeepSeek 模型名，默认 deepseek-chat
#   "deepseek_base_url" 接口地址，默认 https://api.deepseek.com
#   "deepseek_timeout"  请求超时秒数，默认 75
#   "proxy"             形如 "http://127.0.0.1:7890" → 所有在线功能统一走代理
#
# 注：曾支持 "forvo_key"（Forvo 全球真人发音），2026-09-17 已废弃 ——
# Forvo 整站要过 Cloudflare 人机验证、且发 key 的接口早已关停，无法使用。
# 老的配置文件里若还留着这个键，程序会忽略它（不报错），无需手动删除。
#
# 查找顺序：① exe 同目录 dict_config.json ② %LOCALAPPDATA%\<APP_NAME>\dict_config.json
CONFIG_FILE = "dict_config.json"
CONFIG_TEMPLATE = {
    "edge_accent": "",
    "youdao_app_key": "",
    "youdao_app_secret": "",
    "deepseek_api_key": "",
    "deepseek_model": "deepseek-chat",
    "deepseek_base_url": "https://api.deepseek.com",
    "deepseek_timeout": "75",
    "proxy": "",
}


def load_config():
    """读取本地配置，缺失 / 损坏 / 非字典一律静默回退默认值。"""
    cfg = dict(CONFIG_TEMPLATE)
    for p in (os.path.join(app_dir(), CONFIG_FILE),
              os.path.join(os.environ.get("LOCALAPPDATA") or
                           os.path.expanduser("~"), APP_NAME, CONFIG_FILE)):
        try:
            with open(p, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            continue
        if isinstance(data, dict):
            for k in cfg:
                v = data.get(k)
                if isinstance(v, str) and v.strip():
                    cfg[k] = v.strip()
            return cfg, p
    return cfg, ""


CONFIG, CONFIG_PATH = load_config()


def config_status():
    """返回 (整句翻译是否可用, Edge 口音名)，供界面提示用。

    Edge 神经语音**无需任何配置**就能用，所以第一项不再是「配没配 key」，
    而是「整句翻译能不能用」。

    ⚠ 这里故意用字符串查表而**不 import Pronouncer**：本函数定义在
    模块前部（第 668 行），而 Pronouncer 在第 2097 行。虽然函数体在调用时
    才求值、直接写 Pronouncer 也能跑，但一旦有人在模块导入期调用本函数
    就会 NameError。用纯数据查表彻底避开这个顺序依赖。
    """
    code = (CONFIG.get("edge_accent") or "").strip()
    label = ""
    for c, lb in EDGE_ACCENTS:
        if c == code:
            label = lb
            break
    if not label:
        label = EDGE_ACCENTS[0][1]          # 默认美音 Ava
    return (bool(CONFIG.get("youdao_app_key") and CONFIG.get("youdao_app_secret")),
            label)


# ================================================================ DeepSeek API
# 可选增强：不填 key 时完全不影响原有「打开网页 + 复制问题」方案。
# 这里只使用标准库 urllib，不需要额外 SDK，也能自然复用现有代理配置。
DEEPSEEK_DEFAULT_BASE_URL = "https://api.deepseek.com"
DEEPSEEK_DEFAULT_MODEL = "deepseek-chat"
DEEPSEEK_DEFAULT_TIMEOUT = 75


def deepseek_settings():
    """返回 (api_key, model, base_url, timeout)，配置缺失时使用安全默认值。"""
    key = (CONFIG.get("deepseek_api_key") or "").strip()
    model = (CONFIG.get("deepseek_model") or DEEPSEEK_DEFAULT_MODEL).strip()
    base_url = (CONFIG.get("deepseek_base_url") or
                DEEPSEEK_DEFAULT_BASE_URL).strip().rstrip("/")
    try:
        timeout = int((CONFIG.get("deepseek_timeout") or
                       str(DEEPSEEK_DEFAULT_TIMEOUT)).strip())
    except Exception:
        timeout = DEEPSEEK_DEFAULT_TIMEOUT
    timeout = max(10, min(timeout, 300))
    return key, model or DEEPSEEK_DEFAULT_MODEL, base_url, timeout


def deepseek_configured():
    """是否已经填写 API Key。"""
    return bool(deepseek_settings()[0])


def deepseek_api_url():
    """把 base_url 统一成 chat/completions 端点，兼容用户填完整地址。"""
    _key, _model, base_url, _timeout = deepseek_settings()
    if base_url.endswith("/chat/completions"):
        return base_url
    return base_url + "/chat/completions"


def deepseek_chat(messages):
    """调用 DeepSeek 的 OpenAI 兼容聊天接口。

    返回 (正文, 错误信息)。成功时错误信息为空；失败时正文为 None。
    该函数只负责网络与 JSON 解析，必须在后台线程里调用。
    """
    key, model, _base_url, timeout = deepseek_settings()
    if not key:
        return None, "未配置 DeepSeek API Key"
    payload = {
        "model": model,
        "messages": messages,
        "max_tokens": 1400,
        "stream": False,
    }
    if "reasoner" not in model.lower():
        payload["temperature"] = 0.3
    try:
        req = urllib.request.Request(
            deepseek_api_url(),
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={
                "Authorization": "Bearer " + key,
                "Content-Type": "application/json; charset=utf-8",
                "Accept": "application/json",
                "User-Agent": APP_NAME_EN + "/1.1",
            },
            method="POST",
        )
        with _open_url(req, timeout) as r:
            raw = r.read().decode("utf-8", "replace")
        data = json.loads(raw)
        if isinstance(data, dict) and data.get("error"):
            err = data.get("error") or {}
            if isinstance(err, dict):
                return None, str(err.get("message") or err)
            return None, str(err)
        choices = data.get("choices") if isinstance(data, dict) else None
        if not choices:
            return None, "DeepSeek 返回了空结果"
        message = choices[0].get("message") or {}
        content = (message.get("content") or "").strip()
        if not content:
            return None, "DeepSeek 没有返回正文"
        return content, ""
    except urllib.error.HTTPError as e:
        detail = ""
        try:
            detail = e.read().decode("utf-8", "replace")[:500]
        except Exception:
            pass
        if e.code in (401, 403):
            return None, "DeepSeek API Key 无效或没有权限（HTTP %s）" % e.code
        if e.code == 429:
            return None, "DeepSeek 请求过于频繁或额度不足（HTTP 429）"
        return None, "DeepSeek 请求失败（HTTP %s）%s" % (e.code, detail)
    except urllib.error.URLError as e:
        return None, "无法连接 DeepSeek：%s" % (getattr(e, "reason", e),)
    except json.JSONDecodeError:
        return None, "DeepSeek 返回内容不是有效 JSON"
    except Exception as e:
        return None, "DeepSeek 请求异常：%s" % (e,)


def ai_system_prompt(lang="en"):
    """站内 AI 的系统提示：约束语言、来源和回答风格。"""
    lang_name = LANG_DEFS.get(lang, LANG_DEFS["en"]).get("label", "英语")
    return (
        f"你是查单词软件内置的语言学习助手。当前查询语言是{lang_name}。"
        "请使用中文回答。优先基于用户提供的词典信息；如果没有可靠依据，"
        "要明确说不确定。不要编造不存在的词、音标或语法规则。"
        "回答要简洁、分点，并提供可复制的例句。"
    )


def write_config_template(force=False):
    """在 exe 同目录写一份带注释的 dict_config.json 模板，供用户填写。

    默认不覆盖已存在的文件（force=True 才覆盖），避免抹掉用户填的 key。
    """
    p = os.path.join(app_dir(), CONFIG_FILE)
    if os.path.exists(p) and not force:
        return p
    try:
        with open(p, "w", encoding="utf-8") as f:
            json.dump(CONFIG_TEMPLATE, f, ensure_ascii=False, indent=2)
        return p
    except Exception:
        return ""


# =================================================================== 用户数据
# 搜索历史、单词本、分组 —— 独立于词库，存 %LOCALAPPDATA%\<APP_NAME>\user_data.db。
# 与词库分离的原因：词库是「只读词典数据」，用户数据是「可变个人数据」，
# 混在一起既污染词库，也会因部署目录两份 dict.db 的同步问题而丢失。
class UserStore:
    """用户数据的本地持久化（搜索历史 / 单词本 / 分组）。"""

    DEFAULT_GROUP = "默认分组"

    def __init__(self, path=None):
        if path is None:
            base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
            d = os.path.join(base, APP_NAME)
            try:
                os.makedirs(d, exist_ok=True)
            except Exception:
                pass
            path = os.path.join(d, "user_data.db")
        self.path = path
        self.con = None
        try:
            self.con = sqlite3.connect(self.path)
            self.con.row_factory = sqlite3.Row
            # ⚠ 性能关键（2026-09-17）：默认 synchronous=FULL 意味着
            #   每次 commit 都要 fsync —— 本机实测**一次 47ms**。
            #   而打字时每敲一键都会写一次搜索历史，于是每键固定卡 47ms。
            #   WAL + NORMAL 是 SQLite 官方对 WAL 的推荐组合：
            #   进程崩溃依然不丢数据（WAL 日志保证），
            #   只在操作系统崩溃/断电时可能丢最后几条写 ——
            #   对一个本地词典的「搜索历史」而言完全可以接受。
            #   （历史记录本身也已从打字路径上摘掉，见 _on_pick 的 _loading_list）
            self.con.execute("PRAGMA journal_mode=WAL")
            self.con.execute("PRAGMA synchronous=NORMAL")
        except Exception:
            self.con = None
        self._init()

    def _init(self):
        if not self.con:
            return
        try:
            self.con.executescript("""
                CREATE TABLE IF NOT EXISTS history (
                    word TEXT PRIMARY KEY,
                    ts REAL
                );
                CREATE TABLE IF NOT EXISTS groups (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE
                );
                CREATE TABLE IF NOT EXISTS words (
                    word TEXT,
                    group_id INTEGER,
                    note TEXT DEFAULT '',
                    ts REAL,
                    PRIMARY KEY (word, group_id)
                );
            """)
            self.con.commit()
        except Exception:
            pass

    # ------------------------------------------------------------ 搜索历史
    def add_history(self, word):
        w = (word or "").strip()
        if not w or not self.con:
            return
        try:
            self.con.execute(
                "INSERT INTO history(word, ts) VALUES(?, ?) "
                "ON CONFLICT(word) DO UPDATE SET ts=excluded.ts",
                (w, time.time()))
            self.con.commit()
        except Exception:
            pass

    def history(self, limit=200):
        if not self.con:
            return []
        try:
            rows = self.con.execute(
                "SELECT word, ts FROM history ORDER BY ts DESC LIMIT ?",
                (limit,)).fetchall()
            return [(r["word"], r["ts"]) for r in rows]
        except Exception:
            return []

    def delete_history(self, word):
        if not self.con:
            return
        try:
            self.con.execute("DELETE FROM history WHERE word=?", (word,))
            self.con.commit()
        except Exception:
            pass

    def clear_history(self):
        if not self.con:
            return
        try:
            self.con.execute("DELETE FROM history")
            self.con.commit()
        except Exception:
            pass

    # ------------------------------------------------------------ 分组
    def groups(self):
        base = [{"id": 0, "name": self.DEFAULT_GROUP}]
        if not self.con:
            return base
        try:
            rows = self.con.execute(
                "SELECT id, name FROM groups ORDER BY id").fetchall()
            return base + [{"id": r["id"], "name": r["name"]} for r in rows]
        except Exception:
            return base

    def add_group(self, name):
        n = (name or "").strip()
        if not n or not self.con:
            return -1
        try:
            self.con.execute(
                "INSERT OR IGNORE INTO groups(name) VALUES(?)", (n,))
            self.con.commit()
            row = self.con.execute(
                "SELECT id FROM groups WHERE name=?", (n,)).fetchone()
            return row["id"] if row else -1
        except Exception:
            return -1

    # ------------------------------------------------------------ 单词本
    def add_word(self, word, group_id=0, note=""):
        w = (word or "").strip()
        if not w or not self.con:
            return False
        try:
            self.con.execute(
                "INSERT OR IGNORE INTO words(word, group_id, note, ts) "
                "VALUES(?,?,?,?)", (w, group_id, note or "", time.time()))
            self.con.commit()
            return True
        except Exception:
            return False

    def has_word(self, word, group_id=0):
        if not self.con:
            return False
        try:
            r = self.con.execute(
                "SELECT 1 FROM words WHERE word=? AND group_id=?",
                (word, group_id)).fetchone()
            return r is not None
        except Exception:
            return False

    def get_note(self, word, group_id=0):
        """读取某个词在当前分组的笔记；不存在或失败时返回空串。"""
        if not self.con:
            return ""
        try:
            r = self.con.execute(
                "SELECT note FROM words WHERE word=? AND group_id=?",
                (word, group_id)).fetchone()
            return (r["note"] or "") if r else ""
        except Exception:
            return ""

    def set_note(self, word, note, group_id=0):
        """写入/覆盖笔记；单词不存在时自动加入当前分组。"""
        w = (word or "").strip()
        if not w or not self.con:
            return False
        try:
            self.con.execute(
                "INSERT INTO words(word, group_id, note, ts) VALUES(?,?,?,?) "
                "ON CONFLICT(word, group_id) DO UPDATE SET note=excluded.note",
                (w, group_id, note or "", time.time()))
            self.con.commit()
            return True
        except Exception:
            return False

    def remove_word(self, word, group_id=0):
        if not self.con:
            return
        try:
            self.con.execute(
                "DELETE FROM words WHERE word=? AND group_id=?",
                (word, group_id))
            self.con.commit()
        except Exception:
            pass

    def words(self, group_id=0):
        if not self.con:
            return []
        try:
            rows = self.con.execute(
                "SELECT word, note, ts FROM words WHERE group_id=? "
                "ORDER BY ts DESC", (group_id,)).fetchall()
            return [(r["word"], r["note"], r["ts"]) for r in rows]
        except Exception:
            return []

    def clear_words(self):
        if not self.con:
            return
        try:
            self.con.execute("DELETE FROM words")
            self.con.commit()
        except Exception:
            pass

    def count_words(self, group_id=None):
        """统计单词数。group_id=None 表示全部。"""
        if not self.con:
            return 0
        try:
            if group_id is None:
                r = self.con.execute("SELECT COUNT(*) c FROM words").fetchone()
            else:
                r = self.con.execute(
                    "SELECT COUNT(*) c FROM words WHERE group_id=?",
                    (group_id,)).fetchone()
            return r["c"] if r else 0
        except Exception:
            return 0

    def clear_words_group(self, group_id):
        """只清空指定分组。返回删除条数，失败 -1。"""
        if not self.con:
            return -1
        try:
            n = self.count_words(group_id)
            self.con.execute("DELETE FROM words WHERE group_id=?", (group_id,))
            self.con.commit()
            return n
        except Exception:
            return -1

    # ------------------------------------------------- 快照 / 还原（供「撤销」）
    # 为什么用「整表快照 + 还原」而不是「反向操作」：
    #   清空 / 批量移出 这类操作的反向操作要逐条补回，容易漏（尤其是
    #   ts、note、group_id 三个字段），而 user_data.db 只有几十~几千行，
    #   整体快照实测 <1ms，成本可以忽略。
    #   快照返回**纯 Python 列表**而非 sqlite3.Row —— Row 依赖连接，
    #   连接关闭或换库后就读不出来了，长期持有的必须是脱离连接的普通数据。
    def snapshot_history(self):
        """全部历史行的快照 [(word, ts), ...]（不分页，供还原用）。"""
        if not self.con:
            return []
        try:
            return [(r["word"], r["ts"]) for r in self.con.execute(
                "SELECT word, ts FROM history").fetchall()]
        except Exception:
            return []

    def restore_history(self, rows):
        """把历史整体替换为快照。返回写入条数，失败 -1。"""
        if not self.con:
            return -1
        try:
            self.con.execute("DELETE FROM history")
            self.con.executemany(
                "INSERT OR REPLACE INTO history(word, ts) VALUES(?,?)",
                [(w, t) for w, t in rows])
            self.con.commit()
            return len(rows)
        except Exception:
            return -1

    def snapshot_words(self, group_id=None):
        """单词本快照 [(word, group_id, note, ts), ...]。
        group_id=None 表示全部（跨分组），否则只该分组。"""
        if not self.con:
            return []
        try:
            if group_id is None:
                rows = self.con.execute(
                    "SELECT word, group_id, note, ts FROM words").fetchall()
            else:
                rows = self.con.execute(
                    "SELECT word, group_id, note, ts FROM words "
                    "WHERE group_id=?", (group_id,)).fetchall()
            return [(r["word"], r["group_id"], r["note"], r["ts"])
                    for r in rows]
        except Exception:
            return []

    def restore_words(self, rows, group_id=None):
        """还原单词本快照。group_id=None → 清空全部后写入；
        指定 group_id → 只清该分组后写入（跨分组的快照也能只补回一个分组）。
        返回写入条数，失败 -1。"""
        if not self.con:
            return -1
        try:
            if group_id is None:
                self.con.execute("DELETE FROM words")
                put = rows
            else:
                self.con.execute("DELETE FROM words WHERE group_id=?",
                                 (group_id,))
                put = [r for r in rows if r[1] == group_id]
            self.con.executemany(
                "INSERT OR REPLACE INTO words(word, group_id, note, ts) "
                "VALUES(?,?,?,?)", put)
            self.con.commit()
            return len(put)
        except Exception:
            return -1

    def export_words(self, path, group_id=0):
        """导出单词本为 txt（每行一词，可带注释）。返回写入条数，失败 -1。"""
        rows = self.words(group_id)
        try:
            with open(path, "w", encoding="utf-8") as f:
                for w, note, _ts in rows:
                    f.write(w + (f"\t{note}" if note else "") + "\n")
            return len(rows)
        except Exception:
            return -1


# =================================================================== 词典引擎
class DictEngine:
    """封装一个语言词库的查询。"""

    def __init__(self, con, lang_code="en"):
        self.con = con
        self.lang_code = lang_code
        self.kind = "en"
        # 查询结果 LRU 缓存。
        # 打字场景里同一个前缀会被反复查（退格、来回删改、方向键上下移动
        # 都会重放同一次 _on_text），缓存能把重复查询变成 0 成本的字典命中。
        # 之所以不用 functools.lru_cache：它把 self 也当 key，会让连接对象
        # 一直无法回收；这里手工维护一个有序字典，超限就丢最旧的。
        self._cache = {}
        self._cache_order = []
        self._CACHE_MAX = 256
        self._detect()

    def _cache_get(self, key):
        if key in self._cache:
            try:
                self._cache_order.remove(key)
            except ValueError:
                pass
            self._cache_order.append(key)
            return self._cache[key]
        return None

    def _cache_put(self, key, val):
        self._cache[key] = val
        self._cache_order.append(key)
        while len(self._cache_order) > self._CACHE_MAX:
            old = self._cache_order.pop(0)
            self._cache.pop(old, None)

    def _detect(self):
        if not self.con:
            return
        try:
            cols = {r[1] for r in self.con.execute("PRAGMA table_info(dict)")}
            if "phonetic_us" in cols and self.lang_code != "en":
                self.kind = "other"   # 日/法/粤
        except Exception:
            pass

    # ---------------------------------------------------------- 主查询
    # 纯变形指针：释义整行只是「xx的过去式 / 复数 / 比较级 …」这类说明，
    # 没有任何独立义项。匹配例：go的过去式、say的过去式和过去分词、
    # big的比较级、v. do的第三人称单数形式
    _INFLECT_PTR = re.compile(
        r"^(?:[a-z]{1,4}\.\s*)?"                       # 可选词性前缀 v./n. …
        r"(?:[A-Za-z'’\-]+的)?"
        r"(?:过去式|过去分词|现在分词|第三人称单数(?:形式)?|复数(?:形式)?|比较级|最高级)"
        r"(?:和(?:过去式|过去分词|现在分词))?"
        r"[。.;；]?$"
    )

    def _is_inflect_stub(self, row):
        """词条是否只是「变形指针」（是 → 查它时应跳原形）。

        ECDICT 把 went/ate 这类变形也单独收了词条，其中一部分的释义
        只有「go的过去式」这种说明（顶多再挂几行 [计]/[化] 学科术语），
        没有独立内容 —— 查它们时跳到原形体验更好。
        而 chipped（a. 有缺口的）、saw（n. 锯子）这类变形词本身有独立
        释义，应当展示自己的词条，不再硬跳原形（2026-10-08 用户反馈：
        搜 chipped 被强制跳到 chip）。

        ⚠ translation 里的换行是字面两字符 \\n，先还原再切行。
        """
        if row is None:
            return False
        tr = (row["translation"] or "").replace("\\n", "\n").strip()
        if not tr:
            return not (row["definition"] or "").replace("\\n", "\n").strip()
        for ln in tr.splitlines():
            ln = ln.strip().strip("；;。.")
            if not ln or ln.startswith("["):
                continue                       # 学科术语行，不算独立内容
            if ln.startswith(("pl.", "pl ")):
                continue                       # 「pl. 老鼠」这类复数说明
            if self._INFLECT_PTR.match(ln):
                continue                       # 「go的过去式」这类纯指针
            return False                       # 有真实释义行 → 不是 stub
        return True

    def lookup(self, term, dict_key="simple"):
        """按词表查询单词，返回词条 dict 或 None。

        查询顺序很重要：
          ECDICT 把 went / apples 这类变形也单独收了词条。其中
          chipped / saw 这类**本身有独立释义**的（a. 有缺口的 / n. 锯子），
          优先展示自己的词条，并附「原形」提示；而 went（释义只有
          「go的过去式」）这类纯变形指针，才跳到原形拿完整词条。
        """
        if not self.con or not term:
            return None
        t = term.strip()
        if not t:
            return None

        row = None
        from_form = None
        stub_row = None

        # 0) 非英语语种：罗马字检索键优先（nihon -> 日本, nei -> 你）
        if self.kind == "other" or self.lang_code != "en":
            row = self._fetch_sw(t)
            if row is not None:
                from_form = None

        # 1) 英语：直接匹配优先 —— 变形词若有独立释义（chipped = 有缺口的），
        #    优先展示自己的词条；只是变形指针的先挂起，等原形裁决。
        #    非英语词库的词条没有释义字段（全是词形 + 音标），「独立内容」
        #    无从谈起，保持旧顺序（原形优先），不走这条路。
        if row is None and self.lang_code == "en":
            row = self._fetch_exact(t)
            if row is not None and self._is_inflect_stub(row):
                stub_row, row = row, None

        # 2) 词形还原：went -> go（英语仅在没查到、或词条只是变形指针时；
        #    非英语照旧，查不到就直接还原）
        if row is None:
            lemma = self._lemma(t)
            if lemma and lemma.lower() != t.lower():
                cand = self._fetch_exact(lemma)
                if cand is not None:
                    row = cand
                    from_form = lemma
                elif stub_row is not None:
                    row = stub_row     # 原形查不到，退回变形词自己的词条

        # 2.5) 非英语：直接匹配（保持旧顺序：原形优先，直接匹配兜底）
        if row is None and self.lang_code != "en":
            row = self._fetch_exact(t)

        # 3) strip 模糊匹配（long-time / long time / longtime）
        if row is None:
            row = self._fetch_sw(t)

        # 兜底：挂起的变形指针词条总比「查不到」强
        # （如 lemma 自映射、或 sw 键不同导致模糊匹配也落空时）
        if row is None:
            row = stub_row

        if row is None:
            return None

        d = dict(row)
        if from_form:
            d["_from"] = from_form
        elif self.lang_code == "en":
            # 展示的是变形词自己的词条：补一条「原形」提示，保留
            # 「想去原形」的入口，一跳可达。
            lm = self._lemma(d.get("word") or t)
            w0 = (d.get("word") or t).lower()
            if lm and lm.lower() != w0 and self._fetch_exact(lm) is not None:
                d["_lemma"] = lm

        # 词表过滤：该词不属于所选词表时给出提示而不隐藏。
        # 仅对英语词库有意义——日/法/粤语词库没有考纲标签，
        # 若不加判断会显示「不在高考考纲词表内」这类无关提示。
        if dict_key and dict_key != "all" and self.lang_code == "en":
            tags = (d.get("tag") or "").split()
            if dict_key == "oxford":
                if not d.get("oxford") and not d.get("definition"):
                    d["_note"] = "该词不在牛津核心词表内"
            elif dict_key == "cet":
                if not ({"cet4", "cet6", "ky"} & set(tags)):
                    d["_note"] = "该词不在四六级 / 考研词表内"
            elif dict_key == "gk":
                if "gk" not in tags:
                    d["_note"] = "该词不在高考考纲词表内"
        return d

    def _fetch_exact(self, t):
        try:
            return self.con.execute(
                "SELECT * FROM dict WHERE lower=? LIMIT 1", (t.lower(),)
            ).fetchone()
        except Exception:
            return None

    def _fetch_sw(self, t):
        sw = "".join(c for c in t if c.isalnum()).lower()
        if not sw:
            return None
        try:
            return self.con.execute(
                "SELECT * FROM dict WHERE sw=? LIMIT 1", (sw,)
            ).fetchone()
        except Exception:
            return None

    def _lemma(self, t):
        try:
            r = self.con.execute(
                "SELECT lemma FROM lemma WHERE form=? LIMIT 1", (t.lower(),)
            ).fetchone()
            return r[0] if r else None
        except Exception:
            return None

    # ---------------------------------------------------------- 前缀建议
    def suggest(self, prefix, limit=40, dict_key="simple"):
        """前缀建议。

        英语按 lower 前缀匹配；日/法/粤同时按 sw（罗马字检索键）匹配，
        使得 "nihon" 能列出「日本」、"nei" 能列出「你」。
        """
        if not self.con:
            return []
        p = (prefix or "").strip().lower()
        if not p:
            return []

        ck = ("s", self.lang_code, p, limit, dict_key)
        hit = self._cache_get(ck)
        if hit is not None:
            return hit

        try:
            if self.lang_code != "en":
                # 日/法/粤：原文前缀 + 罗马字前缀，两条合并。
                # 同样用「范围扫描」代替 LIKE —— 理由见下面 else 分支的注释。
                hi = p + "\uffff"
                rows = self.con.execute(
                    "SELECT word, phonetic, translation, tag, bnc, frq, collins, oxford "
                    "FROM dict WHERE (lower >= ? AND lower < ?) "
                    "OR (sw >= ? AND sw < ?) "
                    "ORDER BY CASE WHEN lower=? THEN 0 "
                    "WHEN sw=? THEN 1 "
                    "WHEN lower>=? AND lower<? THEN 2 ELSE 3 END, "
                    "LENGTH(word), word LIMIT ?",
                    (p, hi, p, hi, p, p, p + " ", p + " \uffff", limit * 3),
                ).fetchall()
            else:
                # ① `lower >= ? AND lower < ?` 而不是 `LIKE ?`
                #    等价于前缀匹配，但能用上 idx_dict_lower 做范围扫描。
                #    EXPLAIN 实测：LIKE 'x%' → SCAN dict（全表 77 万行，恒定
                #    36ms）；范围写法 → SEARCH dict USING INDEX idx_dict_lower。
                #    这是打字每键省 30ms 的关键。
                # ② 上界 = 前缀 + 一个「比所有小写字母都大」的哨兵。
                #    用 U+FFFF 而非 'z'：词库里有 "café"、"naïve" 这类带重音
                #    的非 ASCII 词条，用 'z' 会把它们漏掉一半。
                hi = p + "\uffff"
                rows = self.con.execute(
                    "SELECT word, phonetic, translation, tag, bnc, frq, collins, oxford "
                    "FROM dict INDEXED BY idx_dict_lower "
                    "WHERE lower >= ? AND lower < ? "
                    "ORDER BY CASE WHEN lower=? THEN 0 "
                    "WHEN lower>=? AND lower<? THEN 1 ELSE 2 END, "
                    "CASE WHEN bnc>0 THEN bnc ELSE 999999 END, word LIMIT ?",
                    (p, hi, p, p + " ", p + " \uffff", limit * 4),
                ).fetchall()

                # ---- 候选排序（关键修复）----
                # 旧实现直接拿 SQL 的返回顺序当最终顺序，判据只有
                # 「完全等于 > 前缀短语 > 其他」+ bnc。
                # bnc（英国国家语料库词频排名）覆盖面很差：ha、wa、ru、
                # RU 这类条目 bnc=0 被当成 999999 排到末尾，而实际常用词
                # 却因为不在 BNC 里被压下去，于是查「ha」第一条是 "ha"
                # 这种几乎无义的词条，查「ru」第一条是缩写 "RU"。
                #
                # 改成显式分档（数字越小越靠前）：
                #   0  与输入完全相同（最高优先，用户就是要这个词）
                #   1  常用词：有柯林斯星级 / 牛津3000 / 词频 frq>0
                #   2  其余（无任何权威词表背书的条目）
                # 同一档内再按词频、词长、字母序稳定排列 —— 词频用 frq
                # 而非 bnc，因为 frq 是 ECDICT 综合后的实际使用频率，
                # 覆盖率和区分度都明显更好。
                mine = [r for r in rows if (r["word"] or "").strip().lower() == p]
                rows = sorted(
                    rows,
                    key=lambda r: (
                        0 if (r["word"] or "").strip().lower() == p else
                        (1 if ((r["collins"] or 0) > 0
                               or (r["oxford"] or 0)
                               or (r["frq"] or 0) > 0) else 2),
                        # 前缀短语（"happy ending"）排在单词之后，
                        # 用户打 "happy" 时想先看到 happy 本身
                        1 if " " in (r["word"] or "").strip() else 0,
                        (r["frq"] or 0) if (r["frq"] or 0) > 0 else 10 ** 7,
                        len((r["word"] or "").strip()),
                        (r["word"] or "").lower(),
                    ),
                )
                # 同一词条可能因大小写重复（RU / ru），按 lower 去重
                _seen, _ded = set(), []
                for r in rows:
                    kk = (r["word"] or "").strip().lower()
                    if kk in _seen:
                        continue
                    _seen.add(kk)
                    _ded.append(r)
                rows = _ded
                if mine:
                    # 完全匹配的词条永远留在最前（去重可能把它挤掉）
                    _top = mine[0]
                    rows = [_top] + [r for r in rows
                                     if (r["word"] or "").strip().lower() != p]
        except Exception:
            return []

        out = []
        for r in rows:
            if dict_key and dict_key != "all" and self.lang_code == "en":
                tags = (r["tag"] or "").split()
                if dict_key == "gk" and "gk" not in tags:
                    continue
                if dict_key == "cet" and not ({"cet4", "cet6", "ky"} & set(tags)):
                    continue
                if dict_key == "oxford" and not (r["oxford"] or r["collins"]):
                    continue
            out.append(dict(r))
            if len(out) >= limit:
                break
        self._cache_put(ck, out)
        return out

    # ---------------------------------------------------------- 中译英
    # 词性前缀（用于把 "n. 狗, 坏蛋" 拆成义项）
    _POS_HEAD = re.compile(
        r"^(n|v|vt|vi|a|adj|ad|adv|prep|conj|pron|num|int|interj|art|aux|"
        r"abbr|na|pl|sing|pt|pp|pref|suf)\.")

    @classmethod
    def split_senses(cls, translation):
        """把 ECDICT 的 translation 拆成独立义项列表。

        ECDICT 的释义是一整串，形如：
            "n. 狗, 坏蛋\\nvt. 跟踪, 尾随"
        结构是：先按词性块切分，每块去掉词性前缀与 [标签] 后，
        再按中英文逗号 / 分号切成一个个义项。

        拆出义项的意义：能区分「狗是 dog 的独立义项」和
        「dog 只是 shock（长毛狗）释义里的一部分」——前者才是用户想找的。

        注意：cn_index.zh 在入库时已把 \\n 合并成空格，
        所以词性标记会出现在字符串中间，例如
            "饮料, 酒v. 喝, 喝酒"
        因此不能只按 \\n 切块，必须同时在「词性标记」处切开，
        否则 v. 会和前一个义项粘连，导致 drink 查不到「喝」。
        """
        out = []
        text = (translation or "").replace("\\n", "\n")
        # 纯标签义项（[电] 开心 这类领域行话）—— 按词条局部收集，
        # 由调用方决定是否排除。绝不能用全局集合：同一个中文词在不同
        # 词条里可能是真义项（water 的「水」）也可能是标签义，
        # 一旦全局共享就会互相污染。
        tagged = set()

        # 先把「行首或空格后紧跟的词性标记」统一换成分隔符，
        # 这样无论原文是 \n 分隔还是空格合并都能正确切块。
        text = re.sub(
            r"(?:^|(?<=[\s]))"
            r"(n|v|vt|vi|a|adj|ad|adv|prep|conj|pron|num|int|interj|art|aux|"
            r"abbr|na|pl|sing|pt|pp|pref|suf)\.",
            "\n",
            text,
        )

        for block in text.split("\n"):
            b = block.strip()
            if not b:
                continue
            # 去 [网络]/[计]/[医] 这类领域标签。
            # 标签删掉后往往留下多余空格，而 ECDICT 里也有直接用空格
            # 分隔两个义项的写法（begin = 「开始 [计] 开始」）。
            # 因此把「空格」也当作义项分隔符，否则会得到
            # 「开始 开始」这种融合义项，既不等值于「开始」、
            # 又拿不到精确匹配分，白白输给 enter。
            #
            # ⚠ 同时要甄别「只靠领域标签存在的义项」。
            #   查「开心」时 open core（[电]开心，开芯谐音梗）会以精确
            #   匹配分挤进结果，而它显然不是用户想要的。
            #
            #   判据必须按「位置」而不是「整块有没有标签」：
            #     computer  = 电脑, 电子计算机 [计] 计算机
            #       → 「电脑」「电子计算机」是真义项，「计算机」才是标签义
            #     若只看整块有标签就全标，computer 查「电脑」会直接消失
            #     （实测踩过这个坑）。
            #   做法：找出每个 [..] 标签在块内的位置，只有落在标签
            #   「作用范围」（标签本身 + 其后到下一个分隔符）里的义项
            #   才算标签义。反例 begin =「开始 [计] 开始」——「开始」
            #   在正文里出现两次，属真义项，不标记。
            body = re.sub(r"\[[^\]]*\]", "\x00", b)   # 哨兵占位，保留位置
            # 哨兵会独立成一个片段（"[电] 开心" → ['\x00', '开心']），
            # 因此「紧跟哨兵之后」的义项才是标签带出来的。
            prev_tag = False
            for seg in re.split(r"[,，;；\s]+", body):
                seg = seg.strip()
                if not seg:
                    continue
                if seg == "\x00":
                    prev_tag = True
                    continue
                s = seg.replace("\x00", "").strip()
                if not s:
                    continue
                out.append(s)
                # computer =「电脑, 电子计算机 [计] 计算机」
                #   → 电脑 / 电子计算机 前一个片段不是哨兵 → 真义项
                #   → 计算机 前一个片段是哨兵      → 标签义
                # open core =「[电] 开心」
                #   → 开心 前一个片段是哨兵          → 标签义 ✓
                if prev_tag:
                    tagged.add(s)
                prev_tag = False
        cls._LAST_TAGGED = tagged
        return out

    # split_senses 最近一次调用中「只来自 [领域] 标签」的义项集合。
    # 刻意用「最近一次」而不是全局累积：中文义项在不同词条里身份不同，
    # water 的「水」是真义项、open core 的「开心」是行话标签义，
    # 一旦全局共享就会互相污染（实测会让「水」「书」「牙」全查不到）。
    # 调用方在拿到 senses 后立刻读它，不存在竞态。
    _LAST_TAGGED = set()

    @staticmethod
    def split_senses_ex(translation):
        """返回 (senses, tagged)：后者是「只来自 [领域] 标签」的义项。"""
        senses = DictEngine.split_senses(translation)
        return senses, set(DictEngine._LAST_TAGGED)

    @staticmethod
    def _sense_score(senses, kw, tagged=None, weak_row=False):
        """义项与查询词的贴合程度，越小越好；None 表示不相关。

        0   = 完全相同（狗）
        0.5 = 单字查询命中双字义项的末尾（钱 → 金钱）——
              中文里这类「单字简称」极常见，若不给近似满分，
              查「钱」会输给释义里恰好有个「钱」字的 pocket。
        1   = 去「的」等后缀后相同（美丽的 → 美丽）
        2   = 义项以查询词开头或结尾（小狗 / 狗尾草）
        3   = 仅包含（长毛狗）

        tagged:    只来自 [领域] 标签的义项集合（按位置判定）
        weak_row:  该词条既无词频也无柯林斯/牛津标记（纯冷僻/生造词条）

        标签义的处置分两种情况：
          · 同词条另有非标签的「kw」义项（computer 的「电脑」）
            → 正常返回，标签义只是额外补充
          · 命中完全依赖标签义
            - 词条还在别处出现过（water 的「水」）→ 保留，
              靠 rare/pop 自然排在核心词之后
            - 词条毫无权威背书（open core 的「[电] 开心」）→ 判不相关。
              这类是领域行话/谐音梗，出现在结果里本身就是错的。
        """
        tagged = tagged or set()
        kw_is_tagged = kw in tagged
        kw_has_plain = any(s == kw and s not in tagged for s in senses)
        if kw_has_plain:
            kw_is_tagged = False      # 有真义项就按真义项走
        best = None
        single = len(kw) == 1
        for s in senses:
            if s == kw:
                if kw_is_tagged and weak_row:
                    return None
                cur = 0
            elif single and len(s) == 2 and s.endswith(kw):
                cur = 0.5
            elif s.rstrip("的地得") == kw:
                cur = 1
            elif s.startswith(kw) or s.endswith(kw):
                cur = 2
            elif kw in s:
                cur = 3
            else:
                continue
            if best is None or cur < best:
                best = cur
        return best

    @staticmethod
    def _sense_rank(senses, kw):
        """查询词在义项列表里出现的位置（0 = 第一个义项）。

        这是区分「主含义」与「顺带提及」的关键信号：
          abandon 的释义以「放弃」打头  → rank 0
          go 的释义里「放弃」排到第 8 位 → rank 7
        两者义项贴合度都是 0（都存在精确义项），但只有前者
        才是把「放弃」当主要意思的词。只看贴合度会让 go 胜出。
        返回 (rank, total)：rank 越小越靠前；None 表示未出现。
        """
        single = len(kw) == 1
        for i, s in enumerate(senses):
            if (s == kw or s.rstrip("的地得") == kw
                    or (single and len(s) == 2 and s.endswith(kw))
                    or s.startswith(kw) or s.endswith(kw) or kw in s):
                return (i, len(senses))
        return None

    # ------------------------------------------------- 中文倒排索引探测
    _cn_sense_ok = None       # None=未探测, True/False=结果（按连接缓存）

    def _has_cn_sense(self):
        """词库里是否有 cn_sense 倒排索引表（探索一次后按类缓存）。

        旧词库没有这张表，此时必须回退到 zh LIKE '%x%' 慢路径，
        否则中文反查会直接返回空。所以这里不能假设表一定存在。
        """
        if DictEngine._cn_sense_ok is None:
            try:
                r = self.con.execute(
                    "SELECT 1 FROM sqlite_master WHERE type='table' "
                    "AND name='cn_sense'").fetchone()
                DictEngine._cn_sense_ok = r is not None
            except Exception:
                DictEngine._cn_sense_ok = False
        return DictEngine._cn_sense_ok

    # -------------------------------------------- 中文近义词扩展（联网补充）
    # 结构：{中文词: [英文表达, ...]}。由 UI 层联网取回后写入，
    # 引擎只负责读取 —— 保持「引擎不碰网络」的分层，测试时不用打桩。
    _cn_extra = {}

    @classmethod
    def set_cn_extra(cls, word, items):
        """登记某中文词的英文表达（联网结果）。空列表也记，避免反复重试。"""
        cls._cn_extra[word] = list(items or [])

    @classmethod
    def has_cn_extra(cls, word):
        return word in cls._cn_extra

    def _cn_extra_for(self, word):
        return DictEngine._cn_extra.get(word) or []

    def _rows_for_english(self, words):
        """把英文表达列表查成与 cn_sense 同构的行。

        返回 (rows, direct)：direct 是「整串直接命中」的词集合。
        多词短语退化成单个实义词（have a grand time → grand）时，
        它只是组成成分、不是短语本身的译法，排序时要降一档 ——
        否则查「开心」会出现 grand 排在 delighted 前面这种怪结果。

        ⚠ 补充修正（2026-09-17）：不能把「所有从短语里提取出来的词」
          一律当成 mere fragment。

          反例：查「开心」时网易有道给回来的表达是
                ['feel happy', 'be delighted', 'have a grand time', ...]
          其中 happy / delighted 是这个短语的**译法主体**
          （feel / be 只是功能词，strip 掉虚词后剩下的就是答案），
          而 grand 只是 have a grand time 里的一个成分
          （真正的名词中心词是 time，grand 只是修饰语）。

          旧逻辑把三者都算 weak_extra=1，导致查「开心」时
          happy 被降档，反被 rejoice / joyful / chuffed 这类生僻词压住。
          实测输出：['chuffed','rejoice','joyful',...,'happy',...] —— 荒谬。

          区分判据：该词是不是短语的**最后一个词**。
            feel happy      → happy 是末词  → 是译法主体，不降档
            be delighted    → delighted 是末词 → 是译法主体，不降档
            have a grand time → grand 不是末词（time 在后）→ 仍降档
          英文里「动词 + 宾语」型短语（have a grand time）的中心义
          在后半段，而「系动词/功能动词 + 形容词」型（feel happy /
          be delighted）的中心义恰好是末尾的形容词 —— 末词判据正好
          把这两种情况分开，无需引入词性分析。
        """
        if not words or not self.con:
            return [], set()
        out, direct = [], set()
        for w in words:
            lw = w.strip().lower()
            # ① 整串命中（"happy"、"give up"）—— 这是最可信的译法
            hit = self._lookup_zh_row(lw)
            if hit:
                out.append(hit)
                direct.add((hit["word"] or "").strip().lower())
                continue
            # ② 取「最实义的那个词」再查。
            #    多词短语不能取最后一个词 ——「have a grand time」的末词
            #    是 time，查出来是「时间」，完全答非所问。正确做法是
            #    跳过虚词，取第一个实义词（grand）。
            parts = [p for p in re.split(r"[\s\-]+", lw)
                     if p and p not in _CN_EN_STOP and len(p) > 2]
            for p in parts:
                hit = self._lookup_zh_row(p)
                if hit:
                    out.append(hit)
                    # ③ 末词豁免：若命中的词恰好是该短语的最后一个词，
                    #    它就是这个短语的译法主体（feel happy → happy），
                    #    记入 direct 以免被打上 weak_extra 降档。
                    #    不是末词的（have a grand time → grand）保持降档。
                    if p == lw.split()[-1] or p == re.split(r"[\s\-]+", lw)[-1]:
                        direct.add((hit["word"] or "").strip().lower())
                    break
        return out, direct

    def _lookup_zh_row(self, word_low):
        """按小写英文词取一条「与 cn_sense 同构」的行；查不到返回 None。"""
        if not word_low:
            return None
        try:
            return self.con.execute(
                "SELECT d.word, c.zh, d.tag, d.frq, d.bnc, d.collins, "
                "d.oxford, 0 AS pos "
                "FROM dict d JOIN cn_index c ON c.lower = d.lower "
                "WHERE d.lower = ? LIMIT 1", (word_low,)).fetchone()
        except Exception as e:
            self._cn_query_error = f"extra {type(e).__name__}: {e}"
            return None

    def search_cn(self, kw, limit=30):
        """中文反查英文。

        排序原则（关键修复）：
          1) 义项贴合度 —— 独立义项「狗」优先于「长毛狗」这类顺带提及
          2) 义项位置   —— 该义项是主含义（排前）还是顺带提及（排后）
          3) 词频 frq   —— 常用词优先（dog 远优于 doggies）
          4) 释义长度   —— 短释义通常是核心义项
        旧实现只按 LENGTH(zh) 排序，会让 a dog fight（狗打架）这类
        短释义把 dog 挤出结果，导致最常见的词反而查不到。
        """
        if not self.con or not kw.strip():
            return []
        k = kw.strip()

        ck = ("c", self.lang_code, k, limit)
        hit = self._cache_get(ck)
        if hit is not None:
            return hit

        # 中文近义词扩展（可选，由调用方注入）。
        # 词库只做字面匹配，happy 的释义里没有「开心」二字，
        # 查「开心」就永远出不来。这里把调用方预先联网取到的英文表达
        # （feel happy / be delighted…）也纳入候选，再回本地词库取完整
        # 词条 —— 这样既不依赖网络也能跑（extra 为空即退化为原逻辑），
        # 又能在联网时补齐词库天生缺的那一层映射。
        extra = self._cn_extra_for(k)

        # 候选集必须包含「有词频的常用词」——这是修复旧版漏词的关键。
        # 直接 WHERE zh LIKE '%水%' LIMIT 4000 会被大量生僻词占满，
        # 把 water（frq=226）挤出候选；分开查询即可保证核心词一定入选。
        #
        # 路径 A：常用词（dict.frq>0），按词频排序后取足量候选
        # 路径 B：其余词条，作为兜底补充
        #
        # 性能（重要）：优先走 cn_sense 倒排索引 —— `sense = ?` 是等值查询，
        # 能吃到 idx_cs_sense（实测 0.4ms）。旧路径 `zh LIKE '%x%'` 前置
        # 通配符吃不到索引，必须全表扫 76.8 万行 → 600ms，是打字卡顿的元凶。
        # 索引表不存在时（旧词库）自动回退 LIKE，保证向后兼容。
        #
        # ⚠ 这里不写 `except: pass`：当初就是静默吞掉「no such column c.zh」
        #   导致索引查询永远失败、每次都悄悄回退到慢路径，且毫无迹象。
        #   现在把异常记进 _cn_query_error，供测试与调试断言读取。
        rows = []
        if self._has_cn_sense():
            # ⚠ 关键修复（2026-09-17）：查询词要连同「去后缀变体」一起查。
            #
            #   问题：cn_sense.sense 存的**不是**规范化义项，而是词条释义的
            #   原样切分结果。beautiful 的释义是「美丽的」，于是它被索引到
            #   sense='美丽的' 名下 —— 而用户查的是「美丽」。
            #   等值查询 `sense = '美丽'` 直接把它排除在外，
            #   结果就是：查「美丽」出来的全是 fairness / loveliness /
            #   pulchritude 这类生僻词，**最该出现的 beautiful 反而不见**。
            #
            #   这不是个例：全表 115.8 万条 sense 里有 107,781 条（9.3%）
            #   以「的」结尾。也就是说近十分之一的中文反查都踩这个坑。
            #
            #   注意 _sense_score() 其实**早就**会处理「美丽的 → 美丽」
            #   （`s.rstrip("的地得") == kw` 给 sc=1），
            #   可惜它拿不到这个词 —— 词在候选集构建阶段就被漏掉了。
            #   所以修在「取候选」这一步，与评分逻辑保持同一套后缀规则。
            #
            #   为什么不用 LIKE '%美丽%' 一把梭：那条路径没有索引，
            #   实测单字母就要 1.1 秒（见下方回退路径的注释）。
            #   这里只是把 1 次等值查询变成 3 次等值查询，全部走
            #   idx_cs_sense，代价可忽略。
            #
            #   去后缀规则与 _sense_score 严格对齐：只对「的地得」三个字
            #   做处理，且不去到空串 —— 「的」本身是个正常查询词。
            variants = [k]
            stripped = k.rstrip("的地得")
            if stripped and stripped != k:
                variants.append(stripped)
            else:
                # 用户查「美丽」时，也要能捞到「美丽的」这类义项。
                # 反向补三种后缀，同样是等值查询、同样吃索引。
                for suf in ("的", "地", "得"):
                    variants.append(k + suf)

            ph = ",".join("?" * len(variants))
            try:
                rows += self.con.execute(
                    "SELECT c.word, c.zh, c.tag, d.frq, d.bnc, d.collins, "
                    "d.oxford, c.pos "
                    "FROM cn_sense c JOIN dict d ON d.lower = c.lower "
                    "WHERE c.sense IN (%s) AND d.frq > 0 "
                    "ORDER BY d.frq ASC LIMIT 1200" % ph,
                    tuple(variants),
                ).fetchall()
            except Exception as e:
                self._cn_query_error = f"{type(e).__name__}: {e}"
            try:
                rows += self.con.execute(
                    "SELECT c.word, c.zh, c.tag, d.frq, d.bnc, d.collins, "
                    "d.oxford, c.pos "
                    "FROM cn_sense c LEFT JOIN dict d ON d.lower = c.lower "
                    "WHERE c.sense IN (%s) AND (d.frq IS NULL OR d.frq = 0) "
                    "LIMIT 600" % ph,
                    tuple(variants),
                ).fetchall()
            except Exception as e:
                self._cn_query_error = f"{type(e).__name__}: {e}"
        # ⚠ 回退路径的第二道闸门：`zh LIKE '%a%'` 这种短 ASCII 查询会命中
        #   近 40 万行，连 LIMIT 都救不了（SQLite 仍要扫全表才能凑够），
        #   单字母实测 1.1 秒、「the」0.6 秒 —— 是「打字一卡一卡」最刺眼的
        #   一种。而中文反查本来就不该由 ASCII 输入触发：用户打英文字母
        #   是查英文单词，调用方走的是 suggest()。
        #
        #   判据：纯 ASCII 且 ≤3 字符。为什么不含更长：`the` 这种 3 字母词
        #   已经能扫出 30 条真结果，而 4 字母以上中文义项里的英文噪声
        #   极少，慢查询概率低；把阈值卡在 3 是实测「省时间」与「不误伤」
        #   的平衡点。
        #
        #   ⚠ 单个汉字（水、狗、书）绝不能被拦下 —— 那是最核心的用法，
        #     所以必须先判 isascii()。
        if not rows and len(k) <= 3 and k.isascii():
            return []
        if not rows:
            self._cn_fallback_used = True
            try:
                rows += self.con.execute(
                    "SELECT c.word, c.zh, c.tag, d.frq, d.bnc, d.collins, "
                    "d.oxford, 0 AS pos "
                    "FROM cn_index c JOIN dict d ON d.lower = c.lower "
                    "WHERE c.zh LIKE ? AND d.frq > 0 "
                    "ORDER BY d.frq ASC LIMIT 3000",
                    (f"%{k}%",),
                ).fetchall()
            except Exception as e:
                self._cn_query_error = f"fallbackA {type(e).__name__}: {e}"
            try:
                rows += self.con.execute(
                    "SELECT c.word, c.zh, c.tag, d.frq, d.bnc, d.collins, "
                    "d.oxford, 0 AS pos "
                    "FROM cn_index c LEFT JOIN dict d ON d.lower = c.lower "
                    "WHERE c.zh LIKE ? AND (d.frq IS NULL OR d.frq = 0) "
                    "LIMIT 1500",
                    (f"%{k}%",),
                ).fetchall()
            except Exception as e:
                self._cn_query_error = f"fallbackB {type(e).__name__}: {e}"

        # 联网补充的英文表达并入候选。
        # 放在这里（而不是拼进 SQL）有两个原因：
        #   ① 它们是「已知正确答案」，不该走限流/排序后再被截断；
        #   ② 它们本身不在 cn_sense 里（happy 的释义没有「开心」），
        #      只能先查英文词再把词条反查回来。
        extra_rows, extra_direct = self._rows_for_english(extra)
        if extra_rows:
            rows = list(extra_rows) + list(rows)
            self._cn_extra_used = True

        if not rows:
            return []

        # 先建全集，再逐条打分。
        # 变形判定必须看到「全部候选词」才知道某词是不是别人的变形，
        # 而候选按词频升序排列（environmental 819 先于 environment 855），
        # 边扫边加 seen 会导致判定时原形还没入集，environmental 逃过降权。
        cand = {}          # lower -> row
        for r in rows:
            w = (r["word"] or "").strip()
            low = w.lower()
            if not w or low in cand:
                continue
            # 过滤掉 "a."、"cyno-" 这类非独立词条（词性残片、纯词缀）
            if re.match(r"^[a-z]{1,3}\.$", low) or low.endswith("-"):
                continue
            cand[low] = r
        seen = set(cand.keys())

        # 联网补充进来的词，其释义里本来就不含查询词（这正是「补缺」的
        # 原因），_sense_score 必然返回 None 而被滤掉。所以单独记一份
        # 白名单，打分时给它们豁免「必须字面命中」这条规则。
        extra_lows = {(r["word"] or "").strip().lower() for r in extra_rows}

        scored = []
        for low, r in cand.items():
            w = (r["word"] or "").strip()

            senses, tagged = self.split_senses_ex(r["zh"])
            # 毫无权威背书的词条：无词频、无柯林斯、无牛津，且是短语。
            # open core（[电]开心）、a dog fight 这类都归此列。
            weak_row = (not (r["frq"] or 0) and not (r["collins"] or 0)
                        and not (r["oxford"] or 0))
            sc = self._sense_score(senses, k, tagged, weak_row)
            if sc is None:
                if low not in extra_lows:
                    continue
                # 联网命中：词库确实缺这个映射，但该英文表达被权威词典
                # 认定为「k 的译法」。直接给最高语义优先级 —— 用户查
                # 「开心」时 feel happy / delighted 就是他要的答案。
                sc = 0
                senses = ["\u0000extra"]    # 占位，让 _sense_rank 也命中
            sr = self._sense_rank(senses, k)
            rank = sr[0] if sr else (0 if low in extra_lows else 99)
            n_sense = sr[1] if sr else 1

            # 联网补充的「非整串命中」项（多词短语退化成单个实义词，
            # 如 have a grand time → grand）只是短语成分，
            # 排位让给整串命中的译法（happy / delighted）。
            weak_extra = 1 if (low in extra_lows and low not in extra_direct) else 0

            frq = r["frq"] or 0
            collins = r["collins"] or 0
            oxford = r["oxford"] or 0
            # frq=0 表示无词频数据，排到最后但要保持内部稳定
            frq_key = frq if frq > 0 else 10 ** 7

            # 评分合并策略：不能简单按 (义项分, 词频) 排序。
            # 否则「美丽」会被 loveliness（frq=25381，义项精确）压过
            # beautiful（frq=992，义项为「美丽的」）——但后者才是常用词。
            # 因此：义项精确(0) 或 常用词（柯林斯>=3 / 牛津3000 / frq<=3000）
            # 时，把义项分压到同一档，让词频说话。
            common = (collins >= 3 or oxford or (0 < frq <= 3000))
            if sc <= 1 or common:
                eff_sc = 0 if sc <= 1 else 1
            else:
                eff_sc = sc
            # 常用词的义项分降权，使词频成为主要判据
            if common and sc >= 2:
                eff_sc = 2

            # 义项位置归一化到 0/1/2 三档，避免「排第 7 位」和
            # 「排第 70 位」被当成同样的劣势。
            #   0 档：查的词就是前两个义项之一 —— 这是该词的主含义
            #   1 档：排在中间
            #   2 档：排在很后面
            #
            # 但常用词天然义项多（look 有 12 个义项，「看」排在第 3 位），
            # 生僻词义项少（potation 的「喝」正好是第 1 个义项）。
            # 若让位置压过词频，就会出现「查『喝』出来 potation 而不是
            # drink」这种荒谬结果。因此对常用词豁免位置惩罚——
            # 常用词能查到，比「义项恰好排第一」重要得多。
            #
            # 豁免要有上限：go 的词频极低（35）却义项极多，「放弃」
            # 排在第 7 位——这显然不是 go 的主要意思，用户查「放弃」
            # 想看的是 abandon。因此只有位置确实靠前时才豁免。
            #
            # 判据是「前 3 个义项之内」或「排在前 1/5 且不超过第 5 位」：
            #   look   看在第 3 位 / 共 12  → 豁免（这是真的主含义之一）
            #   answer 答在第 3 位          → 豁免
            #   go     放弃在第 8 位 / 共 21 → 不豁免（8>5）
            #   take   吃在第 8 位 / 共 21   → 不豁免（8>5）
            # 这样常用词能救回来，同时挡住「义项又多又靠后」的干扰项。
            # 注：放宽到 6 位／1-3 比例实验过，会让 come/company/on
            # 这类超高频词反超 begin/friend/open，净效果更差，故维持 5 位。
            common_word = (collins >= 3 or oxford or (0 < frq <= 3000))
            shallow = rank <= 2 or (rank <= 5 and n_sense and rank * 5 <= n_sense)
            if common_word and shallow:
                rk = 0
            elif rank <= 1:
                rk = 0
            elif rank <= 5:
                rk = 1
            else:
                rk = 2
            # 主含义优先：只有当义项贴合度相同时，位置才起作用。
            # 把 rk 放在 eff_sc 之后、词频之前，正是这个语义。
            #
            # 稀有度分层 rare：词库里大量 frq=0 且无柯林斯/牛津标记的
            # 冷僻词（potation 喝、imprison 关闭、onimous 之类），
            # 它们的释义往往就是几个核心中文词的集合，义项分天然很高。
            # 若不显式降层，用户查「喝」会先看到 potation。
            # 这里把「有权威词表背书」和「纯冷僻」分成两层，
            # 权威层永远优先——这是查词典最朴素的期待。
            rare = 0 if (collins > 0 or oxford or (0 < frq <= 20000)) else 1
            #
            # 变形词降权：用户输入「喝」想要的是原形 drink，
            # 而不是分词 drinking；「关闭」想要 close 而非 closed。
            # 这类 -ing/-ed/-s 变形词在释义上往往与原形完全一致，
            # 单靠词频分不出来（drinking 的词频可能比 drink 还低），
            # 因此显式降一档。
            infl = 1 if self._is_infl_of_existing(w, seen) else 0
            # 词组降权：用户输入「睡觉」想要单词 sleep，而不是
            # hit the hay 这类多词习语。习语释义往往又短又精确，
            # 不加权会一直压过核心单词。
            phrase = 1 if " " in w.strip() or "-" in w.strip() else 0
            # 权威度：用柯林斯星级取反（5 星最权威），牛津 3000 再加权。
            # 早期版本只做「是否 >=3 星」的二值判断，导致 pocket(3星)
            # 和 money(5星) 同档，用户查「钱」先看到 pocket。
            # 改成连续星级后，越权威的词越靠前。
            pop = -(collins * 2) - (3 if oxford else 0)
            scored.append((eff_sc, weak_extra, rare, rk, infl, phrase, pop,
                           frq_key, len(r["zh"] or ""), n_sense, w, dict(r)))

        scored.sort(key=lambda x: tuple(x[:11]))

        out = [d for *_, d in scored[:limit]]
        self._cache_put(ck, out)
        return out

    # 常见变形后缀 —— 用于判断某词是否为另一个词条的变形形式
    _INFL_SUF = ("ing", "ed", "es", "s", "er", "est", "ly")

    # 派生后缀：形容词/副词/名词化形式。查「环境」应给 environment，
    # 而不是它的形容词 environmental；查「美丽」不该被 beautifully 抢走。
    _DERIV_SUF = ("al", "ally", "ly", "ment", "ness", "tion", "sion",
                  "ive", "ous", "ful", "less", "able", "ible", "ity")

    @classmethod
    def _is_infl_of_existing(cls, word, seen):
        """判断 word 是否是词库中另一个词条的变形或派生形式。

        只做保守的「去后缀后原形确实存在于候选集」判断，避免误伤
        本身就以 -ing/-ed 结尾的独立词（如 building、clothing）。
        """
        low = word.lower()
        if len(low) < 4:
            return False

        # 屈折变形：-ing / -ed / -s 等
        for suf in ("ing", "ed", "es", "s"):
            if not low.endswith(suf):
                continue
            base = low[: -len(suf)]
            if len(base) < 3:
                continue
            variants = {base}
            if suf in ("ing", "ed"):
                variants.add(base + "e")          # clos -> close
                if len(base) >= 2 and base[-1] == base[-2]:
                    variants.add(base[:-1])       # stopp -> stop
                if base.endswith("i"):
                    variants.add(base[:-1] + "y")  # studi -> study
            for v in variants:
                if v != low and v in seen:
                    return True

        # 派生形式：environmental -> environment，beautifully -> beautiful
        for suf in cls._DERIV_SUF:
            if not low.endswith(suf) or len(low) - len(suf) < 3:
                continue
            base = low[: -len(suf)]
            candidates = {base}
            if base.endswith("i"):
                candidates.add(base[:-1] + "e")    # creativ -> creative
            if len(base) >= 2 and base[-1] == base[-2]:
                candidates.add(base[:-1])          # full -> ful
            for v in candidates:
                if v != low and v in seen:
                    return True
        return False

    # ---------------------------------------------------------- 统计
    def stats(self):
        if not self.con:
            return {}
        s = {}
        try:
            s["total"] = self.con.execute("SELECT COUNT(*) FROM dict").fetchone()[0]
        except Exception:
            s["total"] = 0
        for t in ["zk", "gk", "cet4", "cet6", "ky", "toefl", "ielts", "gre"]:
            try:
                s[t] = self.con.execute(
                    "SELECT COUNT(*) FROM dict WHERE ' '||tag||' ' LIKE ?",
                    (f"% {t} %",),
                ).fetchone()[0]
            except Exception:
                s[t] = 0
        try:
            s["oxford"] = self.con.execute(
                "SELECT COUNT(*) FROM dict WHERE oxford=1"
            ).fetchone()[0]
        except Exception:
            s["oxford"] = 0
        try:
            s["collins5"] = self.con.execute(
                "SELECT COUNT(*) FROM dict WHERE collins>=4"
            ).fetchone()[0]
        except Exception:
            s["collins5"] = 0
        try:
            # 常用短语的可用条目数（多词、第二词为小品词）
            s["phrasable"] = self.con.execute(
                "SELECT COUNT(*) FROM dict WHERE word LIKE '% %' "
                "AND translation!=''"
            ).fetchone()[0]
        except Exception:
            s["phrasable"] = 0
        return s

    # ---------------------------------------------------------- 真实例句
    def examples(self, word, limit=8):
        """取该词的真实例句（英中对照）。

        数据来自 Tatoeba 语料库（CC-BY 2.0），建库脚本见 build_examples.py。
        排序已在建库时定好（短句优先），这里直接顺序取。
        查不到返回空列表——该词没有被例句库覆盖是正常情况，
        界面据此隐藏「例句」板块，不做任何兜底编造。
        """
        if not self.con or not word:
            return []
        w = (word or "").strip().lower()
        if not w or not re.match(r"^[a-z]", w):
            return []
        try:
            rows = self.con.execute(
                "SELECT e.en, e.zh FROM ex_index x JOIN example e ON e.id = x.ex_id "
                "WHERE x.word = ? ORDER BY e.n_en, e.n_zh LIMIT ?",
                (w, limit),
            ).fetchall()
        except Exception:
            return []
        return [(r["en"], r["zh"]) for r in rows]

    def example_count(self):
        """例句库规模，用于界面标注出处。"""
        if not self.con:
            return 0
        try:
            return self.con.execute("SELECT COUNT(*) FROM example").fetchone()[0]
        except Exception:
            return 0

    # ---------------------------------------------------------- 常用短语
    def phrases(self, word, limit=8):
        """取该词的常用短语（动词 + 小品词类的固定搭配）。

        数据同样来自 ECDICT —— 词库本身就收录了 36.6 万个多词词条
        （give up / look after / put up with …），所以不需要额外爬取，
        直接把「以该词开头、且第二词是小品词/介词」的多词词条挑出来即可。

        筛选与排序（这几个条件缺一不可，否则会混进大量专业术语）：
          1. 第二词必须是小品词或常用介词 —— 这一条过滤掉了
             "break address"、"call analyzer"、"hold area" 这类术语；
          2. 剔除带省略号（put ... right）、带中文、超长、四词以上的条目；
          3. 剔除译文为空的条目 —— 没有中文释义对用户没用；
          4. 排序：牛津收录 > 柯林斯星级 > 词长（短短语更可能是固定搭配）。

        注意：多词词条的 bnc / frq 列在 ECDICT 里**全部为 0**，
        所以词频在这里完全不可用，只能靠上面的规则排序。
        查不到短语是正常情况（约一半的单词没有），返回空列表，
        界面据此隐藏「常用短语」板块，不做任何兜底编造。
        """
        if not self.con or not word:
            return []
        w = (word or "").strip().lower()
        if not w or not re.match(r"^[a-z]", w):
            return []
        # ⚠ 性能关键（2026-09-17 修复）：
        #   旧写法 `lower LIKE ?`（'word %'）**用不上 idx_dict_lower** ——
        #   EXPLAIN QUERY PLAN 实测是 `SCAN dict`，全表扫 77 万行，稳定 84ms。
        #   而 _render 每次渲染词条都会调本函数，实测 _render 总耗时 134ms
        #   里本函数占 97%（cProfile：phrases cumtime 0.419s/5 次）。
        #   用户症状「单词打得很慢」的根因就在这里 —— 打字时每次防抖后
        #   要渲染 2 次，就是 ~170ms 的卡顿。
        #   改成显式区间后走 SEARCH ... USING INDEX idx_dict_lower，
        #   实测 0.2~0.4ms（快 200~400 倍），返回结果完全一致
        #   （computer 193=193、water 400=400、give 400=400）。
        #   与 suggest()（见上方 1066 行的同款说明）保持同一约定。
        #   上界用 U+FFFF 哨兵而非 '!'：词库里有 "café" 这类非 ASCII 词条，
        #   必须取「比所有字符都大」的上界才不会漏。
        try:
            rows = self.con.execute(
                "SELECT word, translation, collins, oxford FROM dict "
                "INDEXED BY idx_dict_lower "
                "WHERE lower >= ? AND lower < ? "
                "AND word LIKE '% %' AND translation!='' LIMIT 400",
                (w + " ", w + " \uffff"),
            ).fetchall()
        except Exception:
            return []

        scored = []
        for r in rows:
            p = (r["word"] or "").strip()
            pl = p.lower()
            if "..." in p or "\u2026" in p or "'" in p:
                continue
            if len(p) > 26 or re.search(r"[\u4e00-\u9fff]", p):
                continue
            toks = pl.split()
            if len(toks) < 2 or len(toks) > 3 or toks[0] != w:
                continue
            if toks[1] not in PHRASE_PARTICLES:
                continue
            tr = _clean_phrase_tr(r["translation"])
            if not re.search(r"[\u4e00-\u9fff]", tr):
                continue
            score = (1000 if r["oxford"] else 0) + (r["collins"] or 0) * 60
            scored.append((-score, len(p), p, tr))
        scored.sort(key=lambda x: (x[0], x[1]))
        return [(s[2], s[3]) for s in scored[:limit]]

# =================================================================== 发音
# ======================================================= Edge 神经语音（TTS）
# 微软 Edge 浏览器「大声朗读」背后的在线语音服务。国内可直连，无需申请 key，
# 且提供 47 种英文神经语音（美/英/澳/加/新/印/南非…），音质远好于录音质量
# 参差的有道词库录音。
#
# ── 为什么不直接用 edge-tts 这个包 ──
# 官方包依赖 aiohttp + websockets 两个重依赖，打进单文件 exe 会让体积
# 增加好几 MB，而这里只需要「发一段 SSML、收一段 MP3」这一个动作。
# 所以下面用标准库 socket + ssl 手写 WebSocket 协议，零额外依赖。
#
# ── 协议要点（踩坑记录）──
# 1. 握手必须带 Sec-MS-GEC 令牌，否则服务端直接返回 403。
#    它不是随机数，而是「当前时间取整到 5 分钟」再和固定 client token
#    一起做 SHA256。少了它，纯 WebSocket 握手一定失败 —— 这一点非常隐蔽，
#    因为报错只是干巴巴的 403，看不出跟时间有关。
# 2. 时间基准是 Windows FILETIME（1601-01-01 起算），不是 Unix 时间戳，
#    中间要加 WIN_EPOCH 偏移。
# 3. 音频数据在**二进制帧**里，帧体前 2 字节是大端的 header 长度，
#    真正的 MP3 在这之后。文本帧里只有各种控制消息。
# 4. 结束标志是文本帧里出现 "Path:turn.end"。
EDGE_TRUSTED_TOKEN = "6A5AA1D4EAFF4E9FB37E23D68491D6F4"
EDGE_HOST = "speech.platform.bing.com"
EDGE_CHROMIUM = "143"           # 版本号会影响 Sec-MS-GEC-Version，需与令牌格式一致
EDGE_WIN_EPOCH = 11644473600    # 1601-01-01 → 1970-01-01 的秒数
EDGE_TIMEOUT = 12               # 秒；TTS 比下载录音慢，给得比 ONLINE_TIMEOUT 宽
EDGE_MAX_TEXT = 2000            # 单次合成上限，防止误传长文本

# 可选口音（界面下拉用）。value 为语音代号，label 给用户看。
# 只挑主流且音质稳定的；服务端实际有 47 种英文语音，够用即可。
# 标签刻意做得短（「美·Ava 女」），因为下拉框宽度直接挤占状态文字空间。
EDGE_ACCENTS = [
    ("en-US-AvaNeural",        "美 · Ava 女"),
    ("en-US-AndrewNeural",     "美 · Andrew 男"),
    ("en-US-EmmaNeural",       "美 · Emma 女"),
    ("en-US-BrianNeural",      "美 · Brian 男"),
    ("en-GB-LibbyNeural",      "英 · Libby 女"),
    ("en-GB-SoniaNeural",      "英 · Sonia 女"),
    ("en-GB-RyanNeural",       "英 · Ryan 男"),
    ("en-AU-NatashaNeural",    "澳 · Natasha 女"),
    ("en-AU-WilliamNeural",    "澳 · William 男"),
    ("en-CA-ClaraNeural",      "加 · Clara 女"),
    ("en-IN-NeerjaNeural",     "印 · Neerja 女"),
    ("en-IE-EmilyNeural",      "爱 · Emily 女"),
    ("en-NZ-MollyNeural",      "新 · Molly 女"),
    ("en-ZA-LeahNeural",       "南非 · Leah 女"),
]


def edge_sec_ms_gec(now=None):
    """生成 Sec-MS-GEC 令牌。

    算法：把当前时间（Windows FILETIME 刻度）向下取整到 5 分钟，
    拼上固定 client token 后做 SHA256，取大写十六进制。
    时间必须准 —— 本机时钟偏差超过 5 分钟会被服务端拒绝。
    """
    ticks = (now if now is not None else time.time()) + EDGE_WIN_EPOCH
    ticks -= ticks % 300                 # 取整到 5 分钟
    ticks *= 1e9 / 100                   # 秒 → 100 纳秒刻度
    raw = ("%.0f%s" % (ticks, EDGE_TRUSTED_TOKEN)).encode("ascii")
    return hashlib.sha256(raw).hexdigest().upper()


def _edge_ws_frame_text(payload):
    """构造一个带掩码的客户端文本帧（FIN=1, opcode=1）。"""
    p = payload.encode("utf-8")
    h = bytearray([0x81])                # FIN + text
    n = len(p)
    if n < 126:
        h.append(0x80 | n)
    elif n < 65536:
        h.append(0x80 | 126)
        h += struct.pack(">H", n)
    else:
        h.append(0x80 | 127)
        h += struct.pack(">Q", n)
    mask = os.urandom(4)
    h += mask
    # 客户端发往服务端的帧必须掩码
    return bytes(h) + bytes(b ^ mask[i % 4] for i, b in enumerate(p))


def _edge_ws_read(sock):
    """读一个 WebSocket 帧，返回 (opcode, payload)。"""
    def rd(n):
        buf = b""
        while len(buf) < n:
            chunk = sock.recv(n - len(buf))
            if not chunk:
                raise EOFError("连接已关闭")
            buf += chunk
        return buf

    head = rd(2)
    opcode = head[0] & 0x0F
    length = head[1] & 0x7F
    if length == 126:
        length = struct.unpack(">H", rd(2))[0]
    elif length == 127:
        length = struct.unpack(">Q", rd(8))[0]
    if head[1] & 0x80:                   # 服务端正常不加掩码，加了就解
        mask = rd(4)
        data = rd(length)
        return opcode, bytes(b ^ mask[i % 4] for i, b in enumerate(data))
    return opcode, rd(length)


def edge_tts_synth(text, voice="en-US-AvaNeural", rate="+0%", pitch="+0Hz",
                   timeout=EDGE_TIMEOUT):
    """调用 Edge 神经语音合成，返回 MP3 字节；失败返回 b""。

    rate / pitch 形如 "+10%" / "-5Hz"，控制语速音调。
    任何异常都吞掉并返回空字节 —— 调用方负责回退到别的音源，
    发音按钮绝不能因为网络问题就「点了没反应」。
    """
    text = (text or "").strip()[:EDGE_MAX_TEXT]
    if not text:
        return b""

    path = ("/consumer/speech/synthesize/readaloud/edge/v1"
            "?TrustedClientToken=%s&Sec-MS-GEC=%s&Sec-MS-GEC-Version=1-%s"
            % (EDGE_TRUSTED_TOKEN, edge_sec_ms_gec(), EDGE_CHROMIUM + ".0.3650.75"))
    url = "wss://%s%s" % (EDGE_HOST, path)

    sock = None
    try:
        # 代理配置：URL 里带的 host:port 会覆盖 ProxyHandler，所以这里
        # 直接按 CONFIG 决定连哪里。不配代理就连直连。
        proxy = (CONFIG.get("proxy") or "").strip()
        if proxy:
            u = urllib.parse.urlparse(proxy)
            phost, pport = u.hostname, (u.port or 80)
            if phost:
                raw = socket.create_connection((phost, pport), timeout=timeout)
                # HTTP CONNECT 隧道，让代理把 TCP 连到 bing 的 443
                raw.sendall(("CONNECT %s:443 HTTP/1.1\r\nHost: %s:443\r\n\r\n"
                             % (EDGE_HOST, EDGE_HOST)).encode())
                resp = b""
                while b"\r\n\r\n" not in resp:
                    c = raw.recv(1024)
                    if not c:
                        break
                    resp += c
                if b" 200" not in resp.split(b"\r\n")[0]:
                    raw.close()
                    return b""
            else:
                raw = socket.create_connection((EDGE_HOST, 443), timeout=timeout)
        else:
            raw = socket.create_connection((EDGE_HOST, 443), timeout=timeout)

        ctx = ssl.create_default_context()
        sock = ctx.wrap_socket(raw, server_hostname=EDGE_HOST)
        sock.settimeout(timeout)

        # ---- WebSocket 握手 ----
        key = base64.b64encode(os.urandom(16)).decode()
        req = (
            "GET %s HTTP/1.1\r\n"
            "Host: %s\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            "Sec-WebSocket-Key: %s\r\n"
            "Sec-WebSocket-Version: 13\r\n"
            "Origin: chrome-extension://jdiccldimpdaibmpdkjnbmckianbfold\r\n"
            "Pragma: no-cache\r\n"
            "Cache-Control: no-cache\r\n"
            "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/%s.0.0.0 "
            "Safari/537.36 Edg/%s.0.0.0\r\n"
            "Accept-Encoding: gzip, deflate, br\r\n"
            "Accept-Language: en-US,en;q=0.9\r\n\r\n"
            % (path, EDGE_HOST, key, EDGE_CHROMIUM, EDGE_CHROMIUM)
        )
        sock.sendall(req.encode())
        buf = b""
        while b"\r\n\r\n" not in buf:
            c = sock.recv(4096)
            if not c:
                break
            buf += c
        if b" 101" not in buf.split(b"\r\n")[0]:
            return b""                   # 握手失败（通常是时钟偏差）

        # ---- 先发 speech.config，再发 SSML ----
        stamp = time.strftime(
            "%a %b %d %Y %H:%M:%S GMT+0000 (Coordinated Universal Time)",
            time.gmtime())
        sock.sendall(_edge_ws_frame_text(
            "X-Timestamp:%s\r\n"
            "Content-Type:application/json; charset=utf-8\r\n"
            "Path:speech.config\r\n\r\n"
            '{"context":{"synthesis":{"audio":{"metadataoptions":'
            '{"sentenceBoundaryEnabled":"false","wordBoundaryEnabled":"false"},'
            '"outputFormat":"audio-24khz-48kbitrate-mono-mp3"}}}}' % stamp))

        # SSML 里必须转义 XML 特殊字符，否则含 & < > 的词会让服务端解析失败
        safe = (text.replace("&", "&amp;").replace("<", "&lt;")
                    .replace(">", "&gt;").replace("'", "&apos;")
                    .replace('"', "&quot;"))
        ssml = ("X-RequestId:%s\r\n"
                "Content-Type:application/ssml+xml\r\n"
                "X-Timestamp:%sZ\r\n"
                "Path:ssml\r\n\r\n"
                "<speak version='1.0' "
                "xmlns='http://www.w3.org/2001/10/synthesis' xml:lang='en-US'>"
                "<voice name='%s'><prosody rate='%s' pitch='%s'>%s</prosody>"
                "</voice></speak>" % (uuid.uuid4().hex, stamp, voice,
                                      rate, pitch, safe))
        sock.sendall(_edge_ws_frame_text(ssml))

        # ---- 收音频 ----
        audio = b""
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                opcode, payload = _edge_ws_read(sock)
            except Exception:
                break
            if opcode == 0x8:            # 服务端关闭
                break
            if opcode == 0x1:            # 文本 = 控制消息
                if b"Path:turn.end" in payload:
                    break
            elif opcode == 0x2:          # 二进制 = 音频
                if len(payload) > 2:
                    hlen = struct.unpack(">H", payload[:2])[0]
                    audio += payload[2 + hlen:]
        return audio
    except Exception:
        return b""
    finally:
        if sock is not None:
            try:
                sock.close()
            except Exception:
                pass


def edge_audio_ok(data):
    """校验拿到的确实是 MP3：大小合理 + 能找到连续帧同步字。

    只验头部两字节不够 —— 服务端出错时也会返回 200 和几百字节的
    非音频内容，那种东西直接播放会「点了没声音」。
    """
    if not data or len(data) < 512:
        return False
    i = 0
    if data[:3] == b"ID3":
        size = ((data[6] & 0x7F) << 21 | (data[7] & 0x7F) << 14 |
                (data[8] & 0x7F) << 7 | (data[9] & 0x7F))
        i = 10 + size
    BR = [0, 32, 40, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320, 0]
    SR = {0: 44100, 1: 48000, 2: 32000}
    frames = 0
    while i < len(data) - 4 and frames < 8:
        if data[i] == 0xFF and (data[i + 1] & 0xE0) == 0xE0:
            b2 = data[i + 2]
            br, sr = BR[(b2 >> 4) & 0x0F], SR.get((b2 >> 2) & 3, 0)
            if not br or not sr:
                i += 1
                continue
            frames += 1
            i += max(int(144000 * br / sr) + ((b2 >> 1) & 1), 4)
        else:
            i += 1
    return frames >= 3


class Pronouncer:
    """
    发音引擎。**以在线真人录音为主，本地语音合成兜底。**

    ── 为什么重做（2026-09-16）──
    旧方案是「音标 → 近似拼写串 → 交给系统语音朗读」。实测问题很严重：

      1. 系统里其实只有中文语音（Huihui/Yaoyao/Kangkang），没有英语语音。
         所谓「美式/英式」只是换了音标串和语速，用同一副中文嗓子读，
         所以听起来英美完全一样。
      2. 音标替换表用的字符和词库实际的字符对不上：
         词库最高频的 ə 是**西里尔字母 U+04D9**（13.9 万次），
         而替换表只收录了 IPA 的 U+0259 → 最常见的音全部原样透传，
         一个中文语音遇到西里尔字母就念成怪腔调，听感即「拼读感」。
      3. 音标被替换成 "wotә" 这种假拼写再朗读，本质就不是自然发音。
      4. 美音模式被写死 rate=+1（加速），英音 rate=-1，语速差一倍。

    ── 现在的方案 ──
    直接用**在线真人录音 + 神经语音**，不再自己拼读音标：

      · 英式 (uk)     —— 有道词典英音录音（type=1）
      · 美式 (us)     —— 有道词典美音录音（type=2）
      · 口音 (edge)   —— Edge 神经语音，可选美/英/澳/加/印等 14 种口音

    已实测确认有道的 type=1 / type=2 是**两份不同的真人录音**
    （tomato 长度差 25%、record 差 41%，正对应英美元音与重音差异），
    远比任何本地 TTS 都标准。

    ── 为什么「全球」换成了 Edge 神经语音（2026-09-17）──
    原先「全球」用的是 Forvo（全球母语者真人发音）。实测放弃，两个原因：

      1. **申请不了**：forvo.com 整站挂在 Cloudflare 人机验证后面，
         国内访问只会拿到 "Just a moment..."（HTTP 403）。
         就算翻出去，注册还要过人机 + 邮箱验证。
      2. **接口已死**：Forvo 用来发 key 的 apifree.forvo.com 早已关停，
         现在无论传什么 key 都返回 "Calling from incorrect domain."。
         也就是说，历尽千辛申请到 key 也是白搭。

    所以改用 Edge 神经语音。它国内可直连、无需申请、免费，且提供
    47 种英文神经语音（含澳/加/新/印/爱/南非等口音），恰好就是
    「全球发音」想给的东西，音质还比有道录音更稳定。
    代价是它属于语音合成而非真人录音 —— 但神经语音已接近真人。

    ── 离线可用性 ──
    下载/合成过的音频会缓存到本地（默认 %LOCALAPPDATA%\\{APP_NAME}\\audio），
    同一个词第二次发音直接读缓存，不再联网。
    完全没网且没缓存时，自动回退到本地系统语音（读原文，不读音标），
    保证发音按钮在任何情况下都不会「点了没反应」。
    """

    # ------------------------------------------------------------ 在线录音
    # 有道词典发音接口。type=1 英音 / type=2 美音，返回 mp3。
    # 这是公开的静态资源接口，无需 key。
    ONLINE_TPL = "https://dict.youdao.com/dictvoice?audio={w}&type={t}"
    ONLINE_TIMEOUT = 6          # 秒；超时就回退本地，不让用户等

    # ------------------------------------------------------------ 全球发音
    # 用 Edge 神经语音（见本文件上方 edge_tts_synth）。可选口音见 EDGE_ACCENTS。
    # 用户选中的口音存 dict_config.json 的 "edge_accent"，留空用默认（美音 Ava）。
    EDGE_DEFAULT = "en-US-AvaNeural"

    @classmethod
    def edge_accent(cls):
        """当前选用的 Edge 语音代号。配置无效时回退默认，绝不返回空串。"""
        v = (CONFIG.get("edge_accent") or "").strip()
        valid = {code for code, _ in EDGE_ACCENTS}
        return v if v in valid else cls.EDGE_DEFAULT

    @staticmethod
    def edge_accent_label(code):
        """语音代号 → 给用户看的名字（如 '美音 · Ava（女）'）。"""
        for c, label in EDGE_ACCENTS:
            if c == code:
                return label
        return code

    # ------------------------------------------------------------ 本地语音
    # 各语言优先使用的语音名（按可用性依次尝试，找不到就回退默认）
    #
    # 注意 VOICE_HINTS 里保留 "Microsoft Zira"：这台机器注册表里确实装了
    # Zira（en-US），但 QtTextToSpeech 只走 Speech_OneCore 那条路，
    # 枚举不到它。所以本地兜底时英文仍可能只能用中文语音，
    # 这也正是必须把「在线真人录音」作为主路径的原因。
    VOICE_HINTS = {
        "en_us": ["Microsoft Zira", "Microsoft David", "Microsoft Mark",
                  "English (United States)", "en-US"],
        "en_uk": ["Microsoft Hazel", "Microsoft George", "Microsoft Susan",
                  "English (United Kingdom)", "en-GB"],
        "ja":    ["Microsoft Haruka", "Microsoft Ayumi", "Microsoft Ichiro",
                  "Japanese", "ja-JP"],
        "fr":    ["Microsoft Hortense", "Microsoft Julie", "French", "fr-FR"],
        "yue":   ["Microsoft Tracy", "Microsoft Danny", "zh-HK",
                  "Chinese (Hong Kong)", "Microsoft Huihui"],
    }

    def __init__(self, cache_dir=None):
        self._tts = None          # 缓存的 QTextToSpeech 实例
        self._engine_name = None
        self._voices = []         # 可用语音列表
        self._warned = False
        self._player = None       # QMediaPlayer（播放在线音频）
        self._audio_out = None
        self._last_source = ""    # 上一次实际用了哪条路径（供界面提示）
        self._cache_dir = cache_dir or self._default_cache_dir()
        try:
            os.makedirs(self._cache_dir, exist_ok=True)
        except Exception:
            pass

    @staticmethod
    def _default_cache_dir():
        base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
        return os.path.join(base, APP_NAME, "audio")

    # ---------------------------------------------------------------- 缓存
    def _cache_path(self, word, accent):
        """缓存文件名。用 accent + 词本身，词里的非法字符替换掉。"""
        safe = "".join(c if c.isalnum() or c in "-_'" else "_"
                       for c in word.lower())
        return os.path.join(self._cache_dir, f"{accent}_{safe}.mp3")

    def _fetch_online(self, word, accent):
        """下载真人录音到缓存，返回本地路径；失败返回 ""。"""
        typ = {"uk": 1, "us": 2}.get(accent)
        if not typ:
            return ""
        path = self._cache_path(word, accent)
        if os.path.exists(path) and os.path.getsize(path) > 1024:
            return path                      # 命中缓存，不联网

        url = self.ONLINE_TPL.format(w=urllib.parse.quote(word), t=typ)
        try:
            req = urllib.request.Request(
                url, headers={"User-Agent": "Mozilla/5.0"})
            with _open_url(req, self.ONLINE_TIMEOUT) as r:
                data = r.read()
        except Exception:
            return ""
        # 校验：确实是 mp3（ID3 头或 MPEG 帧同步字），且大小合理
        if len(data) < 1024:
            return ""
        if not (data[:3] == b"ID3" or data[:2] in (b"\xff\xfb", b"\xff\xf3",
                                                   b"\xff\xf2")):
            return ""
        tmp = path + ".part"
        try:
            with open(tmp, "wb") as f:
                f.write(data)
            os.replace(tmp, path)
        except Exception:
            try:
                os.remove(tmp)
            except Exception:
                pass
            return ""
        return path

    # -------------------------------------------------------- 播放本地音频
    def _fetch_edge(self, word, ratio=None):
        """用 Edge 神经语音合成，存缓存后返回本地路径；失败返回 ""。

        语速默认放慢一点（-10%），因为查词场景下用户是在跟读学发音，
        正常语速对外语学习者偏快。台词式的原速留给用户自己调。
        """
        voice = self.edge_accent()
        if not word:
            return ""
        # 缓存键含语音代号 —— 换口音要能拿到新音频，不能复用旧文件
        key = "edge_%s" % voice.replace("Neural", "")
        path = self._cache_path(word, key)
        if os.path.exists(path) and os.path.getsize(path) > 1024:
            return path                      # 命中缓存，不联网

        # ⚠ 这里是普通字符串拼接，**不是 % 格式化** ——
        #   写成 "-10%%" 会原样送出两个百分号，SSML 的 rate 属性
        #   变成非法值，服务端静默返回空音频（不报错，极难发现）。
        data = edge_tts_synth(
            word, voice,
            rate=("-10%" if ratio is None else ratio))
        if not edge_audio_ok(data):
            return ""
        tmp = path + ".part"
        try:
            with open(tmp, "wb") as f:
                f.write(data)
            os.replace(tmp, path)
        except Exception:
            try:
                os.remove(tmp)
            except Exception:
                pass
            return ""
        return path

    def _ensure_player(self):
        """懒创建 QMediaPlayer（必须在 QApplication 之后）。"""
        if self._player is not None:
            return self._player
        try:
            from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
        except Exception:
            return None
        try:
            self._player = QMediaPlayer()
            self._audio_out = QAudioOutput()
            self._audio_out.setVolume(1.0)
            self._player.setAudioOutput(self._audio_out)
        except Exception:
            self._player = None
        return self._player

    def _play_file(self, path):
        p = self._ensure_player()
        if p is None:
            return False
        try:
            from PySide6.QtCore import QUrl
            p.stop()
            p.setSource(QUrl.fromLocalFile(path))
            p.play()
            return True
        except Exception:
            return False

    # ---------------------------------------------------------------- 入口
    def speak(self, text, accent="us", lang="en", phonetic_uk="",
              phonetic_us=""):
        """发音入口。

        Returns:
            True  —— 已成功触发播放
            False —— 所有路径都不可用
        """
        if not text:
            return False
        self._last_source = ""

        # 非英语语种（日/法/粤）：没有在线录音源，直接走本地语音
        if lang != "en":
            voices = self.VOICE_HINTS.get(lang, [])
            ok = self._qt_speak(text, voices, rate=-0.15)
            if ok:
                self._last_source = "本地语音"
            return ok

        # Edge 口音模式：神经语音合成（可选 14 种口音），
        # 失败回退有道美音，再失败才用本地语音
        if accent == "edge":
            path = self._fetch_edge(text)
            if path and self._play_file(path):
                self._last_source = "Edge " + self.edge_accent_label(
                    self.edge_accent())
                return True
            path = self._fetch_online(text, "us")
            if path and self._play_file(path):
                self._last_source = "真人录音（美音）"
                return True
            ok = self._qt_speak(text, [], rate=-0.15)
            if ok:
                self._last_source = "本地语音"
            return ok

        # 兼容旧调用：老的 "global" 一律按 edge 处理，避免历史代码路径失配
        if accent == "global":
            return self.speak(text, "edge", lang, phonetic_uk, phonetic_us)

        # 美式 / 英式：优先在线真人录音
        path = self._fetch_online(text, accent)
        if path and self._play_file(path):
            self._last_source = "真人录音"
            return True

        # 兜底：本地语音直接读单词原文
        #   注意这里**不再做音标替换**——旧方案正是死在这一步。
        #   宁可让语音引擎按拼写读，也不要喂一个自己拼出来的假单词。
        voices = self.VOICE_HINTS.get("en_uk" if accent == "uk" else "en_us",
                                      [])
        ok = self._qt_speak(text, voices, rate=-0.15)
        if ok:
            self._last_source = "离线语音"
        return ok

    # ------------------------------------------------------- Qt 语音（进程内）
    def _ensure_tts(self):
        """懒创建 QTextToSpeech 实例。

        必须在 QApplication 构造之后再创建，因此不放在 __init__ 里。
        引擎优先 winrt（语音更全），失败回退 sapi。
        """
        if self._tts is not None:
            return self._tts
        try:
            from PySide6.QtTextToSpeech import QTextToSpeech
        except Exception:
            return None
        for eng in ("winrt", "sapi", ""):
            try:
                t = QTextToSpeech(eng) if eng else QTextToSpeech()
            except Exception:
                continue
            if t.state() != QTextToSpeech.State.Error:
                self._tts = t
                self._engine_name = eng or "default"
                try:
                    self._voices = list(t.availableVoices())
                except Exception:
                    self._voices = []
                return t
        return None

    def _pick_voice(self, t, hints):
        """按候选名依次匹配系统语音；找不到返回 None（用系统默认）。"""
        if not self._voices:
            return None
        for h in (hints or []):
            hl = h.lower()
            for v in self._voices:
                name = (v.name() or "").lower()
                loc = v.locale().name().lower()
                if hl in name or hl in loc:
                    return v
        return None

    def _qt_speak(self, text, voice_hints, rate=0):
        """用 QtTextToSpeech 朗读（进程内，不启动外部程序）。"""
        t = self._ensure_tts()
        if t is None:
            return False
        try:
            v = self._pick_voice(t, voice_hints)
            if v is not None:
                t.setVoice(v)
            # rate: Qt 用 -1.0 ~ 1.0。默认稍慢，让用户听得清。
            t.setRate(max(-1.0, min(1.0, rate)))
            t.setVolume(1.0)
            if t.state() != 0:      # 0 = Ready；正在朗读则先停
                try:
                    t.stop()
                except Exception:
                    pass
            t.say(text)
            return True
        except Exception:
            return False

    def available_voices(self):
        """列出系统可用语音（进程内获取，不调 PowerShell）。"""
        t = self._ensure_tts()
        if t is None:
            return []
        out = []
        for v in self._voices:
            out.append(f"{v.name()} [{v.locale().name()}]")
        return out


# =================================================================== 视觉组件
class SealMark(QWidget):
    """左上角的印章 / 书标 —— 强化「这是一个词典」的意象。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(52, 52)
        self._text = "典"

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = self.rect().adjusted(2, 2, -2, -2)
        # 圆角方章
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(SEAL))
        p.drawRoundedRect(r, 9, 9)
        # 内描边
        p.setPen(QPen(QColor(255, 255, 255, 70), 1.4))
        p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(r.adjusted(4, 4, -4, -4), 6, 6)
        # 文字
        f = QFont("Microsoft YaHei", 20, QFont.Bold)
        p.setFont(f)
        p.setPen(QColor("#ffffff"))
        p.drawText(self.rect(), Qt.AlignCenter, self._text)
        p.end()


class LetterStrip(QWidget):
    """书脊上的字母索引条 —— 视觉上立刻认出是字典。"""

    LETTERS = list("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
    picked = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(26)
        self.setMouseTracking(True)
        self._hot = -1
        self._cur = -1

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        n = len(self.LETTERS)
        h = self.height() / n
        f = QFont("Georgia", 7)
        p.setFont(f)
        for i, ch in enumerate(self.LETTERS):
            y = i * h
            if i == self._cur:
                p.setPen(Qt.NoPen)
                p.setBrush(QColor(SEAL))
                p.drawRoundedRect(QRectF(2, y, 22, h), 4, 4)
                p.setPen(QColor("#fff"))
            elif i == self._hot:
                p.setPen(QColor(SEAL))
            else:
                p.setPen(QColor(INK_FAINT))
            p.drawText(QRectF(0, y, 26, h), Qt.AlignCenter, ch)
        p.end()

    def mouseMoveEvent(self, e):
        n = len(self.LETTERS)
        i = int(e.position().y() / (self.height() / n))
        i = max(0, min(n - 1, i))
        if i != self._hot:
            self._hot = i
            self.update()

    def leaveEvent(self, e):
        self._hot = -1
        self.update()

    def mousePressEvent(self, e):
        n = len(self.LETTERS)
        i = int(e.position().y() / (self.height() / n))
        i = max(0, min(n - 1, i))
        self._cur = i
        self.update()
        self.picked.emit(self.LETTERS[i])


class Wordmark(QWidget):
    """顶部书名字标 —— 简洁艺术的标题区。"""

    NAME_PT = 17   # 书名号

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(66)
        self.name = APP_NAME
        self.subtitle = APP_SUBTITLE

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()

        # 张开的书本 / 字典意象：左右两页 + 中缝
        bx, by, bw, bh = 14, 18, 34, 30
        p.setPen(QPen(QColor(SEAL), 1.6))
        p.setBrush(QColor(255, 255, 255, 0))
        left = QPainterPath()
        left.moveTo(bx + bw * 0.5, by + 3)
        left.cubicTo(bx + bw * 0.3, by - 2, bx + 4, by + 1, bx - 1, by + 5)
        left.lineTo(bx - 1, by + bh - 2)
        left.cubicTo(bx + 4, by + bh - 6, bx + bw * 0.3, by + bh - 6, bx + bw * 0.5, by + bh)
        p.drawPath(left)

        right = QPainterPath()
        right.moveTo(bx + bw * 0.5, by + 3)
        right.cubicTo(bx + bw * 0.7, by - 2, bx + bw - 4, by + 1, bx + bw + 1, by + 5)
        right.lineTo(bx + bw + 1, by + bh - 2)
        right.cubicTo(bx + bw - 4, by + bh - 6, bx + bw * 0.7, by + bh - 6, bx + bw * 0.5, by + bh)
        p.drawPath(right)
        # 中缝
        p.setPen(QPen(QColor(SEAL), 1.0, Qt.DashLine))
        p.drawLine(bx + bw * 0.5, by + 4, bx + bw * 0.5, by + bh)
        # 页内文字线
        p.setPen(QPen(QColor(INK_FAINT), 0.8))
        for i in range(4):
            yy = by + 9 + i * 5
            p.drawLine(bx + 3, yy, bx + bw * 0.5 - 4, yy)
            p.drawLine(bx + bw * 0.5 + 5, yy, bx + bw - 3, yy)

        # 标题
        p.setPen(QColor(INK))
        f = QFont("Microsoft YaHei", self.NAME_PT, QFont.Bold)
        f.setLetterSpacing(QFont.AbsoluteSpacing, 2)
        p.setFont(f)
        p.drawText(58, 34, self.name)
        # 副标题
        p.setPen(QColor(INK_FAINT))
        p.setFont(QFont("Microsoft YaHei", 8))
        p.drawText(59, 50, self.subtitle)

        # 右侧装饰横线 + 小红点
        p.setPen(QPen(QColor(LINE), 1))
        p.drawLine(200, 33, w - 24, 33)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(SEAL))
        p.drawEllipse(QPoint(w - 20, 33), 3, 3)
        p.end()


class TagChip(QLabel):
    """考点标签胶囊。"""

    COLORS = {
        "zk":     ("#eef6f1", "#1f7a4d"),
        "gk":     ("#fdf1f0", "#b3352c"),
        "cet4":   ("#eef2fb", "#2b5fd9"),
        "cet6":   ("#eef2fb", "#2b5fd9"),
        "ky":     ("#f6eefb", "#7a3fb3"),
        "toefl":  ("#fff8e8", "#9a6b00"),
        "ielts":  ("#fff8e8", "#9a6b00"),
        "gre":    ("#f2f2f4", "#5c6272"),
        "oxford": ("#fdf6e8", "#b08d4f"),
    }
    NAMES = {
        "zk": "中考", "gk": "高考", "cet4": "四级", "cet6": "六级",
        "ky": "考研", "toefl": "托福", "ielts": "雅思", "gre": "GRE",
        "oxford": "牛津3000",
    }

    def __init__(self, key, parent=None):
        super().__init__(parent)
        bg, fg = self.COLORS.get(key, ("#f2f2f4", "#5c6272"))
        self.setText(self.NAMES.get(key, key))
        self.setStyleSheet(
            f"background:{bg};color:{fg};border-radius:9px;"
            f"padding:2px 9px;font-size:11px;font-weight:600;"
        )
        self.setFixedHeight(20)


class Stars(QWidget):
    """柯林斯星级。"""

    def __init__(self, n, parent=None):
        super().__init__(parent)
        self.n = int(n or 0)
        self.setFixedSize(self.n * 11 + 2, 14)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        for i in range(self.n):
            x = i * 11 + 4
            path = QPainterPath()
            for k in range(5):
                a = -3.14159 / 2 + k * 2 * 3.14159 / 5
                a2 = a + 3.14159 / 5
                r1, r2 = 4.4, 1.9
                px = x + r1 * __import__("math").cos(a)
                py = 7 + r1 * __import__("math").sin(a)
                if k == 0:
                    path.moveTo(px, py)
                else:
                    path.lineTo(px, py)
                path.lineTo(x + r2 * __import__("math").cos(a2),
                            7 + r2 * __import__("math").sin(a2))
            path.closeSubpath()
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(GOLD))
            p.drawPath(path)
        p.end()


class PronButton(QPushButton):
    """发音按钮：一个模式一个按钮，带小喇叭图标。"""

    def __init__(self, label, accent, parent=None):
        super().__init__(parent)
        self.accent = accent
        self.label = label
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(28)
        self._active = False
        self.setStyleSheet(self._qss())
        self.setText(f"  {label}")

    def _qss(self):
        return (
            "QPushButton{background:#ffffff;border:1px solid " + LINE + ";"
            "border-radius:14px;padding:0 12px 0 22px;color:" + INK_SOFT + ";"
            "font-size:11.5px;font-weight:600;text-align:center;}"
            "QPushButton:hover{border-color:" + SEAL + ";color:" + SEAL + ";}"
            "QPushButton:pressed{background:" + PAPER_ALT + ";}"
        )

    def paintEvent(self, e):
        super().paintEvent(e)
        # 画小喇叭
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(SEAL if self.underMouse() else INK_FAINT))
        x, y = 11, self.height() / 2
        p.drawRect(int(x) - 4, int(y) - 2, 3, 4)
        path = QPainterPath()
        path.moveTo(x - 1, y - 2)
        path.lineTo(x + 3, y - 5)
        path.lineTo(x + 3, y + 5)
        path.lineTo(x - 1, y + 2)
        path.closeSubpath()
        p.drawPath(path)
        p.setPen(QPen(QColor(SEAL if self.underMouse() else INK_FAINT), 1.2))
        p.setBrush(Qt.NoBrush)
        p.drawArc(int(x) + 2, int(y) - 4, 6, 8, -60 * 16, 120 * 16)
        p.end()


# =================================================================== 主窗口
class TranslateDialog(QDialog):
    """翻译对话框：粘贴句子/段落 → 翻译。

    ⚠ 2026-09-18 两处重要修正（对应「翻译出好多莫名其妙的句子」）：
      ① 不再拿例句冒充译文 —— 见 translate_text() / _same_sentence()。
      ② 改成**真异步** —— 免 key 通道实测 1.3~1.6s，旧版在主线程同步等
         （还调了 processEvents 假装不卡），整个对话框会僵住。现在走
         run_async：输入框能继续打字、窗口能拖动，结果回来才刷新。

    ⚠ 2026-09-18 晚：支持多语言双向。
      旧版语言对写死成中英，切到日语/法语模式点「翻译」翻的仍是中英 ——
      用户反馈「除了英语的其他语言为啥不能双向翻译」。
      现在 lang 由主窗口传入（当时选的哪个语言模式），
      中文 ⇄ 日语 / 法语 / 粤语 都自动判断方向。
    """

    def __init__(self, parent=None, lang="en"):
        super().__init__(parent)
        self.lang = lang or "en"
        self._lab = LANG_DEFS.get(self.lang, {}).get("label", "英语")
        self._busy = False
        self._req = 0          # 请求序号：慢请求不得覆盖后发请求的结果
        self._last_out = ""    # 供「复制译文」
        self.setWindowTitle(f"翻译 · 中文 ⇄ {self._lab}")
        self.resize(620, 580)
        l = QVBoxLayout(self)
        l.setContentsMargins(16, 16, 16, 16)
        l.setSpacing(10)

        self.in_edit = QTextEdit()
        self.in_edit.setObjectName("transIn")
        self.in_edit.setPlaceholderText(
            "输入或粘贴要翻译的句子 / 段落…（Ctrl+Enter 翻译）")
        self.in_edit.setFixedHeight(150)
        l.addWidget(self.in_edit)

        # 方向说明：让用户一眼知道「输中文会翻成什么」，不用去猜当前语言模式
        self.dir_hint = QLabel(
            f"自动判断方向：中文 → {self._lab}　·　{self._lab} → 中文")
        self.dir_hint.setObjectName("dirHint")
        l.addWidget(self.dir_hint)

        brow = QHBoxLayout()
        brow.setSpacing(8)
        self.trans_btn = QPushButton("翻译")
        self.trans_btn.setObjectName("primaryBtn")
        self.trans_btn.setCursor(Qt.PointingHandCursor)
        self.trans_btn.setFixedHeight(32)
        self.trans_btn.clicked.connect(self._do_translate)
        brow.addWidget(self.trans_btn)

        # 两条「零依赖」退路：翻译通道不通时用户仍有办法完成这件事，
        # 而不是只看到一句「失败」。这也是不再拿例句糊弄用户的前提。
        self.web_btn = QPushButton("网页翻译")
        self.web_btn.setObjectName("miniBtn")
        self.web_btn.setCursor(Qt.PointingHandCursor)
        self.web_btn.setFixedHeight(32)
        self.web_btn.setToolTip(
            "把原文复制到剪贴板并在浏览器打开有道翻译网页版")
        self.web_btn.clicked.connect(self._open_web)
        brow.addWidget(self.web_btn)

        self.copy_btn = QPushButton("复制译文")
        self.copy_btn.setObjectName("miniBtn")
        self.copy_btn.setCursor(Qt.PointingHandCursor)
        self.copy_btn.setFixedHeight(32)
        self.copy_btn.clicked.connect(self._copy_out)
        brow.addWidget(self.copy_btn)

        brow.addStretch(1)
        self.status = QLabel("")
        self.status.setObjectName("pronNow")
        brow.addWidget(self.status)
        l.addLayout(brow)

        self.out_view = QTextBrowser()
        self.out_view.setObjectName("transOut")
        self.out_view.setOpenExternalLinks(False)
        l.addWidget(self.out_view, 1)

        self.setStyleSheet(f"""
            QDialog {{ background: {PAPER}; }}
            #transIn {{
                background: #ffffff; border: 1.4px solid {LINE};
                border-radius: 10px; padding: 10px;
                color: {INK}; font-size: 14px;
            }}
            #transIn:focus {{ border-color: {SEAL}; }}
            #primaryBtn {{
                background: {SEAL}; color: #ffffff; border: none;
                border-radius: 16px; padding: 0 22px;
                font-size: 13px; font-weight: 600;
            }}
            #primaryBtn:hover {{ background: #992c26; }}
            #primaryBtn:disabled {{ background: #c9b6b4; }}
            #miniBtn {{
                background: #ffffff; border: 1px solid {LINE};
                border-radius: 16px; padding: 0 14px;
                color: {INK_SOFT}; font-size: 12px;
            }}
            #miniBtn:hover {{ border-color: {SEAL}; color: {SEAL}; }}
            #transOut {{
                background: #ffffff; border: 1px solid {LINE};
                border-radius: 10px; padding: 14px;
                color: {INK}; font-size: 14px;
            }}
            #pronNow {{ color: {INK_SOFT}; font-size: 11.5px; background: transparent; }}
            #dirHint {{
                color: {INK_FAINT}; font-size: 11.5px; padding-left: 2px;
                background: transparent;
            }}
        """)

    # ------------------------------------------------------------ 快捷键
    def keyPressEvent(self, e):
        if (e.key() in (Qt.Key_Return, Qt.Key_Enter)
                and (e.modifiers() & Qt.ControlModifier)):
            self._do_translate()
            return
        super().keyPressEvent(e)

    # ------------------------------------------------------------ 行为
    def _do_translate(self):
        text = self.in_edit.toPlainText().strip()
        if not text:
            self.status.setText("请输入要翻译的内容")
            return
        # ⚠ 这里**故意不**用 `if self._busy: return` 挡掉重复请求。
        #   真实场景：第一次翻译还没回来（免 key 通道 ~1.5s，网络差时更久），
        #   用户发现文字打错了、改完再按 Ctrl+Enter —— 挡掉就等于
        #   「按了没反应」，用户只能等上一次回来再按一次。
        #   正确做法是照常发起新请求，靠自增的 _req 让**先发的旧结果作废**
        #   （见下面 done 回调里的 `req != self._req`）。
        #   按钮在等待期间是禁用的，所以不会出现「连点刷接口」。
        self._req += 1
        req = self._req
        self._busy = True
        self.trans_btn.setEnabled(False)
        self.trans_btn.setText("翻译中…")
        self.status.setText("翻译中…")

        def work():
            try:
                return translate_text(text, self.lang)
            except Exception as e:
                return None, "翻译失败（%s）" % type(e).__name__

        def done(res):
            if req != self._req:      # 已被更新的请求取代，丢弃
                return
            self._busy = False
            self.trans_btn.setEnabled(True)
            self.trans_btn.setText("翻译")
            result, src = res if res else (None, "翻译失败")
            if result:
                self._last_out = result
                self.out_view.setHtml(
                    f"<div style='font-size:15px;line-height:190%;"
                    f"color:{INK};'>{self._esc(result)}</div>"
                    f"<div style='margin-top:14px;font-size:11px;"
                    f"color:{INK_FAINT};'>来源：{self._esc(src)}</div>")
                self.status.setText("翻译完成")
            else:
                self._last_out = ""
                # 失败时给**可操作的下一步**，而不是一句「失败」了事
                self.out_view.setHtml(
                    f"<div style='font-size:13px;line-height:190%;"
                    f"color:{INK};'>{self._esc(src or '翻译失败')}</div>"
                    f"<div style='margin-top:12px;font-size:12.5px;"
                    f"line-height:185%;color:{INK_SOFT};'>"
                    f"可尝试：<br>"
                    f"· 点上方「<b>网页翻译</b>」—— 原文自动复制，到浏览器粘贴即可<br>"
                    f"· 在 dict_config.json 填入 youdao_app_key，"
                    f"获得稳定的整句翻译</div>")
                self.status.setText("未取到译文")

        run_async(work, done)

    @staticmethod
    def _esc(s):
        return (str(s or "").replace("&", "&amp;").replace("<", "&lt;")
                .replace(">", "&gt;"))

    def _copy_out(self):
        if not self._last_out:
            self.status.setText("还没有译文可复制")
            return
        QApplication.clipboard().setText(self._last_out)
        self.status.setText("译文已复制")

    def _open_web(self):
        """把原文复制到剪贴板并打开有道翻译网页版（零 key、零依赖退路）。"""
        text = self.in_edit.toPlainText().strip()
        if text:
            QApplication.clipboard().setText(text)
        QDesktopServices.openUrl(QUrl("https://fanyi.youdao.com/"))
        self.status.setText("已复制原文 · 到网页里 Ctrl+V 即可" if text
                            else "已打开网页翻译")


class DeepSeekSettingsDialog(QDialog):
    """DeepSeek API 配置窗口，避免让普通用户手改 JSON。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("DeepSeek 设置")
        self.resize(580, 330)
        self.setMinimumWidth(520)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 18, 20, 16)
        lay.setSpacing(10)

        intro = QLabel(
            "填写 DeepSeek API Key 后，AI 回答会直接显示在软件里。"
            "不填写也不影响原有功能：AI 按钮仍会打开 DeepSeek 网页并复制问题。<br><br>"
            "Key 只保存在本机 <code>dict_config.json</code>，不会写进程序。"
            "获取地址：<a href='https://platform.deepseek.com/'>DeepSeek 开放平台</a>")
        intro.setWordWrap(True)
        intro.setTextFormat(Qt.RichText)
        intro.setOpenExternalLinks(True)
        lay.addWidget(intro)

        key, model, base_url, timeout = deepseek_settings()

        kr = QHBoxLayout()
        kr.addWidget(QLabel("API Key"))
        self.key_edit = QLineEdit()
        self.key_edit.setEchoMode(QLineEdit.Password)
        self.key_edit.setPlaceholderText("sk-…")
        self.key_edit.setText(key)
        kr.addWidget(self.key_edit, 1)
        lay.addLayout(kr)

        mr = QHBoxLayout()
        mr.addWidget(QLabel("模型"))
        self.model_box = QComboBox()
        self.model_box.setEditable(True)
        self.model_box.addItems(["deepseek-chat", "deepseek-reasoner"])
        self.model_box.setCurrentText(model or DEEPSEEK_DEFAULT_MODEL)
        mr.addWidget(self.model_box, 1)
        lay.addLayout(mr)

        ur = QHBoxLayout()
        ur.addWidget(QLabel("接口地址"))
        self.base_edit = QLineEdit()
        self.base_edit.setText(base_url or DEEPSEEK_DEFAULT_BASE_URL)
        self.base_edit.setToolTip("一般无需修改；兼容 OpenAI 格式的地址也可以填写。")
        ur.addWidget(self.base_edit, 1)
        lay.addLayout(ur)

        tr = QHBoxLayout()
        tr.addWidget(QLabel("超时（秒）"))
        self.timeout_edit = QLineEdit()
        self.timeout_edit.setFixedWidth(100)
        self.timeout_edit.setText(str(timeout))
        tr.addWidget(self.timeout_edit)
        tr.addStretch(1)
        lay.addLayout(tr)

        warning = QLabel("提示：DeepSeek API 通常按用量计费，具体以 DeepSeek 当前政策为准。")
        warning.setWordWrap(True)
        warning.setObjectName("emptyHint")
        lay.addWidget(warning)
        lay.addStretch(1)

        btns = QHBoxLayout()
        btns.addStretch(1)
        cancel = QPushButton("取消")
        cancel.clicked.connect(self.reject)
        save = QPushButton("保存")
        save.setDefault(True)
        save.clicked.connect(self._save)
        btns.addWidget(cancel)
        btns.addWidget(save)
        lay.addLayout(btns)

    def _save(self):
        key = self.key_edit.text().strip()
        model = self.model_box.currentText().strip() or DEEPSEEK_DEFAULT_MODEL
        base = self.base_edit.text().strip().rstrip("/")
        if not (base.startswith("https://") or base.startswith("http://")):
            QMessageBox.warning(self, "设置无效", "接口地址必须以 http:// 或 https:// 开头。")
            return
        try:
            timeout = int(self.timeout_edit.text().strip())
        except Exception:
            QMessageBox.warning(self, "设置无效", "超时时间必须是整数秒。")
            return
        if not 10 <= timeout <= 300:
            QMessageBox.warning(self, "设置无效", "超时时间需在 10~300 秒之间。")
            return

        values = {
            "deepseek_api_key": key,
            "deepseek_model": model,
            "deepseek_base_url": base,
            "deepseek_timeout": str(timeout),
        }
        parent = self.parent()
        writer = getattr(parent, "parent_window", parent)
        saved = True
        if hasattr(writer, "_save_config_items"):
            saved = writer._save_config_items(values)
        else:
            CONFIG.update(values)
        if not saved:
            QMessageBox.warning(
                self, "保存失败",
                "配置文件无法写入。请确认程序所在目录具有写权限后重试。")
            return
        self.accept()


class DeepSeekDialog(QDialog):
    """站内 DeepSeek 对话窗口，支持追问、复制和保存到单词笔记。"""

    def __init__(self, parent, initial_prompt="", subject="", note_word="",
                 task_label="AI 助手"):
        super().__init__(parent)
        self.parent_window = parent
        self.initial_prompt = (initial_prompt or "").strip()
        self.subject = (subject or "").strip()
        self.note_word = (note_word or "").strip()
        self.task_label = task_label or "AI 助手"
        self.messages = [{
            "role": "system",
            "content": ai_system_prompt(getattr(parent, "lang", "en")),
        }]
        self._request_id = 0
        self._busy = False
        self._initial_sent = False
        self._last_answer = ""

        self.setWindowTitle("DeepSeek 助手")
        self.resize(760, 650)
        self.setMinimumSize(620, 500)
        self._build_ui()

    def _build_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(18, 16, 18, 14)
        lay.setSpacing(8)

        top = QHBoxLayout()
        title = QLabel(self.task_label)
        title.setStyleSheet(f"color:{INK};font-size:15px;font-weight:700;")
        top.addWidget(title)
        if self.subject:
            sub = QLabel(self.subject)
            sub.setStyleSheet(f"color:{INK_FAINT};font-size:12px;")
            top.addWidget(sub)
        top.addStretch(1)
        _key, model, _base, _timeout = deepseek_settings()
        self.model_label = QLabel(model)
        self.model_label.setStyleSheet(f"color:{INK_FAINT};font-size:11px;")
        top.addWidget(self.model_label)
        lay.addLayout(top)

        self.chat = QTextBrowser()
        self.chat.setObjectName("deepseekChat")
        self.chat.setOpenExternalLinks(False)
        self.chat.setPlaceholderText("DeepSeek 回答会显示在这里…")
        self.chat.setStyleSheet(
            f"QTextBrowser{{background:#fff;border:1px solid {LINE};"
            f"border-radius:10px;padding:12px;color:{INK};font-size:13px;}}")
        lay.addWidget(self.chat, 1)

        self.input_edit = QTextEdit()
        self.input_edit.setPlaceholderText("可以继续追问，例如：这个词在商务邮件里怎么用？")
        self.input_edit.setFixedHeight(72)
        self.input_edit.setStyleSheet(
            f"QTextEdit{{background:#fff;border:1px solid {LINE};"
            f"border-radius:9px;padding:8px;color:{INK};font-size:13px;}}")
        lay.addWidget(self.input_edit)

        row = QHBoxLayout()
        self.status = QLabel("回答由 DeepSeek 生成，请核对重要信息。")
        self.status.setObjectName("emptyHint")
        self.status.setWordWrap(False)
        row.addWidget(self.status, 1)

        self.send_btn = QPushButton("发送")
        self.send_btn.setObjectName("aiBtn")
        self.send_btn.clicked.connect(self._send_from_ui)
        row.addWidget(self.send_btn)

        self.stop_btn = QPushButton("停止")
        self.stop_btn.setObjectName("miniBtn")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self._stop)
        row.addWidget(self.stop_btn)

        self.copy_btn = QPushButton("复制回答")
        self.copy_btn.setObjectName("miniBtn")
        self.copy_btn.setEnabled(False)
        self.copy_btn.clicked.connect(self._copy_answer)
        row.addWidget(self.copy_btn)

        self.note_btn = QPushButton("存为笔记")
        self.note_btn.setObjectName("miniBtn")
        self.note_btn.setEnabled(False)
        self.note_btn.clicked.connect(self._save_note)
        row.addWidget(self.note_btn)

        settings = QPushButton("设置")
        settings.setObjectName("miniBtn")
        settings.clicked.connect(self._open_settings)
        row.addWidget(settings)
        lay.addLayout(row)

    def _append(self, who, text, color=INK):
        safe = html.escape(text or "").replace("\n", "<br>")
        self.chat.append(
            f"<div style='margin:8px 0;line-height:170%;color:{color};'>"
            f"<b>{html.escape(who)}：</b>{safe}</div>")
        bar = self.chat.verticalScrollBar()
        bar.setValue(bar.maximum())

    def _set_busy(self, busy):
        self._busy = bool(busy)
        self.send_btn.setEnabled(not busy)
        self.stop_btn.setEnabled(busy)
        self.input_edit.setEnabled(not busy)

    def _send_from_ui(self):
        self._send_prompt(self.input_edit.toPlainText())

    def _send_prompt(self, prompt):
        prompt = (prompt or "").strip()
        if self._busy:
            return
        if not prompt:
            self.status.setText("请先输入问题")
            return
        if not deepseek_configured():
            self.status.setText("尚未配置 DeepSeek API Key")
            self._open_settings()
            return

        self.messages.append({"role": "user", "content": prompt})
        payload = list(self.messages)
        self._append("你", prompt, INK_SOFT)
        self.input_edit.clear()
        self.status.setText("DeepSeek 正在生成…")
        self._set_busy(True)
        self._request_id += 1
        req_id = self._request_id

        def work():
            return deepseek_chat(payload)

        def done(res):
            if req_id != self._request_id:
                return
            self._set_busy(False)
            if not res:
                self.status.setText("请求失败，请检查网络和设置")
                self._append("系统", "请求失败，请检查网络和设置。", SEAL)
                return
            content, err = res
            if err:
                self.status.setText(err)
                self._append("系统", err, SEAL)
                return
            self._last_answer = content
            self.messages.append({"role": "assistant", "content": content})
            self._append("DeepSeek", content)
            self.copy_btn.setEnabled(True)
            self.note_btn.setEnabled(bool(self.note_word))
            self.status.setText("生成完成 · 可继续追问")

        run_async(work, done)

    def _stop(self):
        self._request_id += 1
        self._set_busy(False)
        self.status.setText("已停止等待；后台请求结果将被忽略")

    def _copy_answer(self):
        if not self._last_answer:
            return
        QApplication.clipboard().setText(self._last_answer)
        self.status.setText("回答已复制")

    def _save_note(self):
        if not self._last_answer or not self.note_word:
            return
        parent = self.parent_window
        if hasattr(parent, "_save_ai_note"):
            ok = parent._save_ai_note(self.note_word, self._last_answer)
            self.status.setText("已保存到单词笔记" if ok else "保存笔记失败")

    def _open_settings(self):
        dlg = DeepSeekSettingsDialog(self)
        if dlg.exec() == QDialog.Accepted:
            _key, model, _base, _timeout = deepseek_settings()
            self.model_label.setText(model)
            if deepseek_configured():
                self.status.setText("设置已保存，可以发送问题")
            else:
                self.status.setText("尚未填写 API Key，仍可使用网页版 AI")

    def showEvent(self, event):
        super().showEvent(event)
        if not self._initial_sent and self.initial_prompt:
            self._initial_sent = True
            QTimer.singleShot(0, lambda: self._send_prompt(self.initial_prompt))

    def closeEvent(self, event):
        # 让尚未返回的后台请求失效，避免关闭窗口后刷新已销毁控件。
        self._request_id += 1
        super().closeEvent(event)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} · {APP_NAME_EN}")
        self.resize(1080, 720)
        self.setMinimumSize(900, 600)

        self.lang = "en"
        self.dicts = {
            k: DictEngine(open_db(v["db"]), k) for k, v in LANG_DEFS.items()
        }
        self.engine = self.dicts["en"]
        self.cur_dict_idx = 0
        self.pron = Pronouncer()
        self.store = UserStore()    # 搜索历史 / 单词本 / 分组
        self._nav_stack = []        # 查词跳转历史，供「返回上一词」
        # ---------------------------------------------------------- 撤销栈
        # 用户反馈「看不到操作撤销的按钮，放在哪了」—— 因为**根本没有**：
        #   清空搜索历史时弹窗写着「此操作可撤销」，但代码里清完就没了，
        #   弹窗那句话是假的。单词本的「移出」「清空」同样不可恢复。
        #   这里给所有**破坏性用户数据操作**建一套真撤销：
        #     操作前 → 把受影响的表整体快照塞进栈（user_data.db 很小，<1ms）
        #     用户点撤销 / 按 Ctrl+Z → 用快照整体还原
        #   栈里存的是 (描述, 还原函数)，栈空则按钮置灰 —— 用户一眼能看出
        #   「现在有没有东西可撤销」。
        self._undo_stack = []
        # 步数上限 60（2026-09-18 由 30 提高）：跳转/返回现在也进撤销栈，
        # 30 步会被跳转很快挤满，把「清空单词本」这类重要操作顶出去。
        # 内存不因此增长 —— 跳转记录的 cost=0（只存一个词名 + 导航快照），
        # 真正把关内存的是下面的 _UNDO_COST（按快照条数算）。
        self._UNDO_MAX = 60
        # 撤销栈里快照的总条数上限（内存封顶，见 _push_undo）
        self._undo_cost = 0
        self._UNDO_COST = 5000
        self._auto = False          # 候选列表自动选中标志（保留兼容；现由 _loading_list 主导）
        # ⚠ 性能关键（2026-09-17）：程序化填充候选列表的「闸门」（**计数式**，可嵌套）。
        #   根因：QListWidget 的 clear() 和 setCurrentRow() **都会**发
        #   currentRowChanged → _on_pick。那是程序化行为而非用户操作，
        #   旧实现靠 _auto 标志区分，但第一次回调就把它清成 False，
        #   于是后续被误判为用户查词 → add_history → commit()。
        #   实测 commit() 一次 47ms，而打字时每键都触发 ——
        #   这就是「单词打得很慢」的第二主因（第一主因见 phrases()）。
        #   用计数而非布尔：_show_cn_results 既被 _on_text_now 调用、
        #   也被联网回来的回调单独调用，布尔会在嵌套时被内层提前清零。
        self._loading_list = 0
        self._preview_word = None   # 已预览的词，避免同一词重复渲染
        self._last_query = ""
        self._last_input = ""       # 输入框清空前的备份，供 Esc 恢复
        self._online_cache = {}     # 联网词典增强缓存 {word: {english/collins/...}}
        self._online_fetching = set()
        self._cn_en_fetching = set()   # 正在联网取「中文→英文表达」的词
        self._cn_rows_now = []         # 最近一次中文反查结果（供联网回来比对）
        self._cn_locked = False      # 是否强制「中译英」；默认自动识别方向
        # ---- 非英语模式的中文反查（在线）----
        # 缓存 key 是 (语言, 中文)，避免同一词来回删改时反复联网。
        self._cn_fr_cache = {}
        self._cn_fr_req = 0          # 请求序号：慢请求不得覆盖后发请求的结果
        self._cn_fr_now = None       # 最近一次结果 (中文, 机翻, 候选, 命中)
        # ---- 非英语词条的「中文意思」机翻（词条本身没有中文释义）----
        self._mt_cache = {}          # (语言, 词) -> (中文, 来源)
        self._mt_fetching = set()    # 正在联网的词，防重复请求
        self._cur_word = ""
        self._cur_ph_uk = ""
        self._cur_ph_us = ""
        self._ai_dialog = None

        self._build_ui()
        self._apply_theme()
        self._refresh_dict_buttons()
        QTimer.singleShot(80, lambda: self.search_edit.setFocus())

    # ------------------------------------------------------------ UI
    def _build_ui(self):
        root = QWidget()
        self.setCentralWidget(root)
        outer = QVBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # ---------- 顶部标题区 ----------
        header = QWidget()
        header.setObjectName("header")
        hl = QHBoxLayout(header)
        hl.setContentsMargins(18, 8, 18, 6)
        hl.setSpacing(14)

        self.seal = SealMark()
        hl.addWidget(self.seal)

        self.wordmark = Wordmark()
        self.wordmark.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        hl.addWidget(self.wordmark)

        # 语言选择
        self.lang_box = QComboBox()
        self.lang_box.setFixedHeight(30)
        self.lang_box.setMinimumWidth(96)
        for k, v in LANG_DEFS.items():
            self.lang_box.addItem(f"{v['flag']}  {v['label']}", k)
        self.lang_box.currentIndexChanged.connect(self._on_lang)
        hl.addWidget(self.lang_box, 0, Qt.AlignVCenter)

        # 输入防抖定时器：单次触发，每次按键都重置。
        # 引号是硬要求 —— 敲字时的重放/清空也必须合并成一次查询，
        # 否则退格删字符仍会触发查询，卡顿只减半不减量。
        self._query_timer = QTimer(self)
        self._query_timer.setSingleShot(True)
        self._query_timer.timeout.connect(self._flush_query)
        self._pending_text = ""

        outer.addWidget(header)

        # ---------- 搜索区 ----------
        sbox = QWidget()
        sbox.setObjectName("sbox")
        sl = QVBoxLayout(sbox)
        sl.setContentsMargins(20, 4, 20, 10)
        sl.setSpacing(9)

        srow = QHBoxLayout()
        srow.setSpacing(8)

        self.search_edit = QLineEdit()
        self.search_edit.setObjectName("search")
        self.search_edit.setPlaceholderText(
            "输入中文或英文，自动判断方向…   ↑↓ 切换  Esc 清空")
        self.search_edit.setFixedHeight(46)
        self.search_edit.textChanged.connect(self._on_text)
        self.search_edit.returnPressed.connect(lambda: self._commit_first())
        srow.addWidget(self.search_edit, 1)

        self.trans_btn = QPushButton("翻译")
        self.trans_btn.setObjectName("transBtn")
        self.trans_btn.setCursor(Qt.PointingHandCursor)
        self.trans_btn.setFixedHeight(46)
        self.trans_btn.setFixedWidth(62)
        self.trans_btn.setToolTip("翻译句子 / 段落（可粘贴大段文本）")
        self.trans_btn.clicked.connect(self._open_translate)
        srow.addWidget(self.trans_btn)

        sl.addLayout(srow)

        # 词典切换按钮组
        brow = QHBoxLayout()
        brow.setSpacing(7)
        self.dict_group = QButtonGroup(self)
        self.dict_group.setExclusive(True)
        self.dict_buttons = []
        for i, d in enumerate(DICTS):
            b = QPushButton(d["label"])
            b.setCheckable(True)
            b.setCursor(Qt.PointingHandCursor)
            b.setFixedHeight(28)
            b.setToolTip(d["desc"])
            b.clicked.connect(lambda _=False, idx=i: self._on_dict(idx))
            self.dict_group.addButton(b, i)
            self.dict_buttons.append(b)
            brow.addWidget(b)

        brow.addStretch(1)

        # 中译英开关
        self.cn_btn = QPushButton("自动识别")
        self.cn_btn.setCheckable(True)
        self.cn_btn.setCursor(Qt.PointingHandCursor)
        self.cn_btn.setFixedHeight(28)
        self.cn_btn.setToolTip(
            "默认自动识别方向：输入中文查英文，输入英文查释义。\n"
            "按下此按钮可锁定为「只查中文→英文」。")
        self.cn_btn.clicked.connect(self._on_cn_toggle)
        brow.addWidget(self.cn_btn)

        sl.addLayout(brow)

        # 官方词典直达行 —— 点一下就在浏览器打开该词的官方页面
        orow = QHBoxLayout()
        orow.setSpacing(7)
        orow.addWidget(QLabel("词典原文")) 
        self.od_buttons = []
        for o in OFFICIAL_DICTS:
            b = QPushButton(o["label"])
            b.setObjectName("odBtn")
            b.setCursor(Qt.PointingHandCursor)
            b.setFixedHeight(26)
            b.setToolTip(f"{o['full']}\n{o['note']}\n\n点击在浏览器中打开该词的官方页面")
            b.clicked.connect(lambda _=False, k=o["key"]: self._od_open(k))
            orow.addWidget(b)
            self.od_buttons.append(b)
        orow.addStretch(1)
        self.od_host = QWidget()
        self.od_host.setObjectName("odBar")
        self.od_host.setLayout(orow)
        sl.addWidget(self.od_host)

        outer.addWidget(sbox)

        # ---------- 主体 ----------
        body = QWidget()
        body.setObjectName("body")
        bl = QHBoxLayout(body)
        bl.setContentsMargins(20, 0, 20, 16)
        bl.setSpacing(12)

        # 左：候选列表
        left = QFrame()
        left.setObjectName("card")
        ll = QVBoxLayout(left)
        ll.setContentsMargins(0, 0, 0, 0)
        ll.setSpacing(0)

        self.list_hint = QLabel("候选词")
        self.list_hint.setObjectName("listHint")
        self.list_hint.setContentsMargins(14, 10, 14, 6)
        ll.addWidget(self.list_hint)

        self.result_list = QListWidget()
        self.result_list.setObjectName("results")
        self.result_list.setFrameShape(QFrame.NoFrame)
        self.result_list.currentRowChanged.connect(self._on_pick)
        self.result_list.itemActivated.connect(self._on_activate)
        ll.addWidget(self.result_list, 1)

        # 右侧字母索引条贴在最右
        lwrap = QHBoxLayout()
        lwrap.setContentsMargins(0, 0, 0, 0)
        lwrap.setSpacing(0)
        lwrap.addWidget(left, 1)
        self.strip = LetterStrip()
        self.strip.picked.connect(self._on_letter)
        lwrap.addWidget(self.strip)

        lefthost = QWidget()
        lefthost.setObjectName("card")
        lefthost.setFixedWidth(322)
        lh = QHBoxLayout(lefthost)
        lh.setContentsMargins(0, 0, 0, 0)
        lh.setSpacing(0)
        lh.addWidget(left, 1)
        lh.addWidget(self.strip)
        bl.addWidget(lefthost)

        # 中：详情
        mid = QFrame()
        mid.setObjectName("card")
        ml = QVBoxLayout(mid)
        ml.setContentsMargins(0, 0, 0, 0)
        ml.setSpacing(0)

        self.detail = QTextBrowser()
        self.detail.setObjectName("detail")
        self.detail.setFrameShape(QFrame.NoFrame)
        self.detail.setOpenExternalLinks(False)
        self.detail.anchorClicked.connect(self._on_anchor)
        self.detail.setOpenLinks(False)
        ml.addWidget(self.detail, 1)

        # ---- AI 助手栏 ----
        self.ai_bar = QWidget()
        self.ai_bar.setObjectName("aiBar")
        abl = QHBoxLayout(self.ai_bar)
        abl.setContentsMargins(20, 7, 20, 5)
        abl.setSpacing(7)

        self.ai_label = QLabel("AI")
        self.ai_label.setObjectName("aiLabel")
        abl.addWidget(self.ai_label)

        self.ai_buttons = []
        for t in AI_TASKS:
            b = QPushButton(t["label"])
            b.setObjectName("aiBtn")
            b.setCursor(Qt.PointingHandCursor)
            b.setFixedHeight(26)
            b.setToolTip(
                t["tip"] + "\n（网页版会带问题打开；DeepSeek 站内模式需填写 API Key）")
            b.clicked.connect(lambda _=False, k=t["key"]: self._ai_open(k))
            abl.addWidget(b)
            self.ai_buttons.append(b)

        abl.addStretch(1)

        # AI 站点选择
        self.ai_svc_box = QComboBox()
        self.ai_svc_box.setObjectName("aiSvc")
        self.ai_svc_box.setFixedHeight(26)
        self.ai_svc_box.setMinimumWidth(104)
        for s in AI_SERVICES:
            self.ai_svc_box.addItem(s["label"], s["key"])
        if deepseek_configured():
            for _i in range(self.ai_svc_box.count()):
                if self.ai_svc_box.itemData(_i) == "deepseek_api":
                    self.ai_svc_box.setCurrentIndex(_i)
                    break
        self.ai_svc_box.setToolTip("选择在哪个 AI 网站里提问")
        abl.addWidget(self.ai_svc_box)

        ml.addWidget(self.ai_bar)

        # ---- 底部发音栏：美式 / 英式 / 口音 ----
        self.pron_bar = QWidget()
        self.pron_bar.setObjectName("pronBar")
        pbl = QHBoxLayout(self.pron_bar)
        pbl.setContentsMargins(20, 6, 20, 10)
        pbl.setSpacing(8)

        self.pron_label = QLabel("发音")
        self.pron_label.setObjectName("pronLabel")
        pbl.addWidget(self.pron_label)

        self.pron_buttons = []
        for label, accent in [("美式", "us"), ("英式", "uk"), ("口音", "edge")]:
            b = PronButton(label, accent)
            b.clicked.connect(lambda _=False, a=accent: self._speak(a))
            pbl.addWidget(b)
            self.pron_buttons.append(b)

        # 口音选择下拉。Edge 神经语音提供十几种英文口音，
        # 用下拉比塞十几个按钮现实得多。选完立刻存进 dict_config.json，
        # 下次启动仍是这个口音。
        #
        # ⚠ 宽度必须夹住！下拉框默认会按「最长那条标签」撑开，
        #   实测撑到 212px，直接把 pron_now 从 315px 挤到 215px，
        #   而「美式发音 · happy · 真人录音」需要 246px —— 又回到了
        #   用户投诉过的「下方小字看不全」。这里固定成 150px，
        #   长标签靠下拉列表展开时看全，当前选中项够用即可。
        self.accent_box = QComboBox()
        self.accent_box.setObjectName("accentBox")
        self.accent_box.setCursor(Qt.PointingHandCursor)
        self.accent_box.setFixedHeight(28)
        self.accent_box.setFixedWidth(150)
        self.accent_box.setToolTip("选择「口音」按钮使用的 Edge 神经语音")
        for code, label in EDGE_ACCENTS:
            self.accent_box.addItem(label, code)
        # 下拉列表展开时给出足够宽度，让长标签也能看全
        try:
            self.accent_box.view().setMinimumWidth(190)
        except Exception:
            pass
        _cur = (CONFIG.get("edge_accent") or "").strip()
        for _i in range(self.accent_box.count()):
            if self.accent_box.itemData(_i) == _cur:
                self.accent_box.setCurrentIndex(_i)
                break
        self.accent_box.currentIndexChanged.connect(self._on_accent_change)
        pbl.addWidget(self.accent_box)

        # 收藏按钮（底部这一处）。顶部词条标题旁还有一个，
        # 两处都能点 —— 用户反馈「找不到收藏按钮」，因为旧版只有
        # 词条里 12px 的小字链接，混在标题中几乎看不见。
        self.fav_btn = QPushButton("☆ 收藏")
        self.fav_btn.setObjectName("favBtn")
        self.fav_btn.setCursor(Qt.PointingHandCursor)
        self.fav_btn.setFixedHeight(28)
        self.fav_btn.setMinimumWidth(78)
        self.fav_btn.setToolTip("把当前单词加入单词本（Ctrl+D）")
        self.fav_btn.clicked.connect(self._toggle_fav)
        pbl.addWidget(self.fav_btn)

        # 发音状态文字。
        # ⚠ 旧版这里先 addStretch(1) 再放 pron_now，导致它被挤成
        #   实测 66px 宽 —— 「美式发音 · happy · 真人录音」这类提示
        #   根本显示不全，用户反馈「下方读音旁边的小字看不全」。
        #   现在改成让 pron_now 自己吃下所有剩余宽度（stretch=1），
        #   按钮和配置提示保持固有宽度，文字就再也不会被压扁。
        self.pron_now = QLabel("")
        self.pron_now.setObjectName("pronNow")
        self.pron_now.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.pron_now.setMinimumWidth(120)
        pbl.addWidget(self.pron_now, 1)

        # 可选能力开关状态：把「key 填没填」直接摆在界面上，
        # 免得用户以为功能坏了（其实是没配 key）。tooltip 说明配置位置。
        # 它是次要信息，固定成紧凑宽度，不参与抢空间。
        self.cfg_hint = QLabel("")
        self.cfg_hint.setObjectName("cfgHint")
        self.cfg_hint.setCursor(Qt.PointingHandCursor)
        self.cfg_hint.mousePressEvent = self._on_cfg_hint
        self._refresh_cfg_hint()
        pbl.addWidget(self.cfg_hint, 0)

        # ⚠ 发音栏不能塞进中间那一列！
        #   主体是三栏布局：左固定 322px + 右固定 246px + 间距，
        #   窗口 1080px 时中间只剩 446px。而发音栏本身要放
        #   发音标签(39) + 3 个按钮 + 收藏按钮(78) + 状态文字 + 配置提示，
        #   合计需求 490px > 446px —— 于是状态文字被压到 120px，
        #   「美式发音 · happy · 真人录音」只能显示前几个字。
        #   把整条栏移到 body 外面，就能横跨整个窗口宽度（~1040px），
        #   空间立刻从「不够」变成「富余」。这也更符合视觉习惯：
        #   底部状态栏本来就该是通栏的。
        bl.addWidget(mid, 1)

        # 右：侧栏（词库概览 / 搜索历史 / 单词本）
        right = QFrame()
        right.setObjectName("card")
        right.setFixedWidth(246)
        rl = QVBoxLayout(right)
        rl.setContentsMargins(8, 8, 8, 8)
        rl.setSpacing(0)

        self.side_tabs = QTabWidget()
        self.side_tabs.setObjectName("sideTabs")
        self.side_tabs.setDocumentMode(True)

        # Tab 1：词库概览
        ov = QWidget()
        ovl = QVBoxLayout(ov)
        ovl.setContentsMargins(6, 10, 6, 8)
        ovl.setSpacing(9)
        self.stat_title = QLabel("词库概览")
        self.stat_title.setObjectName("statTitle")
        ovl.addWidget(self.stat_title)
        self.stat_widget = StatsPanel()
        ovl.addWidget(self.stat_widget)
        ovl.addSpacing(8)
        # ---------------------------------------------------- 小贴士（可折叠）
        # 用户反馈「那个小贴士有点挡着我了」。它本身有用（操作提示），
        # 所以不删，改成**可折叠 + 记住选择**（写进 dict_config.json）：
        # 收起后只剩一行标题，省出约 130px 给上面的词库概览。
        self.tip_box = QWidget()
        tbl = QVBoxLayout(self.tip_box)
        tbl.setContentsMargins(0, 0, 0, 0)
        tbl.setSpacing(4)
        trow = QHBoxLayout()
        trow.setContentsMargins(2, 0, 0, 0)
        trow.setSpacing(6)
        self.tip_title = QLabel("小贴士")
        self.tip_title.setObjectName("tipTitle")
        trow.addWidget(self.tip_title)
        trow.addStretch(1)
        self.tip_toggle = QPushButton()
        self.tip_toggle.setObjectName("miniBtn")
        self.tip_toggle.setCursor(Qt.PointingHandCursor)
        self.tip_toggle.setFixedHeight(20)
        self.tip_toggle.setMinimumWidth(48)
        self.tip_toggle.clicked.connect(self._toggle_tip)
        trow.addWidget(self.tip_toggle)
        tbl.addLayout(trow)
        self.tip = QLabel("")
        self.tip.setObjectName("tip")
        self.tip.setWordWrap(True)
        self.tip.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        tbl.addWidget(self.tip)
        ovl.addWidget(self.tip_box)
        ovl.addStretch(1)
        self.side_tabs.addTab(ov, "概览")
        self._apply_tip_collapsed(self._tip_saved_collapsed())

        # Tab 2：搜索历史
        self.side_tabs.addTab(self._build_history_tab(), "历史")

        # Tab 3：单词本
        self.side_tabs.addTab(self._build_wordbook_tab(), "单词本")

        rl.addWidget(self.side_tabs)

        # ------------------------------------------------------- 撤销条（常驻）
        # 用户反馈「看不到操作撤销的按钮，放在哪了」—— 旧版**根本没有**：
        # 清空历史的弹窗写着「此操作可撤销」，代码里清完就没了，那句是假的。
        #
        # 放这里而不是底部发音栏，有两个原因：
        #   ① 语义最近 —— 它撤销的正是上面两个 Tab 里的破坏性操作
        #      （清空历史 / 清空单词本 / 移出单词本），按钮就在出事地点下面。
        #   ② ⚠ 底部发音栏**已经满了**。实测往那条栏里再加 74px，
        #      pron_now 会从 246px 被挤到 195px 而截断
        #      （该栏的宽度预算见上面 pron_bar 处的长注释），
        #      test_layout2.py 会立刻报「发音文字未被截断」失败。
        urow = QHBoxLayout()
        urow.setContentsMargins(6, 8, 6, 4)
        urow.setSpacing(6)
        self.undo_btn = QPushButton("↩ 撤销")
        self.undo_btn.setObjectName("undoBtn")
        self.undo_btn.setCursor(Qt.PointingHandCursor)
        self.undo_btn.setFixedHeight(26)
        self.undo_btn.setMinimumWidth(72)
        self.undo_btn.clicked.connect(self._do_undo)
        self.undo_btn.setEnabled(False)
        urow.addWidget(self.undo_btn)
        # 文字说明「现在撤销的是哪一步」—— 让按钮的状态可自解释，
        # 不用去猜 tooltip。
        self.undo_hint = QLabel("暂无可撤销的操作")
        self.undo_hint.setObjectName("emptyHint")
        self.undo_hint.setWordWrap(False)
        urow.addWidget(self.undo_hint, 1)
        rl.addLayout(urow)
        bl.addWidget(right)

        outer.addWidget(body, 1)

        # 通栏发音 / 收藏栏（横跨整个窗口，见上面 pron_bar 处的说明）
        outer.addWidget(self.pron_bar)

        self._load_stats()
        self._update_tip()
        self._refresh_history()
        self._refresh_wordbook()

    # -------------------------------------------------------- 历史 / 单词本 UI
    def _build_history_tab(self):
        w = QWidget()
        l = QVBoxLayout(w)
        l.setContentsMargins(6, 10, 6, 8)
        l.setSpacing(7)

        hrow = QHBoxLayout()
        hrow.setSpacing(6)
        self.hist_title = QLabel("搜索历史")
        self.hist_title.setObjectName("statTitle")
        hrow.addWidget(self.hist_title)
        hrow.addStretch(1)
        self.hist_clear_btn = QPushButton("清空")
        self.hist_clear_btn.setObjectName("miniBtn")
        self.hist_clear_btn.setCursor(Qt.PointingHandCursor)
        self.hist_clear_btn.setFixedHeight(24)
        self.hist_clear_btn.setToolTip("一键清空全部搜索历史")
        self.hist_clear_btn.clicked.connect(self._clear_history)
        hrow.addWidget(self.hist_clear_btn)
        l.addLayout(hrow)

        self.hist_list = QListWidget()
        self.hist_list.setObjectName("histList")
        self.hist_list.setFrameShape(QFrame.NoFrame)
        self.hist_list.itemActivated.connect(self._on_hist_activate)
        self.hist_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.hist_list.customContextMenuRequested.connect(self._hist_menu)
        l.addWidget(self.hist_list, 1)

        self.hist_empty = QLabel("还没有搜索记录")
        self.hist_empty.setObjectName("emptyHint")
        self.hist_empty.setAlignment(Qt.AlignCenter)
        self.hist_empty.setWordWrap(True)
        l.addWidget(self.hist_empty)
        return w

    def _build_wordbook_tab(self):
        w = QWidget()
        l = QVBoxLayout(w)
        l.setContentsMargins(6, 10, 6, 8)
        l.setSpacing(7)

        grow = QHBoxLayout()
        grow.setSpacing(6)
        self.wb_group = QComboBox()
        self.wb_group.setFixedHeight(26)
        self.wb_group.currentIndexChanged.connect(self._on_wb_group)
        grow.addWidget(self.wb_group, 1)
        self.wb_newgrp_btn = QPushButton("+分组")
        self.wb_newgrp_btn.setObjectName("miniBtn")
        self.wb_newgrp_btn.setCursor(Qt.PointingHandCursor)
        self.wb_newgrp_btn.setFixedHeight(26)
        self.wb_newgrp_btn.setToolTip("新建一个分组")
        self.wb_newgrp_btn.clicked.connect(self._new_group)
        grow.addWidget(self.wb_newgrp_btn)
        l.addLayout(grow)

        self.wb_list = QListWidget()
        self.wb_list.setObjectName("wbList")
        self.wb_list.setFrameShape(QFrame.NoFrame)
        self.wb_list.itemActivated.connect(self._on_wb_activate)
        self.wb_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.wb_list.customContextMenuRequested.connect(self._wb_menu)
        l.addWidget(self.wb_list, 1)

        brow = QHBoxLayout()
        brow.setSpacing(6)
        self.wb_count = QLabel("0 词")
        self.wb_count.setObjectName("emptyHint")
        brow.addWidget(self.wb_count)
        brow.addStretch(1)
        self.wb_export_btn = QPushButton("导出")
        self.wb_export_btn.setObjectName("miniBtn")
        self.wb_export_btn.setCursor(Qt.PointingHandCursor)
        self.wb_export_btn.setFixedHeight(24)
        self.wb_export_btn.setToolTip("把当前分组的单词导出为 txt")
        self.wb_export_btn.clicked.connect(self._export_words)
        brow.addWidget(self.wb_export_btn)

        # 一键清空（用户明确要求：「单词本没有一键清除的功能，再加个确认，
        # 防止我不小心全部清除了」）。三点设计：
        #   ① 红色描边 —— 破坏性操作，视觉上必须与「导出」区分开
        #   ② 确认框里把**要删多少词、哪个分组**写清楚，默认按钮是「取消」
        #      （QMessageBox 默认按钮就是 No，回车不会误删）
        #   ③ 清空**可撤销** —— 见 _clear_wordbook / _push_undo
        self.wb_clear_btn = QPushButton("清空")
        self.wb_clear_btn.setObjectName("dangerBtn")
        self.wb_clear_btn.setCursor(Qt.PointingHandCursor)
        self.wb_clear_btn.setFixedHeight(24)
        self.wb_clear_btn.setToolTip("清空单词本（会先确认；清空后可撤销）")
        self.wb_clear_btn.clicked.connect(self._clear_wordbook)
        brow.addWidget(self.wb_clear_btn)
        l.addLayout(brow)
        return w

    # ---------------------------------------------------------------- 撤销
    def _push_undo(self, label, restore, cost=0):
        """压入一步可撤销操作。

        label 用于按钮/提示文字，restore 负责还原；
        cost = 该快照占用的**条数**，用于内存封顶（见下）。
        """
        self._undo_stack.append((label, restore, cost))
        self._undo_cost += cost
        # 双重封顶：步数 + 条数。
        #   只按步数封顶是不够的 —— 搜索历史表没有上限，长期使用可能长到
        #   几千行；30 步快照全留着就是几万个元组常驻内存。撤销最多追溯到
        #   几十步就够了，为它长期占几十 MB 完全不值当（用户刚投诉过卡的
        #   问题，这种隐性开销要提前掐掉）。
        #   至少保留 1 步：哪怕单次快照就超过预算，也不能压得栈为空。
        while (len(self._undo_stack) > self._UNDO_MAX
               or (self._undo_cost > self._UNDO_COST
                   and len(self._undo_stack) > 1)):
            _, _, c = self._undo_stack.pop(0)
            self._undo_cost -= c
        self._sync_undo_btn()

    def _do_undo(self):
        """撤销最近一次破坏性操作。"""
        if not self._undo_stack:
            self.pron_now.setText("没有可撤销的操作")
            return
        label, restore, cost = self._undo_stack.pop()
        self._undo_cost -= cost
        n = -1
        try:
            n = restore()
        except Exception:
            n = -1
        self._sync_undo_btn()
        # 撤销后所有视图都可能变了，统一刷新
        self._refresh_history()
        self._refresh_wordbook()
        if self._cur_word:
            self._render(self._cur_word, record=False)
        if n is not None and n >= 0:
            self.pron_now.setText(f"已撤销「{label}」（恢复 {n} 项）")
        else:
            self.pron_now.setText(f"已撤销「{label}」")

    def _sync_undo_btn(self):
        """按栈深同步撤销按钮与说明文字的可用状态。"""
        if not hasattr(self, "undo_btn"):
            return
        n = len(self._undo_stack)
        self.undo_btn.setEnabled(n > 0)
        if n == 0:
            self.undo_btn.setToolTip("暂无可撤销的操作（Ctrl+Z）")
        else:
            label = self._undo_stack[-1][0]
            self.undo_btn.setToolTip(
                f"撤销最近一步：{label}（Ctrl+Z）"
                + (f"　栈内还有 {n - 1} 步" if n > 1 else ""))
        if hasattr(self, "undo_hint"):
            if n == 0:
                self.undo_hint.setText("暂无可撤销的操作")
                self.undo_hint.setToolTip("")
            else:
                lab = self._undo_stack[-1][0]
                self.undo_hint.setToolTip(
                    "点击「↩ 撤销」可恢复：" + lab
                    + (f"（栈内还有 {n - 1} 步）" if n > 1 else ""))
                # ⚠ 侧栏只有 246px，这一行「按钮 72 + 间距 6 + 说明」必须夹住。
                #   实测硬编码截断（截到 16 字）仍然超宽：理想宽 187px > 实得
                #   138px，文字被 Qt 硬裁掉一半。改用字体度量做省略号截断 ——
                #   中英数字混排的字宽本来就不一样，只有按真实字宽算才准。
                full = "可撤销：" + lab
                avail = max(70, self.undo_hint.width() - 4)
                self.undo_hint.setText(
                    self.undo_hint.fontMetrics().elidedText(
                        full, Qt.ElideRight, avail))

    # -------------------------------------------------------- 历史 / 单词本 行为
    def _refresh_history(self):
        rows = self.store.history()
        self.hist_list.clear()
        for word, _ts in rows:
            it = QListWidgetItem(word)
            it.setData(Qt.UserRole, word)
            it.setToolTip("点击重新查询；右键可删除")
            self.hist_list.addItem(it)
        self.hist_empty.setVisible(len(rows) == 0)
        self.hist_list.setVisible(len(rows) > 0)
        self._sync_undo_btn()

    def _clear_history(self):
        """清空搜索历史 —— 带确认 + **真**撤销。

        ⚠ 旧版弹窗写着「此操作可撤销」，但代码里清完就没了，
        那句承诺是假的（用户反馈「看不到操作撤销的按钮」正是这个）。
        现在先快照，清空后可用底部「↩ 撤销」或 Ctrl+Z 原样恢复。
        """
        rows = self.store.history()
        if not rows:
            self.pron_now.setText("搜索历史本来就是空的")
            return
        r = QMessageBox.question(
            self, "清空搜索历史",
            f"确定要清空全部 {len(rows)} 条搜索历史吗？\n\n"
            f"清空后可以点底部「↩ 撤销」或按 Ctrl+Z 恢复。",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if r != QMessageBox.Yes:
            return
        snap = self.store.snapshot_history()
        self.store.clear_history()
        self._push_undo("清空搜索历史 %d 条" % len(rows),
                        lambda: self.store.restore_history(snap),
                        cost=len(snap))
        self._refresh_history()
        self.pron_now.setText(
            f"已清空 {len(rows)} 条搜索历史 · 可撤销（Ctrl+Z）")

    def _clear_wordbook(self):
        """一键清空单词本 —— 用户明确要求的功能。

        确认框里给出**精确数量**并让用户选择清哪个范围：
          当前分组 / 全部分组 / 取消（默认）。
        数量为 0 时对应按钮直接不出现，避免「点了没反应」的困惑。
        无论清哪个范围都会入撤销栈，清错了能一键回来。
        """
        gid = self._cur_wb_group()
        gname = self.wb_group.currentText() or "当前分组"
        n_cur = self.store.count_words(gid)
        n_all = self.store.count_words(None)
        n_grp = len(self.store.groups())

        box = QMessageBox(self)
        box.setIcon(QMessageBox.Warning)
        box.setWindowTitle("清空单词本")
        box.setText("确定要清空单词本吗？")
        box.setInformativeText(
            f"当前分组「{gname}」有 <b>{n_cur}</b> 个词，"
            f"全部 {n_grp} 个分组共 <b>{n_all}</b> 个词。<br><br>"
            f"清空后可以点底部「<b>↩ 撤销</b>」或按 Ctrl+Z 恢复。")
        btn_cur = btn_all = None
        if n_cur > 0:
            btn_cur = box.addButton(
                "清空当前分组（%d 词）" % n_cur, QMessageBox.AcceptRole)
        if n_all > 0:
            btn_all = box.addButton(
                "清空全部分组（%d 词）" % n_all, QMessageBox.DestructiveRole)
        cancel = box.addButton("取消", QMessageBox.RejectRole)
        box.setDefaultButton(cancel)          # 回车 = 取消，防误删
        box.exec()
        clicked = box.clickedButton()
        if clicked is None or clicked is cancel:
            self.pron_now.setText("已取消清空")
            return

        if clicked is btn_all:
            snap = self.store.snapshot_words(None)
            self.store.clear_words()
            self._push_undo("清空单词本 %d 词" % n_all,
                            lambda: self.store.restore_words(snap, None),
                            cost=len(snap))
            done, label = n_all, "全部分组"
        else:
            snap = self.store.snapshot_words(gid)
            self.store.clear_words_group(gid)
            self._push_undo("清空「%s」%d 词" % (gname, n_cur),
                            lambda: self.store.restore_words(snap, gid),
                            cost=len(snap))
            done, label = n_cur, "分组「%s」" % gname

        self._reload_wb_list()
        if self._cur_word:
            self._render(self._cur_word, record=False)
        self.pron_now.setText(
            f"已清空{label}的 {done} 个单词 · 可撤销（Ctrl+Z）")

    def _on_hist_activate(self, it):
        w = it.data(Qt.UserRole)
        if w:
            self.search_edit.setText(w)
            self._render(w, record=True)

    def _hist_menu(self, pos):
        it = self.hist_list.itemAt(pos)
        if not it:
            return
        menu = QMenu(self)
        act = menu.addAction("删除这条记录")
        chosen = menu.exec(self.hist_list.mapToGlobal(pos))
        if chosen == act:
            w = it.data(Qt.UserRole)
            snap = self.store.snapshot_history()      # 删除也可撤销
            self.store.delete_history(w)
            self._push_undo("删除历史「%s」" % w,
                            lambda: self.store.restore_history(snap),
                            cost=len(snap))
            self._refresh_history()
            self.pron_now.setText(f"已删除历史：{w} · 可撤销（Ctrl+Z）")

    def _cur_wb_group(self):
        gid = self.wb_group.currentData()
        return gid if gid is not None else 0

    def _refresh_wordbook(self):
        """重建分组下拉框 + 刷新词表。

        ⚠ 必须保留当前选中的分组（2026-09-18 修复）：
          `wb_group.clear()` 会把 currentIndex 归 0，重建后用户正在看的
          「四级」会被无声切回「默认分组」。触发路径最容易撞上的是
          **撤销** —— `_do_undo` 会调本方法，于是「撤销清空」之后
          用户发现自己跑到别的分组去了，很容易以为词丢了。
        """
        cur = self._cur_wb_group()
        self.wb_group.blockSignals(True)
        self.wb_group.clear()
        for g in self.store.groups():
            self.wb_group.addItem(g["name"], g["id"])
        idx = self.wb_group.findData(cur)
        if idx >= 0:
            self.wb_group.setCurrentIndex(idx)
        self.wb_group.blockSignals(False)
        self._reload_wb_list()

    def _reload_wb_list(self):
        gid = self._cur_wb_group()
        rows = self.store.words(gid)
        self.wb_list.clear()
        for word, note, _ts in rows:
            it = QListWidgetItem(word)
            it.setData(Qt.UserRole, word)
            tip = "点击重新查询；右键可移出单词本"
            if note:
                tip += "\n\n笔记：" + note[:600]
            it.setToolTip(tip)
            self.wb_list.addItem(it)
        self.wb_count.setText(f"{len(rows)} 词")

    def _on_wb_group(self):
        self._reload_wb_list()

    def _new_group(self):
        name, ok = QInputDialog.getText(
            self, "新建分组", "分组名称：", text="")
        if not ok:
            return
        name = (name or "").strip()
        if not name:
            return
        if self.store.add_group(name) < 0:
            self.pron_now.setText("分组已存在或创建失败")
            return
        self._refresh_wordbook()
        # 切到新分组
        for i in range(self.wb_group.count()):
            if self.wb_group.itemText(i) == name:
                self.wb_group.setCurrentIndex(i)
                break
        self.pron_now.setText(f"已新建分组：{name}")

    def _on_wb_activate(self, it):
        w = it.data(Qt.UserRole)
        if w:
            self.search_edit.setText(w)
            self._render(w, record=True)

    def _wb_menu(self, pos):
        it = self.wb_list.itemAt(pos)
        if not it:
            return
        menu = QMenu(self)
        act = menu.addAction("移出单词本")
        chosen = menu.exec(self.wb_list.mapToGlobal(pos))
        if chosen == act:
            w = it.data(Qt.UserRole)
            gid = self._cur_wb_group()
            snap = self.store.snapshot_words(gid)     # 移出也可撤销
            self.store.remove_word(w, gid)
            self._push_undo("移出单词本「%s」" % w,
                            lambda: self.store.restore_words(snap, gid),
                            cost=len(snap))
            self._reload_wb_list()
            self.pron_now.setText(f"已移出单词本：{w} · 可撤销（Ctrl+Z）")
            if self._cur_word == w:
                self._render(w, record=False)

    def _export_words(self):
        rows = self.store.words(self._cur_wb_group())
        if not rows:
            self.pron_now.setText("当前分组没有单词")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "导出单词本", "单词本.txt", "文本文件 (*.txt)")
        if not path:
            return
        n = self.store.export_words(path, self._cur_wb_group())
        if n >= 0:
            self.pron_now.setText(f"已导出 {n} 个单词到 {path}")
        else:
            self.pron_now.setText("导出失败，请检查路径是否可写")

    def _toggle_fav(self):
        w = self._cur_word
        if not w:
            return
        gid = self._cur_wb_group()
        if self.store.has_word(w, gid):
            self.store.remove_word(w, gid)
            self.pron_now.setText(f"已取消收藏：{w}")
        else:
            self.store.add_word(w, gid)
            self.pron_now.setText(f"已收藏「{w}」到 {self.wb_group.currentText()}")
        self._reload_wb_list()
        self._render(w, record=False)

    def _sync_fav_btn(self):
        """把底部收藏按钮的文字/状态同步到当前词。

        底部按钮是「无状态渲染」的 —— 每次换词都必须重新对齐，
        否则会出现「已经换了单词，按钮还显示上一个词的收藏状态」。
        """
        if not hasattr(self, "fav_btn"):
            return
        w = self._cur_word
        if not w:
            self.fav_btn.setText("☆ 收藏")
            self.fav_btn.setEnabled(False)
            self.fav_btn.setToolTip("先查一个单词再收藏")
            return
        self.fav_btn.setEnabled(True)
        faved = self.store.has_word(w, self._cur_wb_group())
        self.fav_btn.setText("★ 已收藏" if faved else "☆ 收藏")
        self.fav_btn.setToolTip(
            ("取消收藏「%s」" % w) if faved else ("收藏「%s」到单词本（Ctrl+D）" % w)
        )

    # ------------------------------------------------------------ 主题
    def _apply_theme(self):
        self.setStyleSheet(f"""
            QWidget {{
                background: {PAPER};
                color: {INK};
                font-family: "Microsoft YaHei", "Segoe UI", sans-serif;
            }}
            #header {{ background: {PAPER}; }}
            #sbox {{ background: {PAPER}; }}
            #card {{
                background: #ffffff;
                border: 1px solid {LINE};
                border-radius: 10px;
            }}
            #listHint {{
                color: {INK_FAINT};
                font-size: 11px;
                font-weight: 600;
                letter-spacing: 1px;
                background: transparent;
            }}
            #search {{
                background: #ffffff;
                border: 1.4px solid {LINE};
                border-radius: 23px;
                padding-left: 20px;
                padding-right: 20px;
                font-size: 15px;
                color: {INK};
                selection-background-color: {SEAL};
            }}
            #search:focus {{
                border: 1.6px solid {SEAL};
            }}
            #transBtn {{
                background: {SEAL};
                color: #ffffff;
                border: none;
                border-radius: 23px;
                font-size: 14px;
                font-weight: 600;
                padding: 0;
            }}
            #transBtn:hover {{ background: #992c26; }}
            QPushButton {{
                background: #ffffff;
                border: 1px solid {LINE};
                border-radius: 14px;
                padding: 0 15px;
                color: {INK_SOFT};
                font-size: 12px;
            }}
            QPushButton:hover {{ border-color: {SEAL}; color: {SEAL}; }}
            QPushButton:checked {{
                background: {SEAL}; color: #ffffff; border-color: {SEAL};
                font-weight: 600;
            }}
            QComboBox {{
                background: #ffffff; border: 1px solid {LINE};
                border-radius: 15px; padding-left: 12px;
                color: {INK}; font-size: 12px;
            }}
            QComboBox:hover {{ border-color: {SEAL}; }}
            QComboBox::drop-down {{ border: none; width: 22px; }}
            QComboBox QAbstractItemView {{
                background: #ffffff; border: 1px solid {LINE};
                selection-background-color: {PAPER_ALT};
                selection-color: {INK}; outline: none;
                padding: 4px;
            }}
            #results {{
                background: transparent;
                outline: none;
                padding: 2px 4px 8px 4px;
            }}
            #results::item {{
                padding: 7px 8px;
                border-bottom: 1px solid {LINE};
                color: {INK};
            }}
            #results::item:selected {{
                background: {PAPER_ALT};
                border-left: 3px solid {SEAL};
                color: {INK};
            }}
            #detail {{
                background: #ffffff;
                border: none;
                padding: 22px 28px;
                font-size: 14px;
            }}
            #pronBar {{
                background: {PAPER_ALT};
                border-top: 1px solid {LINE};
            }}
            #aiBar {{
                background: #fdfcf9;
                border-top: 1px dashed {LINE};
            }}
            #aiLabel {{
                color: {SEAL};
                font-size: 11px;
                font-weight: 700;
                letter-spacing: 1.6px;
                background: transparent;
                margin-right: 2px;
            }}
            #aiBtn {{
                background: #ffffff;
                border: 1px solid #e8dcd2;
                border-radius: 13px;
                padding: 0 12px;
                color: #8a5a3c;
                font-size: 11.5px;
            }}
            #aiBtn:hover {{
                background: {SEAL};
                border-color: {SEAL};
                color: #ffffff;
            }}
            #aiSvc {{
                background: #ffffff; border: 1px solid #e8dcd2;
                border-radius: 13px; padding-left: 10px;
                color: #8a5a3c; font-size: 11.5px;
            }}
            #aiSvc:hover {{ border-color: {SEAL}; }}
            #odBar {{
                background: transparent;
            }}
            #odBar QLabel {{
                color: {INK_FAINT};
                font-size: 11px;
                font-weight: 600;
                letter-spacing: 1.2px;
                background: transparent;
                margin-right: 2px;
            }}
            #odBtn {{
                background: {PAPER_ALT};
                border: 1px solid {LINE};
                border-radius: 4px;
                padding: 0 11px;
                color: {INK_SOFT};
                font-size: 11.5px;
            }}
            #odBtn:hover {{
                background: #ffffff;
                border-color: {BLUE};
                color: {BLUE};
            }}
            #odBtn:pressed {{
                background: {BLUE};
                border-color: {BLUE};
                color: #ffffff;
            }}
            #pronLabel {{
                color: {INK_FAINT};
                font-size: 11px;
                font-weight: 600;
                letter-spacing: 1px;
                background: transparent;
                margin-right: 4px;
            }}
            #pronNow {{
                color: {INK_SOFT};
                font-size: 11.5px;
                background: transparent;
                padding-left: 6px;
            }}
            #favBtn {{
                background: {PAPER_ALT};
                border: 1px solid {LINE};
                border-radius: 8px;
                color: {INK_SOFT};
                font-size: 11.5px;
                font-weight: 600;
                padding: 2px 8px;
                margin-left: 4px;
            }}
            #favBtn:hover {{
                background: #FFF6E8;
                border-color: #B8860B;
                color: #B8860B;
            }}
            #favBtn:checked {{
                background: #F6E7D8;
                border-color: {SEAL};
                color: {SEAL};
            }}
            #cfgHint {{
                color: {INK_FAINT};
                font-size: 11px;
                background: {PAPER_ALT};
                border: 1px solid {LINE};
                border-radius: 8px;
                padding: 1px 7px;
                margin-left: 6px;
            }}
            #cfgHint:hover {{
                color: {INK};
                border-color: {RULE_RED};
            }}
            #accentBox {{
                background: {PAPER_ALT};
                border: 1px solid {LINE};
                border-radius: 8px;
                color: {INK_SOFT};
                font-size: 11.5px;
                padding: 0 6px;
            }}
            #accentBox:hover {{
                border-color: {SEAL};
                color: {INK};
            }}
            #accentBox::drop-down {{
                border: none;
                width: 16px;
            }}
            #accentBox QAbstractItemView {{
                background: #ffffff;
                border: 1px solid {LINE};
                color: {INK};
                selection-background-color: {PAPER_ALT};
                selection-color: {SEAL};
                outline: none;
            }}
            #statTitle {{
                color: {INK_FAINT};
                font-size: 11px;
                font-weight: 700;
                letter-spacing: 2px;
                background: transparent;
            }}
            #tipTitle {{
                color: {INK_SOFT};
                font-size: 11px;
                font-weight: 700;
                letter-spacing: 1px;
                background: transparent;
            }}
            #tip {{
                background: {PAPER_ALT};
                border: 1px solid {LINE};
                border-radius: 8px;
                padding: 10px;
                color: {INK_SOFT};
                font-size: 11px;
                line-height: 165%;
            }}
            #sideTabs {{ background: transparent; }}
            #sideTabs::pane {{
                border: none;
                background: transparent;
            }}
            #sideTabs QTabBar::tab {{
                background: transparent;
                color: {INK_FAINT};
                font-size: 12px;
                padding: 6px 9px;
                border: none;
                border-bottom: 2px solid transparent;
            }}
            #sideTabs QTabBar::tab:selected {{
                color: {SEAL};
                border-bottom: 2px solid {SEAL};
                font-weight: 600;
            }}
            #histList, #wbList {{
                background: transparent;
                outline: none;
            }}
            #histList::item, #wbList::item {{
                padding: 6px 8px;
                border-bottom: 1px solid {LINE};
                color: {INK};
                font-size: 12.5px;
            }}
            #histList::item:selected, #wbList::item:selected {{
                background: {PAPER_ALT};
                color: {INK};
            }}
            #miniBtn {{
                background: #ffffff;
                border: 1px solid {LINE};
                border-radius: 12px;
                padding: 0 10px;
                color: {INK_SOFT};
                font-size: 11px;
            }}
            #miniBtn:hover {{
                border-color: {SEAL};
                color: {SEAL};
            }}
            #dangerBtn {{
                background: #ffffff;
                border: 1px solid #E2C3C0;
                border-radius: 12px;
                padding: 0 10px;
                color: {SEAL};
                font-size: 11px;
            }}
            #dangerBtn:hover {{
                background: {SEAL};
                border-color: {SEAL};
                color: #ffffff;
            }}
            /* 撤销按钮：与「收藏」同一视觉层级（用户投诉过找不到按钮，
               这里宁可稍微抢眼也不要藏起来）。禁用态天然变淡，
               等于把「当前有没有可撤销的操作」直接告诉用户。 */
            #undoBtn {{
                background: {PAPER_ALT};
                border: 1px solid {LINE};
                border-radius: 8px;
                color: {INK_SOFT};
                font-size: 11.5px;
                font-weight: 600;
                padding: 2px 8px;
                margin-left: 4px;
            }}
            #undoBtn:hover {{
                background: #FFF6E8;
                border-color: {GOLD};
                color: #8a6400;
            }}
            #undoBtn:disabled {{
                background: transparent;
                border-color: {LINE};
                color: {INK_FAINT};
            }}
            #emptyHint {{
                color: {INK_FAINT};
                font-size: 11px;
                background: transparent;
            }}
            QScrollBar:vertical {{
                background: transparent; width: 9px; margin: 2px;
            }}
            QScrollBar::handle:vertical {{
                background: #d8d5cc; border-radius: 4px; min-height: 30px;
            }}
            QScrollBar::handle:vertical:hover {{ background: {SEAL}; }}
            QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; }}
            QScrollBar::add-page, QScrollBar::sub-page {{ background: none; }}
        """)

    # ------------------------------------------------------------ 交互
    def _on_lang(self, idx):
        k = self.lang_box.itemData(idx)
        self.lang = k
        self.engine = self.dicts.get(k) or self.dicts["en"]
        label = LANG_DEFS[k]["label"]

        # 离开英语时解除「锁定中译英」。
        # 该模式只对英语词库有意义；若不重置，切到日/法/粤语后会残留锁定状态。
        if k != "en" and self._cn_locked:
            self._cn_locked = False
            self.cn_btn.setChecked(False)

        if self.engine and self.engine.con:
            if k == "en":
                self._update_direction_hint(self.search_edit.text())
            else:
                self.search_edit.setPlaceholderText(
                    f"输入{label}词语，即时查询…   ↑↓ 切换  Esc 清空"
                )
        else:
            self.search_edit.setPlaceholderText(
                f"{label}词库尚未安装（{LANG_DEFS[k]['db']} 缺失）"
            )
        self._refresh_dict_buttons()
        self._update_tip()
        self._load_stats()
        txt = self.search_edit.text()
        if txt.strip():
            # 切语言是「一次性」动作，不是打字，不该等防抖 —— 直接查。
            self._query_timer.stop()
            self._on_text_now(txt)

    def _flush_query(self):
        """防抖到期 → 立即执行挂起的查询。"""
        self._query_timer.stop()
        self._on_text_now(self._pending_text)

    def _on_dict(self, idx):
        self.cur_dict_idx = idx
        txt = self.search_edit.text()
        if txt.strip():
            # 切词表同理：用户点了按钮就该立刻看到新结果。
            self._query_timer.stop()
            self._on_text_now(txt)

    def _refresh_dict_buttons(self):
        is_en = self.lang == "en"
        for b in self.dict_buttons:
            b.setVisible(is_en and not self._cn_locked)
        self.cn_btn.setVisible(is_en)
        if is_en:
            self.dict_buttons[self.cur_dict_idx].setChecked(True)
        # 非英语只保留「口音」发音（按该语言语音朗读），并隐藏多余标签
        self.pron_label.setVisible(is_en)
        NAMES = {"us": "美式", "uk": "英式", "edge": "口音"}
        for b in self.pron_buttons:
            if is_en:
                b.setVisible(True)
                b.label = NAMES[b.accent]
                b.setText(f"  {b.label}")
            else:
                b.setVisible(b.accent == "edge")
                if b.accent == "edge":
                    b.label = "朗读"
                    b.setText("  朗读")
        # 口音下拉只在英文 + 显示「口音」按钮时有意义
        self.accent_box.setVisible(is_en)

    def _on_accent_change(self, idx):
        """切换口音：存进配置 + 状态栏提示。

        立刻落盘（而不是等退出时保存），这样用户换完口音即使程序崩溃、
        或被任务管理器强杀，下次打开也还是他选的那个。
        """
        code = self.accent_box.itemData(idx) or ""
        label = self.accent_box.itemText(idx) or ""
        if not code:
            return
        CONFIG["edge_accent"] = code
        p = CONFIG_PATH or os.path.join(app_dir(), CONFIG_FILE)
        try:
            # 先读回原文件，保留用户自己加的注释键（_xxx_说明），只改我们这项
            data = {}
            if os.path.exists(p):
                with open(p, "r", encoding="utf-8") as f:
                    old = json.load(f)
                if isinstance(old, dict):
                    data = old
            data["edge_accent"] = code
            with open(p, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass
        self._refresh_cfg_hint()
        self.pron_now.setText(f"口音已切换为 {label}，点「口音」试听")

    # ------------------------------------------------------- 输入方向识别
    @staticmethod
    def detect_direction(text):
        """自动判断查词方向。

        返回 "cn2en"（输入含中文）或 "en2cn"（输入是英文/其他）。
        设计原则：用户不必手动切换方向——输入什么就查什么。
        含任意中日韩统一表意文字即视为中文输入。
        """
        for ch in text or "":
            if "\u4e00" <= ch <= "\u9fff":      # CJK 基本区
                return "cn2en"
        return "en2cn"

    def _on_cn_toggle(self):
        """「中 ⇄ 英」按钮：切换「自动 / 锁定中译英」两种状态。

        默认是自动模式（按钮不按下）——输入中文自动查英文，
        输入英文自动查英文释义，无需手动切换。
        按下则强制中译英，用于查询「含中文的英文释义」等特殊情况。
        """
        locked = self.cn_btn.isChecked()
        self._cn_locked = locked
        for b in self.dict_buttons:
            b.setVisible(not locked and self.lang == "en")
        t = self.search_edit.text()
        if t.strip():
            self._query_timer.stop()
            self._on_text_now(t)
        else:
            self._update_direction_hint()

    def _update_direction_hint(self, text=""):
        """根据当前输入内容，更新搜索框提示与方向按钮文案。"""
        if self.lang != "en":
            self.cn_btn.setText("中 ⇄ 英")
            return
        if self._cn_locked:
            self.search_edit.setPlaceholderText("输入中文，反查英文单词…")
            self.cn_btn.setText("锁定中文")
            return
        # 自动模式：按当前内容提示
        if self.detect_direction(text) == "cn2en" and (text or "").strip():
            self.search_edit.setPlaceholderText("输入中文，反查英文单词…")
        else:
            self.search_edit.setPlaceholderText(
                "输入中文或英文，自动判断方向…   ↑↓ 切换  Esc 清空"
            )
        self.cn_btn.setText("自动识别")

    def _dict_key(self):
        return DICTS[self.cur_dict_idx]["key"]

    def _on_letter(self, ch):
        self.search_edit.setText(ch)
        self.search_edit.setFocus()

    def _show_cn_results(self, t):
        """渲染中文反查结果（离线 + 已联网补充的合并结果）。

        抽成独立方法是因为有两条调用路径：初次输入、以及联网补充
        回来后重渲染。两条路径必须渲染得完全一样。

        ⚠ 必须自己先 clear()（2026-09-17 修复）：
          原先假定「调用方已经清过列表」，于是初次输入那条路径没问题
          （_on_text_now 里 clear 过），但**联网补充回来后的重渲染**
          （见 _schedule_cn_en 里的 _show_cn_results 调用）是在一个
          已经填满的列表上再 addItem 一遍 —— 结果每一行都出现两次。

          实测症状：查「开心」时列表是
            ['chuffed','rejoice','joyful','chuffed','happy','grand','delighted']
          共 7 条，而引擎实际只返回 6 条，chuffed 重复。

          修法：把 clear() 放进本方法内，让两条路径都自洽，
          不再依赖调用方的清列表动作 —— 这类「隐式前置条件」
          正是重复渲染类 bug 的温床。
        """
        # 同 _on_text_now：程序化填充期间抑制「选中变化 = 用户操作」的误判，
        # 避免把中间态词写进搜索历史（commit 实测 47ms）。
        # 闸门必须包住 clear() —— 它本身也会发 currentRowChanged。
        # 用计数而非布尔：本方法既被 _on_text_now 调用（嵌套），
        # 也被联网补充回来的回调单独调用（非嵌套）。
        self._loading_list += 1
        try:
            self.result_list.clear()
            # 列表清空了，之前的预览记录也失效 —— 必须重置，
            # 否则「清空输入框再重打同一个词」会因 w == _preview_word
            # 而被去重逻辑跳过渲染，详情栏停在欢迎页（陈旧）。
            self._preview_word = None
            rows = self.engine.search_cn(t)
            self._cn_rows_now = rows
            self.list_hint.setText(f"中文反查 · {len(rows)} 条")
            for r in rows:
                it = QListWidgetItem()
                it.setData(Qt.UserRole, r["word"])
                zh = re.sub(r"\\n", " ", r.get("zh") or "")
                it.setText(f"{r['word']}\n     {zh[:36]}")
                self.result_list.addItem(it)
            if rows:
                self.result_list.setCurrentRow(0)
            else:
                self._show_empty_cn(t)
        finally:
            self._loading_list -= 1

    def _schedule_cn_en(self, word):
        """异步取中文词的英文表达（有道 ce 词表）。

        标记 _cn_en_fetching 防止重复请求：防抖之后同一词仍可能因
        用户来回删改而被触发多次。无论成功失败都登记
        DictEngine.set_cn_extra（失败记空表），这样下次不会再打网络。
        """
        if word in self._cn_en_fetching:
            return
        self._cn_en_fetching.add(word)

        def on_done(items):
            # 已经回到主线程，这里可以安全碰引擎缓存与 GUI
            DictEngine.set_cn_extra(word, items or [])
            self._cn_en_fetching.discard(word)
            # 用户可能已经改了输入 —— 只在仍是同一个词时刷新
            if self._last_query == word and self._cn_ok_now():
                self.engine._cache.clear()
                self._show_cn_results(word)

        # ⚠ 用真线程而不是 QTimer.singleShot —— 后者只推迟、不换线程，
        #   请求照样冻界面（本机实测 fetch_cn_en 330~416ms）。
        run_async(lambda: fetch_cn_en(word), on_done)

    # ------------------------------------------------- 中文 → 外语 反查（在线）
    def _search_cn_foreign(self, t):
        """非英语模式：把中文机翻成当前语言，再回本地词库查（异步）。

        为什么必须联网：日语/法语/粤语词库里**没有中文**（实测
        dict_ja/fr/yue 的 cn_index 是 0 行、translation 字段全为空），
        离线根本无从匹配。所以只能「中文 → 机翻成目标语言 → 本地查该外语词」。
        实测（_tr_probe7.py）：水→水、吃→食べる、朋友→友達、谢谢→感謝，
        粤语几乎全对（家→屋企、为什么→點解），法语偏差较大。

        为什么必须异步：单次 1.3~1.9s。同步等会冻界面（用户投诉过卡顿），
        所以先立刻给出「联网翻译中」的反馈，结果回来再填列表。
        """
        key = (self.lang, t)
        lab = LANG_DEFS.get(self.lang, {}).get("label", "")

        hit = self._cn_fr_cache.get(key)
        if hit is not None:
            # 命中缓存：直接渲染，不联网、不等待（同一词反复改输入时很常见）
            self._render_cn_foreign(t, hit[0], hit[1])
            return

        self._cn_fr_req += 1
        req = self._cn_fr_req
        self._show_cn_foreign_wait(t, lab)
        self.list_hint.setText("中文反查 · 联网翻译中…")

        def on_done(res):
            # 已被更新的输入取代 → 丢弃。
            # （防抖 220ms 之后仍可能连发两次，例如快速输入「水」→「水果」）
            if req != self._cn_fr_req or self._last_query != t:
                return
            r, src = res if res else (None, None)
            self._cn_fr_cache[key] = (r, src)
            self._render_cn_foreign(t, r, src)

        # strict=False：这条路径要的就是机翻文本里的候选词切片。
        # 粤语尤其依赖简→繁转换（粤词库收的是繁体字形），
        # 所以不能套 strict 的语言闸门（zh-CN|yue 返回的本来就没有粤式字）。
        run_async(lambda: translate_text(t, self.lang, strict=False), on_done)

    def _show_cn_foreign_wait(self, t, lab):
        """等待期间的占位：清空列表 + 说明正在做什么（不让界面看起来卡住）。"""
        self._loading_list += 1
        try:
            self.result_list.clear()
            # 同 _show_cn_results：列表清了，预览记录必须一起失效
            self._preview_word = None
        finally:
            self._loading_list -= 1
        self.detail.setHtml(f"""
        <div style='font-family:Georgia,serif;'>
          <div style='font-size:20px;color:{INK_FAINT};'>正在把
            <b style='color:{INK};'>{self._esc(t)}</b> 翻成{lab}…</div>
          <div style='margin-top:8px;font-size:12.5px;color:{INK_SOFT};line-height:190%;'>
            {lab}词库没有中文索引，需要先联网翻译，再回词库检索。
            <br>通常 1~2 秒。
          </div>
        </div>
        """)

    def _render_cn_foreign(self, t, tr_text, src):
        """渲染「中文 → 外语」反查结果：机翻候选 → 本地词库命中。"""
        cands = _tr_candidates(tr_text)
        hits, seen = [], set()
        for c in cands:
            for r in self.engine.suggest(c, 8, self._dict_key()):
                w = r.get("word") or ""
                if w and w not in seen:
                    seen.add(w)
                    hits.append(r)
        self._cn_fr_now = (t, tr_text, cands, hits)

        # 同到处：程序化填充期间必须压下「选中变化 = 用户操作」的误判，
        # 否则会把中间态词写进搜索历史
        self._loading_list += 1
        try:
            self.result_list.clear()
            self._preview_word = None
            for r in hits:
                it = QListWidgetItem()
                it.setData(Qt.UserRole, r["word"])
                ph = r.get("phonetic") or ""
                it.setText(f"{r['word']}" + (f"   /{ph}/" if ph else ""))
                self.result_list.addItem(it)
            if hits:
                self.list_hint.setText(
                    f"中文反查 · {len(hits)} 条（机翻 {tr_text[:14]}）")
                self.result_list.setCurrentRow(0)
            else:
                self.list_hint.setText("中文反查 · 词库未收录")
                self._show_cn_foreign_detail(t, tr_text, src, cands)
        finally:
            self._loading_list -= 1

    def _show_cn_foreign_detail(self, t, tr_text, src, cands):
        """词库里没有对应的外语词 —— 如实说明，并把机翻结果原样交给用户。

        不编：查不到就说查不到，但用户至少拿到了「这个词这么说」，
        比一句「未找到」有用得多。
        """
        lab = LANG_DEFS.get(self.lang, {}).get("label", "")
        if not tr_text:
            self.detail.setHtml(f"""
            <div style='font-family:Georgia,serif;'>
              <div style='font-size:20px;color:{INK_FAINT};'>联网翻译没取到结果</div>
              <div style='margin-top:8px;font-size:12.5px;color:{INK_SOFT};line-height:190%;'>
                可能是网络不通或额度用尽。<br>
                可以稍后重试，或点工具栏「翻译」把整句拿去翻。
              </div>
            </div>
            """)
            return
        cand_html = "　".join(self._esc(c) for c in cands[:4])
        self.detail.setHtml(f"""
        <div style='font-family:Georgia,serif;'>
          <div style='font-size:22px;color:{INK_FAINT};'>{lab}词库里没有
            <b style='color:{INK};'>{self._esc(t)}</b> 对应的词条</div>
          <div style='margin-top:10px;font-size:13px;color:{INK_SOFT};line-height:190%;'>
            机翻结果（{self._esc(src or '在线翻译')}）：<br>
            <span style='font-size:19px;color:{INK};'>{self._esc(tr_text)}</span>
            <div style='margin-top:10px;'>取词候选：{cand_html}</div>
            <div style='margin-top:6px;'>词库未收录该词形（可能是动词活用形、
            敬体或生僻词），可以切「全部」词典再看看。</div>
          </div>
        </div>
        """)

    def _cn_ok_now(self):
        """当前上下文是否仍是「英语词库 + 中文方向」。（联网回来后复查）"""
        if self.lang != "en" or not self.engine or not self.engine.con:
            return False
        return True

    def _on_text(self, txt):
        """输入框内容变化 —— 只做「即时、零成本」的反馈，查询推迟。

        打字卡顿的本质是：每敲一个字母都同步跑一次 SQLite 查询，
        而中文反查/前缀建议在优化前要 90~700ms，键盘事件被主线程
        的查询堵住，用户看到的就是「按键掉字、光标滞后」。

        这里拆成两段：
          ① 立刻更新方向提示（纯字符串判断，微秒级）—— 保证界面
             对每次按键都有反馈，不会显得「没反应」。
          ② 把真正的查询丢进 220ms 单次定时器。连续打字时每次按键
             都重置定时器，于是只有「停手」那一刻才真正查一次。
             从 10 个字母的输入算起，查询次数从 10 次降到 1 次。
        """
        self._pending_text = txt
        if self.lang == "en":
            self._update_direction_hint(txt)
        self._query_timer.start(220)

    def _on_text_now(self, txt):
        """防抖定时器到期后真正执行的查询（原 _on_text 主体）。

        ⚠ 整个方法体都在 _loading_list 闸门内（2026-09-17）：
          列表的 clear() 与 setCurrentRow() **都会**发 currentRowChanged
          进而触发 _on_pick。那是「程序化填充」而非用户操作，若不抑制
          就会被当成「用户查了这个词」写进搜索历史 —— commit 实测 47ms，
          而且会把中间态词（如输入 water 时的 watershed）污染进历史。
          闸门必须从 clear() **之前**就生效：只包住填充循环是不够的
          （实测 clear() 那条路径仍会漏出去）。
        """
        self._loading_list += 1
        try:
            t = txt.strip()
            self._last_query = t
            self._auto = True   # 保留兼容（现由 _loading_list 主导）
            self.result_list.clear()
            # 同 _show_cn_results：列表清了，预览记录必须一起失效。
            # 否则「清空 → 重打同一个词」会被去重逻辑跳过渲染，
            # 详情栏停在欢迎页 —— 这是引入去重时最容易漏的一处。
            self._preview_word = None
            # 输入内容变化时同步更新方向提示（仅英语模式）
            if self.lang == "en":
                self._update_direction_hint(txt)

            if not t:
                self.list_hint.setText("候选词")
                self._show_welcome()
                return

            if not self.engine or not self.engine.con:
                self.list_hint.setText("词库缺失")
                self._show_missing_lang()
                return

            # 中译英（离线反查）只对英语词库有效。
            # 方向判断：默认自动识别（输入含中文就走中译英），
            # 若用户按下了「锁定中文」按钮则强制走中译英。
            direction = "cn2en" if (
                self._cn_locked and self.lang == "en"
            ) else self.detect_direction(t)

            if direction == "cn2en" and self.lang == "en":
                self._show_cn_results(t)
                # 词库缺中文近义映射时（happy 的释义里没有「开心」），
                # 结果会很少甚至为空。此时异步联网向有道 ce 词表要
                # 「中文 → 英文表达」，拿到后合并进候选重渲染。
                # 全程不阻塞：先按离线结果渲染，网络回来再刷新。
                if len(self._cn_rows_now) < 6 and not DictEngine.has_cn_extra(t):
                    self._schedule_cn_en(t)
                return

            # ---- 非英语模式的「中文 → 本语言」反查（2026-09-18 新增）----
            # 用户反馈「除了英语的其他语言为啥不能双向翻译」：旧版这里
            # 只判断 `and self.lang == "en"`，非英语模式输入中文会被当成
            # 外语词直接查，必然查不到 —— 中文反查等于完全不存在。
            #
            # ⚠ 顺序讲究：**先给本语言词条一次机会**。
            #   日语里「友達」「会社」「勉強」都是纯汉字，与中文同形，
            #   直接当外语词查是查得到的。若一律当中文去联网反查，
            #   反而要多等 1.5s，还可能被机翻带偏。
            #   所以：本地查得到 → 正常候选列表；查不到 → 才走在线反查。
            if self.lang != "en" and _is_zh_text(t):
                if not self.engine.suggest(t, 60, self._dict_key()):
                    self._search_cn_foreign(t)
                    return

            rows = self.engine.suggest(t, 60, self._dict_key())
            self.list_hint.setText(f"候选词 · {len(rows)}")
            for r in rows:
                it = QListWidgetItem()
                it.setData(Qt.UserRole, r["word"])
                ph = r.get("phonetic") or ""
                zh = re.sub(r"\\n", " ", r.get("translation") or "")
                zh = re.sub(r"\s+", " ", zh)[:32]
                if self.lang == "en":
                    it.setText(f"{r['word']}" + (f"   /{ph}/" if ph else "") + f"\n     {zh}")
                else:
                    # 非英语：主行显示原文，次行显示音标（或释义）
                    sub = f"/{ph}/" if ph else zh
                    it.setText(f"{r['word']}\n     {sub}")
                self.result_list.addItem(it)

            if rows:
                self.result_list.setCurrentRow(0)
            else:
                self._show_notfound(t)
        finally:
            self._loading_list -= 1

    def _commit_first(self):
        if self.result_list.count():
            self.result_list.setCurrentRow(0)
            self._on_pick(0)

    def _on_pick(self, row):
        if row < 0:
            return
        it = self.result_list.item(row)
        if not it:
            return
        w = it.data(Qt.UserRole)
        if not w:
            return
        if self._loading_list:
            # 程序化填充列表时的选中变化**不是**用户操作：
            #   只做词条预览，绝不写搜索历史。
            #   旧实现这里无条件 `record=not self._auto` 并立刻把 _auto
            #   清为 False，导致 Qt 第二次发 currentRowChanged 时被判成
            #   用户操作 → add_history → commit()（实测 47ms/次）。
            #   另外同一词不重复渲染（去重），省掉一次无谓的词条构建。
            if w != self._preview_word:
                self._preview_word = w
                self._render(w, record=False)
            return
        self._preview_word = w
        self._render(w, record=True)

    def _on_activate(self, it):
        w = it.data(Qt.UserRole)
        if w:
            self._render(w, record=True)

    def _on_anchor(self, url):
        s = url.toString()
        if s == "wb:toggle":
            self._toggle_fav()
            return
        if s == "nav:back":
            self._nav_back()
            return
        if s.startswith("phrase:"):
            # 「常用短语」板块里点了某个短语 —— 直接查该短语的完整词条
            p = s[7:].strip()
            if p:
                self.search_edit.setText(p)
                self.search_edit.setFocus()
                self._render(p, record=True)
            return
        if s.startswith("word:"):
            w = s[5:]
            self.search_edit.setText(w)
            self.search_edit.setFocus()
            self._render(w, record=True)
            return

    # ------------------------------------------------------------ 返回上一词
    def _make_word_undo(self, target, nav_snapshot):
        """构造一步「切回某个词」的撤销动作（连导航栈一起还原）。

        ⚠ 导航栈必须一并还原：否则撤销跳转之后，「↩ 返回」的落点会错位
          （本该退到更早的词，却退回了刚离开的那个词）。
        返回 None 表示「不报告恢复条数」，_do_undo 会只显示
        「已撤销『…』」而不带「（恢复 N 项）」。
        """
        def _restore():
            self._nav_stack = list(nav_snapshot)
            self.search_edit.setText(target)
            # record=False：这是在还原历史，不是一次新的用户查词，
            # 不能再写搜索历史、也不能再压一步撤销（否则 Ctrl+Z 会打转）
            self._render(target, record=False)
            return None
        return _restore

    def _nav_back(self):
        """返回上一个查的词（防误触）。

        ⚠ 2026-09-18：返回动作**自己也进撤销栈**。
          否则「返回」是单向门：跳转能撤销了、返回却不能，
          用户再按 Ctrl+Z 会撤销到更早的别的操作，行为难以预测。
          现在两个方向对称：
             跳转 A→B 可撤销（回到 A）
             返回 B→A 可撤销（回到 B）
        """
        if not self._nav_stack:
            self.pron_now.setText("没有上一步了")
            return
        prev = self._nav_stack.pop()
        cur = self._cur_word
        # 撤销「返回」时要恢复成**返回前**的导航状态 = 现在的栈 + prev
        nav_snap = list(self._nav_stack) + ([prev] if prev else [])
        self.search_edit.setText(prev)
        self._render(prev, record=False)
        if cur and cur != prev:
            self._push_undo("回到「%s」" % cur,
                            self._make_word_undo(cur, nav_snap))

    # ------------------------------------------------------------ 翻译
    def _open_translate(self):
        # 把当前语言模式传进去：于是中文 ⇄ 日语 / 法语 / 粤语 都是自动方向，
        # 而不是像旧版那样无论切到哪个语言都只翻中英。
        dlg = TranslateDialog(self, self.lang)
        dlg.exec()

    # ------------------------------------------------------------ AI 助手
    def _ai_open(self, task_key):
        """按当前站点设置打开 AI：网页模式走浏览器，站内模式走 API。

        网页流程：打开站点 → 把提问复制到剪贴板 → 提示「粘贴(Ctrl+V)发送」。
        ChatGPT 这类原生支持 ?q= 预填的站会额外走预填，双保险。
        站内流程：在 QDialog 中调用 DeepSeek API，支持追问和保存笔记。
        """
        from urllib.parse import quote

        task = next((t for t in AI_TASKS if t["key"] == task_key), None)
        if task is None:
            return

        # 「造句/写作检查」面向搜索框里的整句；其余面向当前词条
        if task_key == "writing":
            subject = (self.search_edit.text() or "").strip()
            if not subject:
                self.pron_now.setText("请先在搜索框输入要检查的句子")
                return
        else:
            subject = self._cur_word or (self.search_edit.text() or "").strip()
            if not subject:
                self.pron_now.setText("请先查一个词，再让 AI 讲解")
                return

        prompt = ai_build_prompt(task_key, subject, subject, self.lang)
        svc_key = self.ai_svc_box.currentData()
        svc = next((s for s in AI_SERVICES if s["key"] == svc_key), AI_SERVICES[0])

        if svc.get("internal"):
            note_word = subject if task_key != "writing" else ""
            self._ai_internal_open(prompt, subject, task, note_word)
            return

        # 先把提问复制到剪贴板（兜底，永远有效）
        copied = False
        try:
            QGuiApplication.clipboard().setText(prompt)
            copied = True
        except Exception:
            pass

        # 打开站点：支持原生预填的用预填 URL，否则用官网
        if svc.get("prefill"):
            url = svc["prefill"].format(q=quote(prompt, safe=""))
        else:
            url = svc["url"]
        ok = QDesktopServices.openUrl(QUrl(url))

        if ok:
            if svc.get("prefill"):
                self.pron_now.setText(
                    f"已打开 {svc['label']} · 问题已预填（未生效请粘贴）")
            elif copied:
                self.pron_now.setText(
                    f"已打开 {svc['label']} · 问题已复制，粘贴(Ctrl+V)发送")
            else:
                self.pron_now.setText(f"已打开 {svc['label']}")
        else:
            if copied:
                self.pron_now.setText(
                    f"未能打开浏览器 · 问题已复制，请手动打开 {svc['label']}")
            else:
                self.pron_now.setText("未能打开浏览器")

    def _ai_context(self, word):
        """提取少量本地词库信息作为站内 AI 的上下文，避免发送整条词库。"""
        try:
            d = self.engine.lookup(word, self._dict_key()) if self.engine else None
        except Exception:
            d = None
        if not d:
            return ""
        parts = []
        trans = (d.get("translation") or "").replace("\\n", "\n").strip()
        definition = (d.get("definition") or "").replace("\\n", "\n").strip()
        pos = (d.get("pos") or "").strip()
        if pos:
            parts.append("词性：" + pos[:120])
        if trans:
            parts.append("中文释义：" + trans[:700])
        if definition:
            parts.append("英文释义：" + definition[:700])
        try:
            exs = self.engine.examples(word, 2) if self.engine else []
        except Exception:
            exs = []
        if exs:
            lines = []
            for item in exs[:2]:
                if isinstance(item, (list, tuple)):
                    lines.append(" / ".join(str(x) for x in item[:2]))
                else:
                    lines.append(str(item))
            parts.append("例句：" + "\n".join(lines))
        return "\n".join(parts)[:1800]

    def _ai_internal_open(self, prompt, subject, task, note_word=""):
        """打开站内 DeepSeek；没有 Key 时先引导配置。"""
        if not deepseek_configured():
            cfg = DeepSeekSettingsDialog(self)
            if cfg.exec() != QDialog.Accepted or not deepseek_configured():
                self.pron_now.setText("未配置 DeepSeek API Key，仍可选用网页版 AI")
                return

        full_prompt = prompt
        if note_word:
            ctx = self._ai_context(note_word)
            if ctx:
                full_prompt += "\n\n本地词库参考信息（仅作辅助，不可靠时请说明）：\n" + ctx

        dlg = DeepSeekDialog(
            self,
            initial_prompt=full_prompt,
            subject=subject,
            note_word=note_word,
            task_label=task.get("label") or "DeepSeek 助手",
        )
        self._ai_dialog = dlg
        dlg.finished.connect(lambda _r: setattr(self, "_ai_dialog", None))
        dlg.show()
        dlg.raise_()
        dlg.activateWindow()
        self.pron_now.setText("已打开 DeepSeek 站内助手")

    def _save_ai_note(self, word, content):
        """把 AI 回答追写到当前分组里的单词笔记。"""
        w = (word or "").strip()
        text = (content or "").strip()
        if not w or not text:
            return False
        gid = self._cur_wb_group()
        old = self.store.get_note(w, gid)
        stamp = time.strftime("%Y-%m-%d %H:%M")
        entry = f"【DeepSeek {stamp}】\n{text}"
        note = (old + "\n\n" if old else "") + entry
        if len(note) > 20000:
            note = note[-20000:]
        ok = self.store.set_note(w, note, gid)
        if ok:
            self._reload_wb_list()
        return ok

    # ------------------------------------------------------ 官方词典直达
    def _od_open(self, dict_key):
        """在浏览器中打开该词在某部官方词典里的页面。

        这里是「看正规词典原文」的正道：ECDICT 只是免费的中英对照词表，
        不含牛津/朗文/柯林斯的版权正文；跳转官方站拿到的才是原汁原味的内容。
        """
        from urllib.parse import quote

        od = next((o for o in OFFICIAL_DICTS if o["key"] == dict_key), None)
        if od is None:
            return
        w = (self._cur_word or (self.search_edit.text() or "").strip()).strip()
        if not w:
            self.pron_now.setText("请先查一个词")
            return
        # 词形还原过的词用原形去查，否则 went 在牛津官网查不到
        url = od["url"].format(w=quote(w.lower(), safe=""))
        ok = QDesktopServices.openUrl(QUrl(url))
        if ok:
            self.pron_now.setText(f"已打开 {od['label']}：{w}")
        else:
            try:
                QGuiApplication.clipboard().setText(url)
                self.pron_now.setText("未能打开浏览器，网址已复制到剪贴板")
            except Exception:
                self.pron_now.setText("未能打开浏览器")

    # ------------------------------------------------------------ 发音
    # -------------------------------------------------------- 配置状态提示
    def _refresh_cfg_hint(self):
        """在状态栏右侧显示可选能力的启用状态（只读提示，点了给说明）。

        ⚠ 必须保持「极短」。底部这一行同时要塞：发音按钮 ×3、口音下拉、
        收藏按钮、发音状态文字、以及这个提示。用户反馈「下方读音旁边的
        小字看不全」，根因就是这里写了「全球音源 ○  整句翻译 ○」共 54px+，
        把 pron_now 挤到只剩 120px，而「美式发音 · happy · 真人录音」
        需要 246px。现在缩成两个小圆点，具体说明全放 tooltip ——
        信息一点没少，但让出了 50px 给真正重要的状态文字。

        第一项的含义已变：Edge 发音**不需要配置**（国内直连、免费、
        无 key），所以这里显示的是「整句翻译有没有配」。
        """
        try:
            tr_on, _accent = config_status()
            # ✓ = 已启用，○ = 未配置（回退）。两个字符 + 分隔，约 20px。
            self.cfg_hint.setText(
                "音✓ " + ("译✓" if tr_on else "译○")
            )
            self.cfg_hint.setToolTip(self._cfg_tooltip(tr_on))
        except Exception:
            self.cfg_hint.setText("")

    def _cfg_tooltip(self, tr_on):
        loc = CONFIG_PATH or os.path.join(app_dir(), CONFIG_FILE)
        _tr, accent = config_status()
        lines = ["可选能力配置（点这里看说明）",
                 f"配置文件：{loc}",
                 f"Edge 神经语音：已启用（免费，无需配置），当前 {accent}",
                 f"有道整句翻译：{'已启用' if tr_on else '未配置，仅词典式兜底'}",
                 "DeepSeek 站内助手：" +
                 ("已配置" if deepseek_configured() else "未配置，可选")] 
        if CONFIG.get("proxy"):
            lines.append(f"代理：{CONFIG['proxy']}")
        return "\n".join(lines)

    def _on_cfg_hint(self, _ev):
        """点状态提示：把配置说明和模板落到 exe 同目录，方便用户直接填。"""
        tr_on, accent = config_status()
        p = CONFIG_PATH or write_config_template()
        tip = (f"配置文件位置：\n{p}\n\n"
               f"Edge 神经语音：已启用（免费、无需 key），当前 {accent}\n"
               f"　　（口音在底部下拉框里直接换，会自动记住）\n"
               f"有道整句翻译：{'已启用' if tr_on else '未配置（填 youdao_app_key / youdao_app_secret）'}\n"
               f"DeepSeek 站内助手：{'已配置' if deepseek_configured() else '未配置（在 AI 下拉框选「DeepSeek 站内」，点 AI 按钮即可设置）'}\n"
               f"代理：{CONFIG.get('proxy') or '未配置（填 proxy，形如 http://127.0.0.1:7890）'}\n\n"
               "填好后重启软件即可生效，无需重新打包。\n\n"
               "注：Forvo 全球发音已于 2026-09-17 移除 —— 该站国内无法访问，"
               "且其发音接口早已停止服务。现已改用 Edge 神经语音替代。")
        QMessageBox.information(self, "配置说明", tip)

    def _speak(self, accent):
        """三种发音模式：美式 / 英式 / 口音。

        美式/英式走有道真人录音；口音走 Edge 神经语音（可选十几种口音）。
        全部在线优先，断网才回退本地系统语音。
        状态栏会标明这次实际用的是哪种音源，用户一眼就能看出是否断网。
        """
        w = self._cur_word
        if not w:
            self.pron_now.setText("请先查一个词")
            return
        names = {"us": "美式", "uk": "英式", "edge": "口音", "global": "口音"}
        accent = "edge" if accent == "global" else accent   # 兼容旧调用
        # Edge 合成要 1~2 秒，先把「正在获取」摆出来，否则用户会以为没反应
        self.pron_now.setText(f"{names[accent]}发音 · 正在获取…")
        QApplication.processEvents()
        ok = self.pron.speak(
            w, accent, self.lang,
            phonetic_uk=self._cur_ph_uk,
            phonetic_us=self._cur_ph_us,
        )
        if ok:
            src = getattr(self.pron, "_last_source", "") or ""
            tail = f" · {src}" if src else ""
            self.pron_now.setText(f"{names[accent]}发音 · {w}{tail}")
        else:
            self.pron_now.setText("发音不可用（无网络且本机无语音）")

    # ------------------------------------------------------------ 渲染
    def _render(self, word, record=True):
        if not self.engine:
            return
        d = self.engine.lookup(word, self._dict_key())
        if not d:
            self._show_notfound(word)
            return

        new_word = d.get("word", word)
        # 导航栈：记录「上一个词」，供「返回」按钮退回
        if record and self._cur_word and self._cur_word != new_word:
            prev = self._cur_word
            # 撤销用的导航快照必须在 append **之前**取：撤销这次跳转后
            # 应回到「跳转前」的历史状态，这样再点「返回」才会退到更早的词，
            # 而不是原地打转。
            nav_snap = list(self._nav_stack)
            self._nav_stack.append(prev)
            # 跳转也进撤销栈 —— 用户反馈「为啥不能撤销跳转操作」：
            #   旧版撤销栈里只有破坏性数据操作（清空历史/删词），
            #   点释义里的蓝色词或短语跳走之后，「↩ 撤销」是灰的、
            #   Ctrl+Z 按了没反应，看起来像功能没做。
            self._push_undo("跳转回「%s」" % prev,
                            self._make_word_undo(prev, nav_snap))
        self._cur_word = new_word
        # 搜索历史：仅记录用户主动查的词（自动选中不记，避免中间态污染）
        if record:
            self.store.add_history(new_word)

        self._cur_ph_uk = d.get("phonetic") or ""
        self._cur_ph_us = d.get("phonetic_us") or ""
        self.pron_now.setText("")
        W = d.get("word", "")
        ph_uk = d.get("phonetic") or ""
        ph_us = d.get("phonetic_us") or ""
        tag = d.get("tag") or ""
        collins = d.get("collins") or 0
        oxford = d.get("oxford") or 0

        html = []
        html.append("<div style='font-family:Georgia,serif;'>")

        # ---- 词头 + 收藏 / 返回 ----
        # 收藏做成「胶囊按钮」而不是 12px 小字链接。
        # 用户反馈「收藏按钮在哪」—— 旧版把 12px 的「☆ 收藏」直接跟在
        # 29px 的单词后面，字号差 2.4 倍、又没有边框，视觉上完全被吞掉。
        # 这里给文字链接套一层带底色和圆角的 box，让它一眼就像个按钮。
        faved = self.store.has_word(W, self._cur_wb_group())
        star = "★ 已收藏" if faved else "☆ 收藏"
        star_bg = "#F6E7D8" if faved else "#FFF6E8"
        star_fg = SEAL if faved else "#B8860B"
        # 「↩ 返回」也做成胶囊按钮（原来是与收藏并列的 12px 淡灰小字）。
        # 用户反馈「看不到操作撤销的按钮」—— 收藏按钮之前因为同样的原因
        # 被投诉过一次并且改成了胶囊，返回按钮却被漏下了。
        # 有历史可退时才显示（没得退的按钮只会让人困惑）。
        back_html = ""
        if self._nav_stack:
            back_html = (
                f"&nbsp;<a href='nav:back' style='font-size:13px;"
                f"font-weight:600;color:{INK_SOFT};text-decoration:none;"
                f"background:{PAPER_ALT};border:1px solid {LINE};"
                f"border-radius:11px;padding:2px 10px;'>↩ 返回</a>")
        html.append(
            f"<div style='font-size:29px;font-weight:700;color:{INK};"
            f"letter-spacing:0.5px;'>{self._esc(W)}"
            f"&nbsp;&nbsp;<a href='wb:toggle' style='font-size:13px;"
            f"font-weight:600;color:{star_fg};text-decoration:none;"
            f"background:{star_bg};border:1px solid {star_fg};"
            f"border-radius:11px;padding:2px 10px;'>{star}</a>"
            f"{back_html}"
            f"</div>"
        )

        # ---- 音标：英语显示英美并列，其它语言只显示单音标 ----
        if ph_uk or ph_us:
            html.append("<div style='margin-top:7px;font-size:12.5px;color:%s;'>" % INK_SOFT)
            if self.lang == "en":
                if ph_us:
                    html.append(
                        f"<span style='color:{SEAL};font-weight:600;'>美</span> "
                        f"<span style='font-family:Georgia,serif;'>/{self._esc(ph_us)}/</span>"
                    )
                if ph_uk:
                    if ph_us:
                        html.append("<span style='color:%s;'>　</span>" % LINE)
                    html.append(
                        f"<span style='color:{BLUE};font-weight:600;'>英</span> "
                        f"<span style='font-family:Georgia,serif;'>/{self._esc(ph_uk)}/</span>"
                    )
            else:
                lab = LANG_DEFS.get(self.lang, {}).get("label", "")
                html.append(
                    f"<span style='color:{SEAL};font-weight:600;'>{lab}</span> "
                    f"<span style='font-family:Georgia,serif;'>/{self._esc(ph_uk)}/</span>"
                )
            html.append("</div>")

        # ---- 标签行（以彩色胶囊呈现，HTML 内联样式实现）----
        chips = []
        for k in ["zk", "gk", "cet4", "cet6", "ky", "toefl", "ielts", "gre"]:
            if k in tag.split():
                bg, fg = TagChip.COLORS.get(k, ("#f2f2f4", "#5c6272"))
                chips.append(
                    f"<span style='background:{bg};color:{fg};"
                    f"padding:2px 9px;border-radius:9px;font-size:11px;"
                    f"font-weight:600;'>{TagChip.NAMES[k]}</span>"
                )
        if oxford:
            bg, fg = TagChip.COLORS["oxford"]
            chips.append(
                f"<span style='background:{bg};color:{fg};"
                f"padding:2px 9px;border-radius:9px;font-size:11px;"
                f"font-weight:600;'>牛津3000</span>"
            )
        if chips or collins:
            html.append("<div style='margin-top:9px;'>")
            html.append("&nbsp;".join(chips))
            if collins:
                if chips:
                    html.append("&nbsp;&nbsp;")
                html.append(
                    f"<span style='color:{GOLD};font-size:12px;'>"
                    f"{'★' * int(collins)}</span>"
                    f"<span style='color:{INK_FAINT};font-size:11px;'> 柯林斯</span>"
                )
            html.append("</div>")

        # ---- 词形还原提示 ----
        if d.get("_from"):
            html.append(
                f"<div style='margin-top:8px;padding:6px 10px;background:{PAPER_ALT};"
                f"border-radius:6px;font-size:11.5px;color:{INK_SOFT};'>"
                f"变形还原：<b>{self._esc(word)}</b> → <b style='color:{SEAL};'>"
                f"{self._esc(W)}</b></div>"
            )

        # ---- 原形提示（变形词本身有独立词条、没有跳走时）----
        # 用户反馈（2026-10-08）：搜 chipped 想看「有缺口的」这个独立义项，
        # 旧版却强制跳到 chip。现在展示它自己的词条，同时留一扇去原形的门。
        if d.get("_lemma"):
            html.append(
                f"<div style='margin-top:8px;padding:6px 10px;background:{PAPER_ALT};"
                f"border-radius:6px;font-size:11.5px;color:{INK_SOFT};'>"
                f"<b>{self._esc(W)}</b> 本身可作单词使用；它也是 "
                f"<a href='word:{self._esc(d['_lemma'])}' "
                f"style='color:{SEAL};text-decoration:none;'>"
                f"<b>{self._esc(d['_lemma'])}</b></a> 的变形，点这里查看原形</div>"
            )

        # ---- 词表提示 ----
        if d.get("_note"):
            html.append(
                f"<div style='margin-top:8px;padding:6px 10px;background:#fff8e8;"
                f"border-radius:6px;font-size:11.5px;color:#9a6b00;'>{d['_note']}</div>"
            )

        html.append("<div style='height:14px;'></div>")

        # ---- 中文释义 ----
        zh = (d.get("translation") or "").replace("\\n", "\n").strip()
        if zh:
            html.append(self._section("中文释义"))
            for line in zh.split("\n"):
                line = line.strip()
                if not line:
                    continue
                html.append(
                    f"<div style='margin:4px 0;font-size:15px;color:{INK};"
                    f"line-height:185%;'>{self._linkify(line)}</div>"
                )
        elif self.lang != "en" and W:
            # 非英语词库**没有中文释义字段** —— 实测 dict_ja/fr/yue 的
            # translation 字段 0 条非空（221353/245728/56190 全是空串），
            # 所以用户查日语词只看得到词形 + 音标，像本没解释的读音表。
            # 这里用在线机翻补一行，并**明确标注「机翻参考」**：
            # 实测粤语很准、日语多数可用、法语偏差（manger→「22，」），
            # 标了才不会让人以为那是词典原文。
            key = (self.lang, W)
            mt = self._mt_cache.get(key)
            html.append(self._section("中文意思"))
            if mt is None:
                html.append(
                    f"<div style='margin:4px 0;font-size:12.5px;"
                    f"color:{INK_FAINT};'>正在联网取中文意思…</div>")
                if record:
                    # 只在用户**主动查看**时联网；打字时的候选预览不触发，
                    # 否则每预览一个候选词就发一次请求（用户投诉过卡顿）
                    self._schedule_mt_zh(W)
            elif mt[0]:
                html.append(
                    f"<div style='margin:4px 0;font-size:15px;color:{INK};"
                    f"line-height:185%;'>{self._linkify(mt[0])}</div>"
                    f"<div style='margin-top:5px;font-size:11px;"
                    f"color:{INK_FAINT};'>机翻参考（{self._esc(mt[1])}），"
                    f"未必准确，仅供理解方向</div>")
            else:
                html.append(
                    f"<div style='margin:4px 0;font-size:12.5px;"
                    f"color:{INK_FAINT};'>未取到中文意思（网络不通，"
                    f"或该词机翻无结果）</div>")

        # ---- 英文释义 ----
        en = (d.get("definition") or "").replace("\\n", "\n").strip()
        if en:
            html.append(self._section("英文释义"))
            for line in en.split("\n"):
                line = line.strip()
                if not line:
                    continue
                html.append(
                    f"<div style='margin:4px 0;font-size:13px;color:{INK_SOFT};"
                    f"line-height:185%;font-family:Georgia,serif;'>{self._esc(line)}</div>"
                )

        # ---- 联网增强：英英释义 / 柯林斯 / 同义词（有道 jsonapi）----
        onl = self._online_cache.get(W) if self.lang == "en" else None
        if onl:
            if onl.get("english"):
                html.append(self._section("英英释义（联网）"))
                for pos, text in onl["english"][:4]:
                    lab = f"<span style='color:{SEAL};font-weight:600;'>{pos}</span> " if pos else ""
                    html.append(
                        f"<div style='margin:4px 0;font-size:13px;color:{INK};"
                        f"line-height:175%;font-family:Georgia,serif;'>{lab}"
                        f"{self._esc(text)}</div>"
                    )
            if onl.get("collins"):
                html.append(self._section("柯林斯释义（联网）"))
                for pos, tran in onl["collins"][:3]:
                    lab = f"<span style='color:{SEAL};font-weight:600;'>{pos}</span> " if pos else ""
                    html.append(
                        f"<div style='margin:4px 0;font-size:13px;color:{INK_SOFT};"
                        f"line-height:175%;font-family:Georgia,serif;'>{lab}"
                        f"{self._esc(tran)}</div>"
                    )
            if onl.get("synos"):
                html.append(self._section("同义词（联网）"))
                for pos, ws in onl["synos"][:4]:
                    lab = f"<span style='color:{INK_FAINT};'>{pos}</span> " if pos else ""
                    words = " · ".join(
                        f"<a href='word:{self._esc(w)}' style='color:{BLUE};"
                        f"text-decoration:none;'>{self._esc(w)}</a>" for w in ws)
                    html.append(
                        f"<div style='margin:4px 0;font-size:13px;color:{INK};"
                        f"line-height:185%;'>{lab}{words}</div>"
                    )

        # ---- 常用短语（词库自带固定搭配，非生成） ----
        # 用户要求：「常用短语直接放在单词的内容里」。
        # 数据来自 ECDICT 自身的多词词条，筛出「动词+小品词」型固定搭配。
        # 放在释义之后、例句之前 —— 短语属于词汇知识，比例句更优先。
        phs = self.engine.phrases(W, limit=8)
        if phs:
            html.append(self._section("常用短语"))
            html.append(
                f"<div style='font-size:11px;color:{INK_FAINT};margin:-2px 0 8px 0;'>"
                f"{PHRASE_SOURCE_NOTE}</div>"
            )
            for ph, tr in phs:
                # 短语本身可点击 —— 点一下就直接查该短语的完整词条
                safe_ph = self._esc(ph)
                html.append(
                    "<table width='100%' cellspacing='0' cellpadding='0' "
                    "style='margin:0 0 6px 0;'><tr>"
                    f"<td valign='top' style='width:11px;color:{SEAL};"
                    f"font-size:13px;'>\u00b7</td><td>"
                    f"<a href='phrase:{safe_ph}' style='text-decoration:none;"
                    f"color:{BLUE};font-size:13.5px;font-family:Georgia,serif;"
                    f"font-weight:600;'>{safe_ph}</a>"
                    f"<span style='font-size:12.5px;color:{INK_SOFT};"
                    f"margin-left:8px;'>{self._esc(tr)}</span>"
                    "</td></tr></table>"
                )

        # ---- 例句（真实语料，非生成） ----
        # 这是用户明确要的「真实词典例句」：句子来自 Tatoeba 语料库的
        # 中英对照句对，全部是可查证的真实用法，不是 AI 编的。
        exs = self.engine.examples(W, limit=6)
        if exs:
            html.append(self._section("例句"))
            html.append(
                f"<div style='font-size:11px;color:{INK_FAINT};margin:-2px 0 8px 0;'>"
                f"来自 Tatoeba 语料库的真实中英对照句</div>"
            )
            for en_s, zh_s in exs:
                html.append(
                    "<table width='100%' cellspacing='0' cellpadding='0' "
                    "style='margin:0 0 10px 0;'><tr>"
                    f"<td valign='top' style='width:11px;color:{SEAL};"
                    f"font-size:14px;'>·</td><td>"
                    f"<div style='font-size:13.5px;color:{INK};line-height:170%;"
                    f"font-family:Georgia,serif;'>{self._linkify(en_s)}</div>"
                    f"<div style='font-size:12.5px;color:{INK_SOFT};"
                    f"line-height:170%;margin-top:2px;'>{self._esc(zh_s)}</div>"
                    "</td></tr></table>"
                )

        # ---- 变形 ----
        ex = (d.get("exchange") or "").strip()
        if ex:
            M = {"p": "过去式", "d": "过去分词", "i": "现在分词",
                 "3": "第三人称单数", "r": "比较级", "t": "最高级", "s": "复数"}
            items = []
            for part in ex.split("/"):
                if ":" not in part:
                    continue
                k, v = part.split(":", 1)
                if k in M and v:
                    items.append((M[k], v))
            if items:
                html.append(self._section("词形变化"))
                row = []
                for k, v in items[:8]:
                    row.append(
                        f"<span style='color:{INK_FAINT};'>{k}</span> "
                        f"<a href='word:{self._esc(v)}' style='color:{BLUE};"
                        f"text-decoration:none;'>{self._esc(v)}</a>"
                    )
                html.append(
                    f"<div style='font-size:12.5px;color:{INK};line-height:200%;'>"
                    + "　·　".join(row) + "</div>"
                )

        html.append("</div>")
        self.detail.setHtml("".join(html))
        self.detail.verticalScrollBar().setValue(0)
        self._sync_fav_btn()
        # 联网增强：首次查词异步抓有道 jsonapi，拿到后重渲染（命中缓存则直接展示）
        if self.lang == "en" and W and W not in self._online_cache:
            self._schedule_online_enhance(W)

    def _schedule_online_enhance(self, word):
        """联网获取英英释义/柯林斯/同义词；成功则重渲染当前词条。

        ⚠ 必须走真线程（2026-09-17）：原先用 `QTimer.singleShot(40, ...)`，
        那只是把回调**推迟到下一个事件循环**，请求仍然跑在 UI 主线程上，
        实测冻界面 ~417~513ms（超时上限 3s）。
        而 `_render` 每次渲染词条都会排一次本函数 —— 打字时每预览一个
        候选词就冻半秒，这是「单词打得很慢」的第三个来源。
        """
        if word in self._online_fetching:
            return
        self._online_fetching.add(word)
        run_async(lambda: fetch_online_def(word),
                  lambda data: self._on_online_ready(word, data))

    def _on_online_ready(self, word, data):
        """联网结果回到主线程后的收尾（可安全碰 GUI / 缓存）。"""
        try:
            if data and (data.get("english") or data.get("collins")
                         or data.get("synos")):
                self._online_cache[word] = data
        finally:
            self._online_fetching.discard(word)
        # 用户仍停留在这个词才重渲染；否则丢弃
        if self._cur_word == word and word in self._online_cache:
            self._render(word, record=False)

    def _schedule_mt_zh(self, word):
        """非英语词条的「中文意思」：异步机翻并缓存。

        ⚠ 只由 _render 在 record=True（用户主动查/点选）时调用。
          打字过程中的候选预览也走 _render，但那时 record=False，
          不触发 —— 否则每预览一个候选词就发一次网络请求。
        """
        lang = self.lang
        key = (lang, word)
        if key in self._mt_cache or key in self._mt_fetching:
            return
        self._mt_fetching.add(key)

        def on_done(res):
            self._mt_fetching.discard(key)
            r, src = res if res else (None, None)
            # 失败也写缓存（空串）：不然每次重渲染都会再打一次网络
            self._mt_cache[key] = (r or "", src or "")
            # 用户可能已经切走 —— 只在仍是同一个词、同一个语言时刷新
            if self._cur_word == word and self.lang == lang:
                self._render(word, record=False)

        # allow_same=True：日语汉字词与中文同形（「水」→「水」）是常态，
        # 同形恰恰说明意思一致，不能像翻译对话框那样把它当「没翻」丢掉
        run_async(lambda: _mymemory_raw(word, "%s|%s" % (lang, ZH_MM),
                                        allow_same=True), on_done)

    def _section(self, title):
        return (
            f"<div style='margin:18px 0 8px 0;padding-left:9px;"
            f"border-left:3px solid {SEAL};font-size:12px;font-weight:700;"
            f"color:{INK_SOFT};letter-spacing:2px;'>{title}</div>"
        )

    def _linkify(self, line):
        """把释义里出现的英文单词变成可点击跳转的链接。"""
        def rep(m):
            w = m.group(0)
            if len(w) < 2:
                return w
            return f"<a href='word:{w}' style='color:{BLUE};text-decoration:none;'>{w}</a>"
        return re.sub(r"[A-Za-z][A-Za-z\-']{1,}", rep, self._esc(line))

    @staticmethod
    def _esc(s):
        return (
            str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        )

    # ------------------------------------------------------------ 空状态
    def _show_welcome(self):
        s = self._stats or {}
        total = f"{s.get('total', 0):,}"
        html = f"""
        <div style='font-family:Georgia,serif;'>
          <div style='font-size:23px;color:{INK};font-weight:700;'>
            开始查词
          </div>
          <div style='margin-top:8px;font-size:13px;color:{INK_SOFT};line-height:190%;'>
            在搜索框输入单词即可即时查询，共收录
            <b style='color:{SEAL};'>{total}</b> 条词条。<br>
            支持动词时态、名词复数等变形自动还原，例如
            <span style='font-family:Georgia,serif;color:{SEAL};'>went</span>、
            <span style='font-family:Georgia,serif;color:{SEAL};'>apples</span>。
          </div>
        """
        html += self._section("操作速查")
        keys = [
            ("↑ / ↓", "切换候选词"),
            ("回车", "查看当前词条"),
            ("Esc", "清空搜索框"),
            ("Ctrl+Tab", "切换词典"),
            ("美 / 英 / 全球", "在线真人录音 · 需联网"),
            ("词典原文", "跳转牛津/剑桥等官方词典"),
            ("常用短语", "点短语直接查该短语"),
            ("AI 按钮", "跳转浏览器深度讲解"),
        ]
        for k, v in keys:
            html += (
                f"<div style='margin:4px 0;font-size:12.5px;color:{INK_SOFT};'>"
                f"<span style='display:inline-block;min-width:104px;"
                f"font-family:Georgia,serif;color:{INK};font-weight:600;'>{k}</span>"
                f"{v}</div>"
            )
        html += "</div>"
        self.detail.setHtml(html)

    def _show_notfound(self, t):
        hint = ""
        if self.engine and self.engine.con:
            base = re.sub(r"(ies|es|s|ed|ing|er|est)$", "", t.lower())
            if base and base != t.lower():
                hint = (
                    f"<div style='margin-top:10px;font-size:12.5px;color:{INK_SOFT};'>"
                    f"是否想查 <a href='word:{self._esc(base)}' "
                    f"style='color:{BLUE};text-decoration:none;'>{self._esc(base)}</a>？</div>"
                )
        self.detail.setHtml(f"""
        <div style='font-family:Georgia,serif;'>
          <div style='font-size:22px;color:{INK_FAINT};'>未找到
            <b style='color:{INK};'>{self._esc(t)}</b></div>
          <div style='margin-top:8px;font-size:12.5px;color:{INK_SOFT};line-height:190%;'>
            当前词典中没有该词条。<br>
            可以试试：切换「全部」词典、确认拼写、或输入动词原形。
          </div>
          {hint}
        </div>
        """)

    def _show_empty_cn(self, t):
        self.detail.setHtml(f"""
        <div style='font-family:Georgia,serif;'>
          <div style='font-size:22px;color:{INK_FAINT};'>没有匹配
            <b style='color:{INK};'>{self._esc(t)}</b> 的英文词</div>
          <div style='margin-top:8px;font-size:12.5px;color:{INK_SOFT};'>
            换一个更常见的中文词试试，例如「放弃」「美丽」「环境」。
          </div>
        </div>
        """)

    def _show_missing_lang(self):
        lab = LANG_DEFS[self.lang]["label"]
        db = LANG_DEFS[self.lang]["db"]
        self.detail.setHtml(f"""
        <div style='font-family:Georgia,serif;'>
          <div style='font-size:22px;color:{INK_FAINT};'>{lab}词库未安装</div>
          <div style='margin-top:8px;font-size:12.5px;color:{INK_SOFT};line-height:190%;'>
            需要把词库文件 <b style='font-family:Consolas,monospace;color:{SEAL};'>{db}</b>
            放到程序同目录下。<br>英语词库已内置，可直接切换回「英语」使用。
          </div>
        </div>
        """)

    # ------------------------------------------------------------ 统计
    def _update_tip(self):
        """侧栏小贴士随语言变化。"""
        if not hasattr(self, "tip"):
            return
        if self.lang == "en":
            self.tip.setText(
                "小贴士\n"
                "· 输入 went / apples 会自动\n"
                "  还原到原形\n"
                "· 点击释义中的蓝色词语\n"
                "  可直接跳转（Ctrl+Z 可撤销）\n"
                "· 美 / 英 发音为真人录音\n"
                "  （首次需联网，之后走缓存）\n"
                "· 「中 → 英」可反查英文词"
            )
        else:
            lab = LANG_DEFS.get(self.lang, {}).get("label", "")
            self.tip.setText(
                "小贴士\n"
                f"· 输入中文可反查{lab}词\n"
                "  （联网机翻后检索，约 1~2 秒）\n"
                "· 词条里的中文意思是机翻参考\n"
                "· 也可输入罗马字 / 拼音\n"
                "  （如 nihon、nei）\n"
                f"· 点「翻译」可中文 ⇄ {lab} 互译"
            )

    # ------------------------------------------------- 小贴士折叠（记住选择）
    def _tip_saved_collapsed(self):
        """读「小贴士是否已收起」这个偏好。

        存的是字符串 "1"/"0" —— load_config 只接受字符串值
        （它会把非字符串的键丢掉），所以这里不能用 bool。
        """
        return str(CONFIG.get("tip_collapsed") or "").strip() == "1"

    def _apply_tip_collapsed(self, collapsed):
        if not hasattr(self, "tip"):
            return
        self._tip_collapsed = bool(collapsed)
        self.tip.setVisible(not self._tip_collapsed)
        self.tip_title.setText("小贴士（已收起）" if self._tip_collapsed
                               else "小贴士")
        self.tip_toggle.setText("展开 ▸" if self._tip_collapsed else "收起 ▾")
        self.tip_toggle.setToolTip(
            "展开小贴士" if self._tip_collapsed
            else "把小贴士收起来，腾出侧栏空间")

    def _toggle_tip(self):
        """收起 / 展开小贴士，并把选择立刻落盘（下次打开保持）。"""
        self._apply_tip_collapsed(not getattr(self, "_tip_collapsed", False))
        self._save_config("tip_collapsed",
                          "1" if self._tip_collapsed else "0")

    def _save_config_items(self, values):
        """把若干配置写进 dict_config.json，同时保留用户自己的说明键。

        先读回原文件再只改这一项 —— 用户可能自己加过注释键
        （模板里就有 `_说明` 这类），整体覆盖会把它们抹掉。
        """
        vals = {k: str(v) for k, v in (values or {}).items()}
        p = CONFIG_PATH or os.path.join(app_dir(), CONFIG_FILE)
        try:
            data = {}
            if os.path.exists(p):
                with open(p, "r", encoding="utf-8") as f:
                    old = json.load(f)
                if isinstance(old, dict):
                    data = old
            data.update(vals)
            with open(p, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            CONFIG.update(vals)
            return True
        except Exception:
            return False

    def _save_config(self, key, value):
        """把一项偏好写进 dict_config.json。"""
        self._save_config_items({key: value})

    def _load_stats(self):
        self._stats = self.engine.stats() if self.engine else {}
        self.stat_widget.set_data(self._stats)
        if not self.result_list.count() and not self.search_edit.text().strip():
            self._show_welcome()

    # ------------------------------------------------------------ 快捷键
    def keyPressEvent(self, e):
        k = e.key()
        # Ctrl+Z = 撤销最近一次破坏性操作（清空历史 / 清空单词本 / 移出…）。
        # 与「返回上一词」分开：那个是 Alt+←，语义是「翻回刚查的词」，
        # 与「撤销我刚才的删除」不是一回事，混在一个快捷键上会互相踩。
        if k == Qt.Key_Z and (e.modifiers() & Qt.ControlModifier):
            self._do_undo()
            return
        if k == Qt.Key_Left and (e.modifiers() & Qt.AltModifier):
            self._nav_back()
            return
        if k == Qt.Key_Escape:
            cur = self.search_edit.text()
            if cur.strip():
                # 有内容 → 备份并清空；再按 Esc 可恢复（防误清空）
                self._last_input = cur
                self.search_edit.clear()
                self.pron_now.setText("已清空 · 再按 Esc 恢复上次内容")
            elif self._last_input:
                self.search_edit.setText(self._last_input)
                self._last_input = ""
                self.pron_now.setText("已恢复上次输入")
            else:
                self.search_edit.clear()
            self.search_edit.setFocus()
            return
        if k == Qt.Key_Down:
            r = self.result_list.currentRow()
            if r + 1 < self.result_list.count():
                self.result_list.setCurrentRow(r + 1)
            return
        if k == Qt.Key_Up:
            r = self.result_list.currentRow()
            if r > 0:
                self.result_list.setCurrentRow(r - 1)
            return
        if k == Qt.Key_Tab and (e.modifiers() & Qt.ControlModifier):
            self.cur_dict_idx = (self.cur_dict_idx + 1) % len(DICTS)
            self._refresh_dict_buttons()
            t = self.search_edit.text()
            if t.strip():
                self._query_timer.stop()
                self._on_text_now(t)
            return
        super().keyPressEvent(e)


class StatsPanel(QWidget):
    """侧栏词库分布图 —— 简洁艺术风格的横向条形图。"""

    ROWS = [
        ("gk", "高考", SEAL),
        ("zk", "中考", "#1f7a4d"),
        ("cet4", "四级", BLUE),
        ("cet6", "六级", "#4a7ff0"),
        ("ky", "考研", "#7a3fb3"),
        ("toefl", "托福", GOLD),
        ("ielts", "雅思", "#c9a227"),
        ("gre", "GRE", INK_FAINT),
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.data = {}
        # 布局：8 行标签(22px) + 间隔 + 分隔线 + 2 行汇总(17px)
        self._h = 8 * 22 + 8 + 1 + 2 * 17 + 6
        self.setFixedHeight(self._h)

    def set_data(self, d):
        self.data = d or {}
        self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w = self.width()
        y = 2

        # 非英语词库没有考试标签，改为展示单条总量信息
        tagged = sum(self.data.get(k, 0) for k, _, _ in self.ROWS)
        if tagged == 0:
            self._paint_plain(p, w)
            p.end()
            return

        mx = max([self.data.get(k, 0) for k, _, _ in self.ROWS] + [1])
        # 标签占左侧 40px；数据条紧随其后；数字右对齐到面板右缘，
        # 避免「牛津核心词」这类 4 字标签与数字互相压字。
        bar_x = 40
        num_w = 46
        bar_w = max(24, w - bar_x - num_w - 6)
        num_right = w

        f_lab = QFont("Microsoft YaHei", 8)
        f_num = QFont("Georgia", 8, QFont.Bold)

        for key, label, color in self.ROWS:
            v = self.data.get(key, 0)
            p.setFont(f_lab)
            p.setPen(QColor(INK_SOFT))
            p.drawText(0, y + 10, label)

            # 轨道
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(PAPER_ALT))
            p.drawRoundedRect(bar_x, y + 2, bar_w, 9, 4.5, 4.5)

            # 数据条
            frac = (v / mx) if mx else 0
            p.setBrush(QColor(color))
            p.drawRoundedRect(bar_x, y + 2, max(3, int(bar_w * frac)), 9, 4.5, 4.5)

            p.setFont(f_num)
            p.setPen(QColor(INK))
            self._draw_right(p, num_right, y + 11, f"{v:,}")

            y += 22

        # 底部汇总
        y += 8
        p.setPen(QColor(LINE))
        p.drawLine(0, y, w, y)
        y += 17
        p.setFont(QFont("Microsoft YaHei", 8))
        p.setPen(QColor(INK_FAINT))
        p.drawText(0, y, "牛津核心词")
        p.setFont(QFont("Georgia", 8, QFont.Bold))
        p.setPen(QColor(INK))
        self._draw_right(p, num_right, y, f"{self.data.get('oxford', 0):,}")
        y += 17
        p.setFont(QFont("Microsoft YaHei", 8))
        p.setPen(QColor(INK_FAINT))
        p.drawText(0, y, "总词条")
        p.setFont(QFont("Georgia", 8, QFont.Bold))
        p.setPen(QColor(SEAL))
        self._draw_right(p, num_right, y, f"{self.data.get('total', 0):,}")
        p.end()

    @staticmethod
    def _draw_right(p, right_x, baseline_y, text):
        """把文本右对齐到 right_x 处。"""
        fm = p.fontMetrics()
        tw = fm.horizontalAdvance(text)
        p.drawText(int(right_x - tw), baseline_y, text)

    def _paint_plain(self, p, w):
        """非英语词库：没有考纲标签，展示总量与计量条。"""
        total = self.data.get("total", 0)
        p.setFont(QFont("Microsoft YaHei", 9, QFont.Bold))
        p.setPen(QColor(INK))
        p.drawText(0, 16, "收录词条")

        p.setFont(QFont("Georgia", 21, QFont.Bold))
        p.setPen(QColor(SEAL))
        p.drawText(0, 52, f"{total:,}")

        # 装饰用细线
        p.setPen(QColor(LINE))
        p.drawLine(0, 68, w, 68)

        p.setFont(QFont("Microsoft YaHei", 8))
        p.setPen(QColor(INK_SOFT))
        p.drawText(0, 90, "每个词条均含")
        p.drawText(0, 106, "该语言的国际音标")
        p.drawText(0, 122, "（IPA）读音。")

        p.setFont(QFont("Microsoft YaHei", 8))
        p.setPen(QColor(INK_FAINT))
        p.drawText(0, 152, "检索方式")
        p.setFont(QFont("Microsoft YaHei", 8))
        p.setPen(QColor(INK_SOFT))
        p.drawText(0, 170, "· 原文直接输入")
        p.drawText(0, 186, "· 罗马字 / 拼音输入")


def _install_crash_log():
    """把未捕获异常写入日志文件，便于用户反馈问题。"""
    import traceback, datetime

    def hook(exc_type, exc, tb):
        for log in _log_paths(f"{APP_NAME}_错误日志.txt"):
            try:
                with open(log, "a", encoding="utf-8") as f:
                    f.write(f"\n===== {datetime.datetime.now()} =====\n")
                    traceback.print_exception(exc_type, exc, tb, file=f)
                break
            except Exception:
                continue
        sys.__excepthook__(exc_type, exc, tb)

    sys.excepthook = hook


def _log_paths(name):
    """返回可写的日志路径候选：程序同目录优先，其次用户临时目录。"""
    out = []
    try:
        out.append(os.path.join(app_dir(), name))
    except Exception:
        pass
    try:
        out.append(os.path.join(os.environ.get("TEMP", "."), name))
    except Exception:
        pass
    return out


def _boot_log(msg, verbose=False):
    """启动日志。仅在设置 {APP_NAME}_调试 环境变量（或 DICT_DEBUG）时写入，
    正常使用不会产生日志文件，保持目录干净。"""
    if not (os.environ.get(f"{APP_NAME}_调试") or os.environ.get("DICT_DEBUG")):
        if not verbose:
            return
    import datetime
    line = f"{datetime.datetime.now()}  {msg}\n"
    for log in _log_paths(f"{APP_NAME}_启动日志.txt"):
        try:
            with open(log, "a", encoding="utf-8") as f:
                f.write(line)
            break
        except Exception:
            continue


def _selftest_edge(out_path):
    """离线自检：验证 Edge TTS 在当前运行环境（尤其是打包后的 exe）里可用。

    为什么要做成程序自带的能力：打包会悄悄破坏很多东西（CA 证书路径、
    标准库模块裁剪、ssl 后端），**源码里跑得通不代表 exe 里跑得通**。
    本项目就吃过一次亏 —— spec 里把 QtMultimedia 排除了，导致打包后
    发音静默失效，而且不报任何错。有了这个开关，每次打包后可以一条
    命令确认「网络 + TLS + 口音表 + 校验」整条链路都还在。

    用法：查单词.exe --selftest-edge 结果文件路径
    结果写成一个纯文本报告（UTF-8），退出码 0 = 全部通过。
    """
    lines = []
    ok_all = True

    def add(name, ok, detail=""):
        nonlocal ok_all
        if not ok:
            ok_all = False
        lines.append("%s  %s%s" % ("PASS" if ok else "FAIL", name,
                                   ("  " + str(detail)) if detail else ""))

    lines.append("frozen=%s" % getattr(sys, "frozen", False))
    lines.append("exe=%s" % sys.executable)
    lines.append("app_dir=%s" % app_dir())
    lines.append("config_path=%s" % (CONFIG_PATH or "(无，用内置默认)"))
    lines.append("python=%s" % sys.version.split()[0])
    lines.append("")

    # ① 标准库是否齐（打包最容易缺的就是这些）
    for mod in ("socket", "ssl", "struct", "hashlib", "base64", "uuid"):
        try:
            __import__(mod)
            add("标准库 %s 可用" % mod, True)
        except Exception as e:
            add("标准库 %s 可用" % mod, False, e)

    # ② 令牌算法
    try:
        g = edge_sec_ms_gec(0)
        add("令牌生成（64 位大写 hex）",
            len(g) == 64 and g == g.upper(), g[:16] + "...")
    except Exception as e:
        add("令牌生成", False, e)

    # ③ 口音表
    add("口音表非空", len(EDGE_ACCENTS) >= 10, "%d 种" % len(EDGE_ACCENTS))
    add("默认口音在表内",
        Pronouncer.edge_accent() in {c for c, _ in EDGE_ACCENTS},
        Pronouncer.edge_accent())

    # ④ TLS 证书（ssl.create_default_context 在打包环境里可能找不到 CA）
    try:
        ctx = ssl.create_default_context()
        n = len(ctx.get_ca_certs())
        add("系统 CA 证书可读", n > 0, "%d 张" % n)
    except Exception as e:
        add("系统 CA 证书可读", False, e)

    # ⑤ 真实合成（最关键的一步）
    try:
        t0 = time.time()
        audio = edge_tts_synth("test", "en-US-AvaNeural", timeout=15)
        dt = int((time.time() - t0) * 1000)
        good = edge_audio_ok(audio)
        add("真实合成英文语音", good, "%dms / %d bytes" % (dt, len(audio)))
    except Exception as e:
        add("真实合成英文语音", False, e)

    # ⑥ 缓存写入（验证 exe 有权限写 AppData）
    try:
        pr = Pronouncer()
        p = pr._fetch_edge("selftestword")
        add("合成并写入缓存", bool(p and os.path.exists(p)),
            os.path.basename(p) if p else "")
    except Exception as e:
        add("合成并写入缓存", False, e)

    lines.append("")
    lines.append("RESULT " + ("OK" if ok_all else "FAIL"))
    try:
        with open(out_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
    except Exception:
        pass
    return 0 if ok_all else 1


def _selftest_cn(out_path):
    """自检：验证中文反查的两个关键修复在**打包后**仍然生效。

    ── 为什么要单独做这个（2026-09-17）──
    打包后的字节码被压进 PYZ 归档，用「在 exe 里搜特征字符串」的办法
    根本验不出来（短字符串检索不到，长字符串也可能被优化）。
    源码跑得通 ≠ exe 跑得通 —— 本项目吃过 spec 排除 QtMultimedia
    导致发音静默失效的亏。所以关键修复必须有**功能级**的打包后自检。

    验两条（都是本轮修的真实 bug）：
      1) 后缀变体查询：查「美丽」首条必须是 beautiful
         （旧 bug：出来 fairness，因为 cn_sense 把 beautiful 索引到
           「美丽的」名下，等值查询 sense='美丽' 直接漏掉它）
      2) 末词豁免：查「开心」时 happy 必须排第一
         （旧 bug：happy 被当成短语成分降档，被 rejoice/joyful/chuffed
           这些生僻词压住）

    ⚠ 第 2 条依赖联网（有道 ce 词表）。断网时该条无法结论，
      记录 SKIP 而不是 FAIL —— 不能让网络状况导致自检假失败。
    """
    lines = []

    def say(s=""):
        lines.append(str(s))

    ok = True

    say("frozen=%s" % getattr(sys, "frozen", False))
    say("exe=%s" % sys.executable)
    say("")

    try:
        con = open_db("dict.db")
    except Exception as e:
        say("FAIL  打开词库失败: %r" % (e,))
        say("")
        say("RESULT FAIL")
        try:
            with open(out_path, "w", encoding="utf-8") as f:
                f.write("\n".join(lines) + "\n")
        except Exception:
            pass
        return 1

    if con is None:
        say("FAIL  词库 dict.db 不存在（resource_path 找不到）")
        say("")
        say("RESULT FAIL")
        try:
            with open(out_path, "w", encoding="utf-8") as f:
                f.write("\n".join(lines) + "\n")
        except Exception:
            pass
        return 1

    eng = DictEngine(con, "en")

    # ① 后缀变体：查「美丽」→ beautiful
    try:
        rows = eng.search_cn("美丽")
        got = [r["word"] for r in rows[:3]]
        if got and got[0] == "beautiful":
            say("PASS  查「美丽」首条是 beautiful  %s" % (got,))
        else:
            say("FAIL  查「美丽」首条应为 beautiful，实际 %s" % (got,))
            ok = False
    except Exception as e:
        say("FAIL  查「美丽」抛异常: %r" % (e,))
        ok = False

    # ② 同类：查「漂亮」→ pretty（同一个 bug 的另一面）
    try:
        rows = eng.search_cn("漂亮")
        got = [r["word"] for r in rows[:3]]
        if got and got[0] == "pretty":
            say("PASS  查「漂亮」首条是 pretty  %s" % (got,))
        else:
            say("FAIL  查「漂亮」首条应为 pretty，实际 %s" % (got,))
            ok = False
    except Exception as e:
        say("FAIL  查「漂亮」抛异常: %r" % (e,))
        ok = False

    # ③ 回归：核心词排序不能坏
    for zh, want in (("狗", "dog"), ("水", "water"), ("书", "book"),
                     ("电脑", "computer"), ("学习", "study"),
                     ("环境", "environment"), ("放弃", "abandon")):
        try:
            r = eng.search_cn(zh)
            g = r[0]["word"] if r else None
            if g == want:
                say("PASS  查「%s」首条是 %s" % (zh, want))
            else:
                say("FAIL  查「%s」首条应为 %s，实际 %s" % (zh, want, g))
                ok = False
        except Exception as e:
            say("FAIL  查「%s」抛异常: %r" % (zh, e))
            ok = False

    # ④ 末词豁免：查「开心」→ happy（需联网取同义词）
    try:
        DictEngine.set_cn_extra("开心", [])       # 清掉可能残留的缓存
        eng._cache.clear()
        a = eng.search_cn("开心")
        pre = [r["word"] for r in a[:3]]
        if "happy" in pre:
            say("PASS  查「开心」(纯离线) 已含 happy  %s" % (pre,))
        else:
            # 纯离线查不到是**预期**的（happy 释义里没有「开心」二字），
            # 必须联网补充。这里主动取一次。
            try:
                items = fetch_cn_en("开心")
            except Exception:
                items = []
            if items:
                DictEngine.set_cn_extra("开心", items)
                eng._cache.clear()
                b = eng.search_cn("开心")
                post = [r["word"] for r in b[:3]]
                if post and post[0] == "happy":
                    say("PASS  联网补充后查「开心」首条是 happy  %s  (取回=%s)"
                        % (post, items))
                else:
                    say("FAIL  联网补充后查「开心」首条应为 happy，实际 %s"
                        % (post,))
                    ok = False
            else:
                say("SKIP  查「开心」需联网补充同义词，当前取不到（断网？）")
    except Exception as e:
        say("SKIP  查「开心」自检异常（多为网络原因）: %r" % (e,))

    # ⑤ 无重复渲染：结果列表不应有重复词
    try:
        allw = [r["word"] for r in eng.search_cn("狗")]
        if len(allw) == len(set(allw)):
            say("PASS  反查结果无重复词  (%d 条)" % len(allw))
        else:
            dups = [x for x in set(allw) if allw.count(x) > 1]
            say("FAIL  反查结果出现重复词: %s" % dups)
            ok = False
    except Exception as e:
        say("FAIL  重复性检查抛异常: %r" % (e,))
        ok = False

    try:
        con.close()
    except Exception:
        pass

    say("")
    say("RESULT %s" % ("OK" if ok else "FAIL"))
    try:
        with open(out_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
    except Exception:
        pass
    return 0 if ok else 1


def _selftest_ai(out_path):
    """自检：确认打包后的 DeepSeek 配置、请求解析和笔记接口完整。"""
    import tempfile

    lines = []
    ok_all = True

    def say(msg):
        lines.append(msg)

    def add(name, ok, detail=""):
        nonlocal ok_all
        if not ok:
            ok_all = False
        say("%s  %s%s" % ("PASS" if ok else "FAIL", name,
                           ("  " + str(detail)) if detail else ""))

    say("frozen=%s" % getattr(sys, "frozen", False))
    say("exe=%s" % sys.executable)
    say("")

    for key in ("deepseek_api_key", "deepseek_model",
                "deepseek_base_url", "deepseek_timeout"):
        add("配置模板含 %s" % key, key in CONFIG_TEMPLATE)
    services = {s["key"]: s for s in AI_SERVICES}
    add("包含 DeepSeek 站内服务",
        services.get("deepseek_api", {}).get("internal") == "deepseek")
    add("日语提示词使用日语词语",
        "日语词语" in ai_build_prompt("explain", "日本", lang="ja"))

    class _Resp:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self):
            return json.dumps({
                "choices": [{"message": {"content": "自检回答"}}]
            }, ensure_ascii=False).encode("utf-8")

    old_cfg = dict(CONFIG)
    old_open = _open_url
    captured = {}

    def fake_open(req, timeout):
        captured["url"] = req.full_url
        captured["auth"] = req.get_header("Authorization")
        captured["body"] = json.loads(req.data.decode("utf-8"))
        return _Resp()

    try:
        CONFIG.update({
            "deepseek_api_key": "selftest-key",
            "deepseek_model": "deepseek-chat",
            "deepseek_base_url": "https://api.deepseek.com",
            "deepseek_timeout": "60",
        })
        globals()["_open_url"] = fake_open
        text, err = deepseek_chat([{"role": "user", "content": "test"}])
        add("请求解析正文", text == "自检回答", repr(text))
        add("请求成功无错误", err == "", err)
        add("请求端点正确",
            captured.get("url") == "https://api.deepseek.com/chat/completions",
            captured.get("url"))
        add("请求携带 API Key",
            captured.get("auth") == "Bearer selftest-key", captured.get("auth"))
        add("模型名写入请求",
            captured.get("body", {}).get("model") == "deepseek-chat")
    except Exception as e:
        add("DeepSeek 请求自检", False, repr(e))
    finally:
        globals()["_open_url"] = old_open
        CONFIG.clear()
        CONFIG.update(old_cfg)

    try:
        with tempfile.TemporaryDirectory(prefix="dict_ai_") as td:
            store = UserStore(os.path.join(td, "user.db"))
            add("笔记写入接口", store.set_note("dog", "AI 笔记", 0))
            add("笔记读取接口", store.get_note("dog", 0) == "AI 笔记")
            add("笔记自动加入单词本", store.has_word("dog", 0))
            try:
                store.con.close()
            except Exception:
                pass
    except Exception as e:
        add("笔记接口自检", False, repr(e))

    say("")
    say("RESULT %s" % ("OK" if ok_all else "FAIL"))
    try:
        with open(out_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
    except Exception:
        pass
    return 0 if ok_all else 1


def _selftest_v2(out_path):
    """自检：验证 2026-09-18 的三项改动在**打包后**仍然生效。

    为什么必须有这个（同 _selftest_cn 的理由）：
      打包后字节码压进 PYZ，搜特征字符串验不出来；而本轮新增了
      一个新 import —— `difflib`（`_same_sentence` 闸门用它算相似度）。
      **如果 spec/打包过程漏了它，源码跑得通、exe 一翻译就崩**。
      本自检直接调用闸门函数，是最直接的功能级探测。

    验六条：
      1) difflib 可用 + 闸门能拒绝「包含但更长」的例句
         （这正是「翻译出莫名其妙句子」的根因，必须能被 exe 拒绝）
      2) 闸门对「同一句」（只差标点大小写）放行
      3) 撤销：快照 → 清空 → 还原 后内容逐条一致
      4) 单词本：只清目标分组，别的分组不许动
      5) 翻译链常量齐全（免密钥通道端点）
      6) 真实翻译一次（联网）—— 断网记 SKIP 不记 FAIL

    ⚠ 第 3/4 条用的是**临时库**，绝不碰用户的真实单词本。
    """
    import tempfile
    lines = []

    def say(s=""):
        lines.append(str(s))

    ok = True

    say("frozen=%s" % getattr(sys, "frozen", False))
    say("exe=%s" % sys.executable)
    say("")

    # ① difflib + 闸门能拒绝「例句冒充译文」
    try:
        import difflib as _dl
        say("PASS  difflib 已打进 exe（%s）" % _dl.__name__)
    except Exception as e:
        say("FAIL  difflib 缺失，翻译闸门会崩: %r" % (e,))
        ok = False

    try:
        bad = _same_sentence("Oh, Amy, I love you.", "I love you.")
        if bad is False:
            say("PASS  闸门拒绝「包含但更长」的例句（Oh, Amy, I love you.）")
        else:
            say("FAIL  闸门应拒绝该例句，实际返回 %r" % (bad,))
            ok = False
    except Exception as e:
        say("FAIL  闸门调用抛异常: %r" % (e,))
        ok = False

    # ② 同一句（仅标点/大小写差异）放行
    try:
        if _same_sentence("I love you", "I love you.") is True:
            say("PASS  闸门放行「同一句」（仅标点差异）")
        else:
            say("FAIL  闸门应放行仅标点差异的同一句")
            ok = False
        if _same_sentence("今天天气真好。", "今天天气真好。") is True:
            say("PASS  中文同一句放行")
        else:
            say("FAIL  中文同一句未放行")
            ok = False
    except Exception as e:
        say("FAIL  闸门（中文）抛异常: %r" % (e,))
        ok = False

    # ⑤ 翻译通道常量
    try:
        missing = []
        if "mymemory" not in MYMEMORY_URL:
            missing.append("MYMEMORY_URL")
        if "suggest" not in SUGGEST_URL:
            missing.append("SUGGEST_URL")
        if int(TRANSLATE_TIMEOUT) <= 0:
            missing.append("TRANSLATE_TIMEOUT")
        if missing:
            say("FAIL  翻译通道常量缺失/异常: %s" % missing)
            ok = False
        else:
            say("PASS  翻译通道常量齐全（MyMemory + 有道 suggest）")
    except Exception as e:
        say("FAIL  翻译常量检查异常: %r" % (e,))
        ok = False

    # ③④ 撤销 / 单词本 —— 全程用临时库
    try:
        d = tempfile.mkdtemp(prefix="selfv2_")
        st = UserStore(os.path.join(d, "u.db"))
        st.add_history("alpha")
        st.add_history("beta")
        snap_h = st.snapshot_history()
        st.clear_history()
        n = st.restore_history(snap_h)
        if len(st.history()) == 2 and n == 2:
            say("PASS  撤销：历史快照/还原 round-trip（%d 条）" % n)
        else:
            say("FAIL  历史撤销后应为 2 条，实际 %d" % len(st.history()))
            ok = False

        g1 = st.add_group("自检组")
        st.add_word("apple", 0)
        st.add_word("banana", 0)
        st.add_word("cherry", g1)
        # ⚠ 快照必须在这里取（3 条齐全时）—— 我第一版把 snapshot 放在
        #   clear_words_group 之后，快照里只剩 1 条，于是后面断言「还原后
        #   应有 3 词」必然失败。那不是产品 bug，是自检自己写错了。
        snap_all = st.snapshot_words(None)
        st.clear_words_group(0)
        if st.count_words(0) == 0 and st.count_words(g1) == 1:
            say("PASS  单词本：只清默认分组，另一分组完好")
        else:
            say("FAIL  清分组越界（默认=%d 自检组=%d）"
                % (st.count_words(0), st.count_words(g1)))
            ok = False
        st.clear_words()
        st.restore_words(snap_all, None)
        if st.count_words(None) == 3:
            say("PASS  单词本：整表还原（3 词）")
        else:
            say("FAIL  单词本整表还原后应为 3 词，实际 %d"
                % st.count_words(None))
            ok = False
        # 只还原一个分组：撤销「清空当前分组」时必须不碰别的分组
        st.clear_words()
        st.restore_words(snap_all, 0)
        if st.count_words(0) == 2 and st.count_words(g1) == 0:
            say("PASS  单词本：只还原默认分组，别组不受影响")
        else:
            say("FAIL  单分组还原越界（默认=%d 自检组=%d）"
                % (st.count_words(0), st.count_words(g1)))
            ok = False
    except Exception as e:
        say("FAIL  撤销/单词本自检抛异常: %r" % (e,))
        ok = False

    # ⑦ 多语言（2026-09-18 晚新增的三项也要在 exe 里活着）
    try:
        # 语言对随语言模式变（旧版写死中英）
        s_, d_ = tr_lang_pair("我爱你", "ja")
        if (s_, d_) != (ZH_MM, "ja"):
            say("FAIL  tr_lang_pair(ja) 应为 (zh-CN, ja)，实得 %r"
                % ((s_, d_),))
            ok = False
        else:
            say("PASS  语言对随模式变（中文→日语 = zh-CN|ja）")
        # 「是中文」的判定必须认得日语汉字（学校へ行く 是日语不是中文）
        if _is_zh_text("学校へ行く"):
            say("FAIL  _is_zh_text 把「学校へ行く」当成了中文（假名判定失效）")
            ok = False
        else:
            say("PASS  假名判定：「学校へ行く」识别为日语")
        # 机翻切片要剥掉落单的括号（今晚修的产品瑕疵）
        cands = _tr_candidates("ありがとうございます）。")
        if cands != ["ありがとうございます"]:
            say("FAIL  _tr_candidates 未剥落单括号: %r" % (cands,))
            ok = False
        else:
            say("PASS  机翻切片剥掉落单括号")
    except Exception as e:
        say("FAIL  多语言自检抛异常: %r" % (e,))
        ok = False

    # ⑨ 变形词跳转策略（2026-10-08）：有独立义项的变形词不硬跳原形。
    #    这是 lookup() 查询顺序的改动，必须在 exe 里功能级验证 ——
    #    「源码过 ≠ exe 过」，打包漏收代码时只有这里能兜住。
    try:
        con = open_db("dict.db")
        if con is None:
            say("FAIL  变形策略：dict.db 不在 exe 旁（自检要在部署目录跑）")
            ok = False
        else:
            eng = DictEngine(con)
            d = eng.lookup("chipped", "all")
            if d and (d.get("word") or "").lower() == "chipped" \
                    and d.get("_lemma") == "chip" and not d.get("_from"):
                say("PASS  chipped 展示独立词条（有缺口的），附原形提示")
            else:
                say("FAIL  chipped 应展示自己的词条并带 _lemma=chip，实得 %r"
                    % (d and (d.get("word"), d.get("_from"), d.get("_lemma")),))
                ok = False
            d = eng.lookup("went", "all")
            if d and (d.get("word") or "").lower() == "go" \
                    and d.get("_from") == "go":
                say("PASS  went 仍跳到原形 go（纯变形指针）")
            else:
                say("FAIL  went 应跳到 go，实得 %r"
                    % (d and (d.get("word"), d.get("_from")),))
                ok = False
            con.close()
    except Exception as e:
        say("FAIL  变形策略自检抛异常: %r" % (e,))
        ok = False

    # ⑩ 译文质量闸门（2026-10-08）：法语不能收英语、粤语不能收简繁、
    #     日语无假名的熟词表达要放行。这三条都是纯函数、离线可验。
    try:
        cases = [
            ("英语冒充法语要拒收", _looks_like_target("I Love You", "fr", "我爱你"),
             False),
            ("法语正常译文放行",
             _looks_like_target("Le chat est sur la table", "fr", "猫"), True),
            ("粤语只简繁要拒收", _looks_like_target("點解", "yue", "点解"), False),
            ("日语无假名熟词放行", _looks_like_target("大好き", "ja", "我爱你"),
             True),
            ("英语冒充日语要拒收", _looks_like_target("I love you", "ja", "我爱你"),
             False),
        ]
        for name, got, want in cases:
            if got is want:
                say("PASS  译文闸门：%s" % name)
            else:
                say("FAIL  译文闸门：%s（实得 %r）" % (name, got))
                ok = False
    except Exception as e:
        say("FAIL  译文闸门自检抛异常: %r" % (e,))
        ok = False

    # ⑥ 真实翻译一次（断网 SKIP）
    try:
        tr, src = translate_text("I love you.")
        if tr and ("爱" in tr or "love" in tr.lower()):
            say("PASS  真实翻译可用：%r [%s]" % (tr[:30], src))
        elif tr is None:
            say("SKIP  真实翻译未取到（网络不可用）：%s" % str(src)[:60])
        else:
            say("SKIP  真实翻译结果未识别：%r [%s]" % (tr[:30], src))
    except Exception as e:
        say("FAIL  翻译调用抛异常: %r" % (e,))
        ok = False

    # ⑧ 真实多语言翻译一次（断网 SKIP）—— 验证「其他语言能双向」在 exe 里成立
    try:
        tr, src = translate_text("我爱你", "ja")
        if tr and tr != "我爱你":
            say("PASS  真实多语言翻译可用：我爱你→%r [%s]" % (tr[:30], src))
        elif tr is None:
            say("SKIP  多语言翻译未取到（网络不可用）：%s" % str(src)[:60])
        else:
            say("SKIP  多语言翻译结果未识别：%r" % (tr[:30],))
    except Exception as e:
        say("FAIL  多语言翻译调用抛异常: %r" % (e,))
        ok = False

    say("")
    say("RESULT %s" % ("OK" if ok else "FAIL"))
    try:
        with open(out_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
    except Exception:
        pass
    return 0 if ok else 1


def main():
    # 自检开关：打包后验证 Edge 发音链路是否完整（见 _selftest_edge 说明）。
    # 放在 QApplication 之前 —— 自检不需要 GUI，headless 环境也能跑。
    if len(sys.argv) >= 2 and sys.argv[1] == "--selftest-edge":
        out = sys.argv[2] if len(sys.argv) >= 3 else "selftest_edge.txt"
        sys.exit(_selftest_edge(out))
    # 自检开关：打包后验证中文反查修复是否生效（见 _selftest_cn 说明）。
    if len(sys.argv) >= 2 and sys.argv[1] == "--selftest-cn":
        out = sys.argv[2] if len(sys.argv) >= 3 else "selftest_cn.txt"
        sys.exit(_selftest_cn(out))
    # 自检开关：打包后验证 2026-09-18 的三项改动（翻译/撤销/单词本清空）。
    # 尤其要验 difflib 有没有被打进包 —— 那是本轮新增的 import，
    # 漏了的话「源码跑得通、exe 一翻译就崩」。
    if len(sys.argv) >= 2 and sys.argv[1] == "--selftest-v2":
        out = sys.argv[2] if len(sys.argv) >= 3 else "selftest_v2.txt"
        sys.exit(_selftest_v2(out))
    # 自检开关：验证打包后的 DeepSeek 配置、请求解析和笔记接口。
    if len(sys.argv) >= 2 and sys.argv[1] == "--selftest-ai":
        out = sys.argv[2] if len(sys.argv) >= 3 else "selftest_ai.txt"
        sys.exit(_selftest_ai(out))

    _install_crash_log()
    _boot_log("---- start ----")
    _boot_log(f"frozen={getattr(sys,'frozen',False)} app_dir={app_dir()}")
    # 高 DPI：Qt6 默认已启用缩放，旧版 AA_* 属性在新版已移除，故不再设置
    app = QApplication(sys.argv)
    _boot_log("QApplication OK")
    app.setApplicationName(APP_NAME)
    app.setApplicationDisplayName(APP_NAME)
    try:
        w = MainWindow()
    except Exception:
        _boot_log("MainWindow FAILED:\n" + traceback.format_exc())
        raise
    _boot_log(f"MainWindow OK lang={w.lang} "
              f"engine={'ok' if (w.engine and w.engine.con) else 'none'}")
    w.show()
    _boot_log("show() OK")
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
