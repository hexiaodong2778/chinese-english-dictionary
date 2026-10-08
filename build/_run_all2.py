# -*- coding: utf-8 -*-
"""跑全部测试脚本并汇总。

解析策略（按优先级）：
  1) "PASS=n FAIL=m"          —— 最常见
  2) "发音测试：通过 N / 失败 M"
  3) "通过 N / 失败 M"
  4) "RESULT OK" / "ALL OK"   —— 只有成败没有计数，算 1/0
  5) 退出码非 0 且有 Traceback —— 判为失败并记录
"""
import io
import os
import re
import subprocess
import sys
import time

# 路径自适应：本脚本所在目录即测试根目录，克隆到任何位置都能直接跑
BUILD = os.path.dirname(os.path.abspath(__file__))
# 默认使用当前解释器；如需锁定某个特定 Python，把它改成绝对路径即可
PY = sys.executable or r"D:\hclaw\python\python.exe"

scripts = sorted(fn for fn in os.listdir(BUILD)
                 if (fn.startswith("test_") or fn.startswith("verify_"))
                 and fn.endswith(".py"))

env = dict(os.environ)
env["QT_QPA_PLATFORM"] = "offscreen"
env["PYTHONIOENCODING"] = "utf-8"

# 每个脚本的超时上限。
# ★ test_edge_tts.py 单独调短（2026-09-18）：它会**跑完但退不出**
#   （Qt FFmpeg 媒体线程持 GIL，详见该脚本尾部注释），
#   判定完全靠产物文件，所以没必要陪它等满 900s ——
#   它自己干活约 2~3 分钟，300s 足够宽裕。
#   调短只影响「多久轮到产物兜底」，不影响判定结果。
TIMEOUTS = {"test_edge_tts.py": 300}
DEFAULT_TIMEOUT = 900


def parse(text):
    """返回 (npass, nfail, 说明)。没解析出来返回 (0,0,'')。

    ⚠ 坑（2026-09-17 修）：原来的正则写的是大写 `PASS\\s*=`，
       而项目里一大半脚本（包括 test_smoke.py 的
       `RESULT  pass=32  fail=0`）用的是**小写** pass/fail。
       正则没加 re.I，于是这些脚本全被解析成 (0,0,'')，
       汇总里显示「0 PASS 0 FAIL」并被标成「有问题」——
       看起来像 33 个脚本坏了，其实它们全是绿的，是解析器瞎了。

       教训：解析器要按**实际输出**来写，不是按我以为的格式来写。
             并且无法解析时不该静默返回 0/0，要标出来（见下方 bad 判定）。
    """
    # 1) pass=N fail=M（大小写不敏感；容忍 RESULT: 32 passed, 0 failed）
    mp = re.search(r"\bpass(?:ed)?\s*[=:]\s*(\d+)\s*[,;]?\s*"
                   r"\bfail(?:ed)?\s*[=:]\s*(\d+)", text, re.I)
    if mp:
        return int(mp.group(1)), int(mp.group(2)), "pass/fail=N"
    # 2) RESULT: 13 passed, 0 failed
    mp = re.search(r"(\d+)\s*passed\s*[,;]?\s*(\d+)\s*failed", text, re.I)
    if mp:
        return int(mp.group(1)), int(mp.group(2)), "N passed/M failed"
    # 3) 通过 N / 失败 M
    mp = re.search(r"通过\s*(\d+)\s*[/／]\s*失败\s*(\d+)", text)
    if mp:
        return int(mp.group(1)), int(mp.group(2)), "通过/失败"
    # 4) N/M 通过
    mp = re.search(r"(\d+)\s*[/／]\s*(\d+)\s*(?:通过|passed|PASS)",
                   text, re.I)
    if mp:
        return int(mp.group(1)), 0, "N/N"
    # 5) RESULT OK / ALL OK（只有成败没有计数）
    if re.search(r"RESULT\s+OK|ALL\s+OK|ALL\s+PASS|^\s*OK\s*$",
                 text, re.I | re.M):
        return 1, 0, "RESULT OK"
    # 6) 数「PASS xxx / FAIL xxx」逐行标签
    n_pass = len(re.findall(r"^\s*PASS\b|^\s*✓", text, re.M))
    n_fail = len(re.findall(r"^\s*FAIL\b|^\s*✗", text, re.M))
    if n_pass or n_fail:
        return n_pass, n_fail, "逐行 PASS/FAIL"
    # 7) 有 FAIL 字样或回溯但没数字 → 判失败
    if re.search(r"\bFAIL\b|Traceback", text):
        return 0, 1, "疑似失败"
    # 8) 脚本只打印 "done" 之类 —— 退出码正常就算过，但标明未解析
    return 0, 0, ""


