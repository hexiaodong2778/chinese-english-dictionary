# -*- coding: utf-8 -*-
"""把本轮（2026-09-18）产生的临时探测/日志文件归档到 _trash_20260918/。

原则（宁可漏收，不可误收）：
  · 只动 **以 `_` 开头** 的文件 —— 项目里正式交付物（app.py / app.spec /
    test_*.py / build_*.py / dict.db ...）都不以 `_` 开头。
  · 只动 **今天修改过** 的 —— mtime 不是今天的一律留下，避免误碰历史资产。
  · 只动 **日志类**（.txt/.png/.log）和显式列出的探测脚本。
    `_deploy_final.py` / `_run_all2.py` / `_tidy_0918.py` 这类**仍在用**的
    工具脚本必须保留（它们也在白名单里，这里靠 keep 名单排除）。
  · **只移动，不删除** —— 全程 shutil.move，随时可以搬回来。
"""
import os
import shutil
import datetime

BUILD = r"D:\Dictionary\build"
TRASH = os.path.join(BUILD, "_trash_20260918")
TODAY = datetime.date(2026, 9, 18)

# 本脚本自己的日志名。
# ★ 为什么不用 shell 重定向：`> _tidy.txt` 会在进程启动前就把文件建好，
#   它满足「_ 开头 + 今天 + .txt」，于是第一版脚本把它**自己搬进了回收站**。
#   经 bash shim 重定向时 sys.stdout.name 也拿不到真实文件名（实测为空），
#   所以改成脚本自己写固定名日志 + 按 `_tidy` 前缀排除。
SELF_LOG = "_tidy_log.txt"

# 明确保留：仍在使用的工具脚本
KEEP = {
    # 本轮改造过的工具
    "_deploy_final.py", "_run_all2.py", "_tidy_0918.py",
    # ★ 这些**是工具不是探测残留**（按 docstring 判的，别看前缀）：
    #   _quick.py      快速跑一批指定测试并汇总（本机没 tail，靠它）
    #   _bench3.py     连跑 3 次打字基准看波动
    #   _perf_split.py cProfile 把打字耗时按函数拆开
    #   _geo_ui.py     量控件几何，查压叠/挤坏
    #   _shot_ui.py    截图验证侧栏撤销条 / 清空按钮 / 返回胶囊
    "_quick.py", "_bench3.py", "_perf_split.py", "_geo_ui.py", "_shot_ui.py",
    # 本轮（多语言）新增的界面截图工具 —— 证据要能复现
    "_shot_ml.py",
    # 本轮新增的分级探针 —— 技能里把它们记作「进程不退出」这类问题的
    # 标准排查手段（每级一个独立子进程 + 硬超时 + 只改一个变量），
    # 将来再遇到同类问题直接复用，别删。
    "_probe_edge_exit.py", "_probe_edge_exit2.py", "_probe_edge_hang.py",
    # 本轮最终验收证据，别收走
    "_run_all_result.txt", "_deploy_final.txt",
    SELF_LOG,
}

# 本轮**一次性**探测脚本（结论已写进 SKILL.md 与 memory，脚本本身可归档）
PROBE_PY = {
    "_tr_probe.py", "_tr_probe2.py", "_tr_probe3.py", "_tr_probe4.py",
    "_tr_probe5.py",
    # 多语言通道能力探测（结论已抄进 app.py 注释与 test_multilang.py）
    "_tr_probe6.py", "_tr_probe7.py",
}

LOG_EXT = (".txt", ".log", ".png")


def moved_today(path):
    try:
        mt = datetime.date.fromtimestamp(os.path.getmtime(path))
    except OSError:
        return False
    return mt == TODAY


os.makedirs(TRASH, exist_ok=True)

# ---- 硬闸门：先扫全部 .py 源码，被引用到的文件一律不动 ----
# 这样「移动不会破坏依赖」是**证明**出来的，不用靠重跑全量回归去推断。
import re

_src_text = {}
_ME = os.path.basename(__file__)
for fn in os.listdir(BUILD):
    if fn.endswith(".py"):
        # ★ 别把本脚本自己算成「引用源」—— 本脚本里当然提到了
        #   _tr_probe*.py 这些名字（它们在 PROBE_PY 里），
        #   否则闸门会为了「保护」而把它们全留下，等于没清。
        if fn == _ME:
            continue
        try:
            _src_text[fn] = open(os.path.join(BUILD, fn),
                                 encoding="utf-8", errors="replace").read()
        except OSError:
            pass


def referenced(name):
    """有没有别的 .py 文本里提到这个名字（含注释/字符串/路径）。"""
    pat = re.compile(r"""['"\s(/\\]%s['"\s.)/\\]""" % re.escape(name))
    for fn, src in _src_text.items():
        if fn == name:
            continue
        if pat.search(src):
            return fn
    return None


# ★ 自己的 stdout 重定向目标绝不能搬 —— 见文件头 SELF_LOG 的说明。
#   这里统一按 `_tidy` 前缀排除（_tidy.txt / _tidy2.txt / _tidy_log.txt）。


moved, kept, skipped_old, skipped_ref = [], [], [], []
for fn in sorted(os.listdir(BUILD)):
    p = os.path.join(BUILD, fn)
    if not os.path.isfile(p):
        continue
    if not fn.startswith("_"):
        continue
    if fn in KEEP or fn.startswith("_tidy"):
        kept.append(fn)
        continue
    is_log = fn.lower().endswith(LOG_EXT)
    is_probe = fn in PROBE_PY
    if not (is_log or is_probe):
        kept.append(fn)
        continue
    if not moved_today(p):
        skipped_old.append(fn)
        continue
    who = referenced(fn)
    if who:
        skipped_ref.append((fn, who))
        continue
    dst = os.path.join(TRASH, fn)
    if os.path.exists(dst):
        os.remove(dst)
    shutil.move(p, dst)
    moved.append(fn)

L = []


def say(s=""):
    L.append(str(s))
    print(s)


say("=" * 66)
say("归档到 %s" % TRASH)
say("=" * 66)
say("已归档 %d 个：" % len(moved))
for fn in moved:
    say("   " + fn)
say()
say("保留（在用工具脚本）: %s" % ", ".join(sorted(kept)))
say("跳过（非今日修改）%d 个" % len(skipped_old))
if skipped_ref:
    say("跳过（被源码引用，不能动）%d 个：" % len(skipped_ref))
    for fn, who in skipped_ref:
        say("   %s   <- 被 %s 引用" % (fn, who))
say("RESULT OK")

# 自己写日志（不依赖 shell 重定向，免得把日志文件自己搬进回收站）
with open(os.path.join(BUILD, SELF_LOG), "w", encoding="utf-8") as f:
    f.write("\n".join(L) + "\n")
print("\nlog -> build/%s" % SELF_LOG)
