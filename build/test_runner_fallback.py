# -*- coding: utf-8 -*-
"""单元测试：_run_all2.py 的「超时未退出·按产物判定」回退逻辑。

背景：test_edge_tts.py 会**跑完但进程退不出**（Qt FFmpeg 媒体线程
持着 GIL 不放，详见该脚本尾部的注释）。这种「跑完但退不出」只能看
产物判定 —— 但**看产物**这件事本身有把真卡死洗成绿的风险，
所以必须有三道护栏，且必须被测试钉住：
  1) 产物文件不存在        → 仍判真失败（不许瞎给绿）
  2) 产物文件是上一次的旧文件 → 仍判真失败（mtime 必须晚于本次启动）
  3) 产物文件是新的且能解析 → 才按产物判定，且**单独归为一档**
     （不混进正常通过，也不计进真失败）

⚠ 本文件用 ast 从 _run_all2.py 里**只抽出 parse 函数**再执行。
   直接 `import _run_all2` 会把整个 18 分钟的全量回归跑起来。
"""
import ast
import io
import os
import sys

BUILD = r"D:\Dictionary\build"
RUNNER = os.path.join(BUILD, "_run_all2.py")

PASS = []
FAIL = []


def check(name, cond, detail=""):
    if cond:
        PASS.append(name)
    else:
        FAIL.append("%s %s" % (name, detail))


# ---- 从 runner 源码里只取出 parse 函数 ----
src = io.open(RUNNER, encoding="utf-8").read()
tree = ast.parse(src)
fn_src = None
for node in tree.body:
    if isinstance(node, ast.FunctionDef) and node.name == "parse":
        fn_src = ast.get_source_segment(src, node)
        break
check("能从 _run_all2.py 抽出 parse()", fn_src is not None)
if fn_src is None:
    print("PASS=0 FAIL=1")
    sys.exit(1)

ns = {"re": __import__("re")}
exec(compile(fn_src, "<parse>", "exec"), ns)
parse = ns["parse"]

# 抽出来的确实是真货：拿已知输出试一下
check("抽出的 parse 可用（pass/fail=N）",
      parse("RESULT  pass=32  fail=0") == (32, 0, "pass/fail=N"),
      repr(parse("RESULT  pass=32  fail=0")))

# ---- 复刻 runner 里的回退判定（与 _run_all2.py 保持一致）----
def fallback(fn, t0):
    """返回 (npass, nfail, how)，逻辑与 _run_all2.py 的 TimeoutExpired 分支一致。"""
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
    return np_, nf_, how


def classify(np_, nf_, rc, how):
    """复刻 runner 的四档分类，返回 '真失败' / '超时未退出' / '未解析' / '通过'。"""
    if nf_ > 0:
        return "真失败"
    if how.startswith("超时未退出"):
        return "超时未退出" if "按产物判定" in how else "真失败"
    if rc not in (0, None):
        return "真失败"
    return "未解析" if not how else "通过"


ART = os.path.join(BUILD, "test_edge_tts.txt")
have_art = os.path.exists(ART)

if have_art:
    mt = os.path.getmtime(ART)

    # 场景 A：产物是本次跑出来的（t0 早于产物 mtime）→ 应按产物判定
    np_, nf_, how = fallback("test_edge_tts.py", mt - 60)
    check("A 新产物 → 按产物判定", "按产物判定" in how, how)
    check("A 解析出 60/0", (np_, nf_) == (60, 0), repr((np_, nf_, how)))
    check("A 分类为「超时未退出」而非真失败",
          classify(np_, nf_, -9, how) == "超时未退出",
          classify(np_, nf_, -9, how))

    # 场景 B：产物是上一次的旧文件（t0 远晚于 mtime）→ 不许给绿
    np2, nf2, how2 = fallback("test_edge_tts.py", mt + 600)
    check("B 旧产物 → 判为无产物", how2 == "超时未退出(无产物)", how2)
    check("B 分类为真失败（护栏生效）",
          classify(np2, nf2, -9, how2) == "真失败",
          classify(np2, nf2, -9, how2))

    # 场景 C：产物本身有失败 → 就算按产物判定也必须算真失败
    check("C 产物含 FAIL>0 → 仍判真失败",
          classify(59, 1, -9, "超时未退出·按产物判定(pass/fail=N)") == "真失败")

    # 场景 D：压根没有产物文件的脚本超时 → 真失败
    np3, nf3, how3 = fallback("test_no_such_artifact_xyz.py", mt - 60)
    check("D 无产物文件 → 真失败",
          classify(np3, nf3, -9, how3) == "真失败", how3)
else:
    FAIL.append("找不到 test_edge_tts.txt，无法验回退路径")

# 场景 E：正常退出、有计数的脚本不受影响
check("E 正常脚本分类不受影响", classify(60, 0, 0, "pass/fail=N") == "通过")
# 场景 F：退出码正常的「未解析」仍单独一档
check("F 未解析仍单独一档", classify(0, 0, 0, "") == "未解析")

print("PASS=%d FAIL=%d" % (len(PASS), len(FAIL)))
for f in FAIL:
    print("  FAIL:", f)
# 本文件不加载 Qt、不播音频，进程能干净退出，所以用 sys.exit 就好。
# （对比：test_edge_tts.py 播过音后连 os._exit 都退不出，
#   详见那个文件尾部的注释 —— 别把这两个场景搞混。）
sys.exit(1 if FAIL else 0)