results = []
tp = tf = 0
for fn in scripts:
    try:
        t0 = time.time()
        p = subprocess.run([PY, fn], cwd=BUILD, env=env,
                           capture_output=True,
                           timeout=TIMEOUTS.get(fn, DEFAULT_TIMEOUT))
        out = (p.stdout or b"").decode("utf-8", "replace")
        err = (p.stderr or b"").decode("utf-8", "replace")
        text = out + "\n" + err
        np_, nf_, how = parse(text)
        # 退出码异常但解析到 0 失败 → 也标出来
        results.append((fn, np_, nf_, p.returncode, how))
        tp += np_
        tf += nf_
    except subprocess.TimeoutExpired:
        # ★ 进程超时没退出 ≠ 测试失败（2026-09-18 定）。
        #   已查明 test_edge_tts.py 的真实情况：它**跑完了**
        #   （它自己的产物文件里写着 PASS=60 FAIL=0），
        #   但进程退不出去 —— 第 ⑨ 节真的播放音频，Qt 的 FFmpeg
        #   媒体后端在自己的线程上异步探测 mp3，该线程停在原生调用里
        #   并且**持着 GIL 不放**，主线程从最后一次 print 之后就拿不回
        #   GIL，于是后面任何 Python 语句都执行不到
        #   （所以 os._exit / sys.exit / TerminateProcess 全都没机会跑，
        #     faulthandler 也一个栈都打不出来）。
        #   → 这种「跑完但退不出」只能看**产物**判定，不能看进程退出码。
        #
        #   护栏（避免把真卡死洗成绿）：
        #     1) 产物文件必须存在，且 mtime 晚于本次启动时间
        #     2) 产物里必须能解析出 pass/fail
        #     3) 单独归为「超时未退出·按产物判定」一档，不混进正常通过
        fb = os.path.join(BUILD, fn[:-3] + ".txt")
        np_ = nf_ = 0
        how = "超时未退出(无产物)"
        if os.path.exists(fb) and os.path.getmtime(fb) >= t0 - 1:
            try:
                ftxt = io.open(fb, encoding="utf-8", errors="replace").read()
                fnp, fnf, fhow = parse(ftxt)
                if fhow:
                    np_, nf_, how = fnp, fnf, "超时未退出·按产物判定(%s)" % fhow
            except OSError:
                pass
        results.append((fn, np_, nf_, -9, how))
        tp += np_
        tf += nf_
    except Exception as e:
        results.append((fn, 0, 1, -2, "异常 %s" % type(e).__name__))
        tf += 1

lines = ["=" * 74, "全量回归汇总", "=" * 74, "",
         "%-36s %6s %6s %5s %s" % ("脚本", "PASS", "FAIL", "EXIT", "解析方式"),
         "-" * 74]
nbad = 0
nfail_real = 0
nunparsed = 0
nhang = 0
for fn, np_, nf_, rc, how in results:
    # 分四档：
    #   真失败       —— 解析到 FAIL>0，或非零退出，或超时且**没有**可比对的产物
    #   超时未退出   —— 进程没退，但自己的产物文件给出了 pass/fail（单独一档，
    #                  不计入真失败，但必须显式列出来，不藏）
    #   未解析       —— 退出码正常但输出里没有可识别的计数
    #   通过
    if nf_ > 0:
        mark = "   <== 真失败"
        nbad += 1
        nfail_real += 1
    elif how.startswith("超时未退出"):
        if "按产物判定" in how:
            mark = "   <== 超时未退出(产物已判定)"
            nhang += 1
        else:
            mark = "   <== 真失败(超时且无产物)"
            nbad += 1
            nfail_real += 1
    elif rc not in (0, None):
        mark = "   <== 真失败"
        nbad += 1
        nfail_real += 1
    elif not how:
        mark = "   <== 未解析(退出码正常)"
        nunparsed += 1
    else:
        mark = ""
    lines.append("%-36s %6d %6d %5d %s%s" % (
        fn, np_, nf_, rc, how, mark))
lines += ["-" * 74,
          "%-36s %6d %6d" % ("合计", tp, tf),
          "",
          "脚本数 = %d" % len(results),
          "真失败 = %d" % nfail_real,
          "超时未退出(按产物判定) = %d" % nhang,
          "未解析(退出码正常) = %d" % nunparsed,
          "TOTAL PASS=%d FAIL=%d" % (tp, tf)]

io.open(os.path.join(BUILD, "_run_all_result.txt"), "w",
        encoding="utf-8").write("\n".join(lines) + "\n")
print("TOTAL PASS=%d FAIL=%d  scripts=%d  真失败=%d  "
      "超时未退出=%d  未解析=%d"
      % (tp, tf, len(results), nfail_real, nhang, nunparsed))
