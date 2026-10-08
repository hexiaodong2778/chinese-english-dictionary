# -*- coding: utf-8 -*-
"""DeepSeek 站内助手：配置、请求解析、语言提示和笔记保存。"""
import io
import json
import os
import sys
import tempfile

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8",
                              errors="replace")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, r"D:\Dictionary\build")

from PySide6.QtWidgets import QApplication
app = QApplication.instance() or QApplication(sys.argv)

import app as A

ok = fail = 0


def chk(name, cond, extra=""):
    global ok, fail
    if cond:
        ok += 1
        print(f"  PASS  {name}")
    else:
        fail += 1
        print(f"  FAIL  {name}  {extra}")


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self):
        return json.dumps(self.payload, ensure_ascii=False).encode("utf-8")


print("== 1) 配置项与语言提示 ==")
for key in ("deepseek_api_key", "deepseek_model", "deepseek_base_url",
            "deepseek_timeout"):
    chk(f"配置模板含 {key}", key in A.CONFIG_TEMPLATE)

p = A.ai_build_prompt("explain", "日本", lang="ja")
chk("日语模式提示词使用日语词语", "日语词语" in p, p)
p = A.ai_build_prompt("example", "bonjour", lang="fr")
chk("法语模式提示词使用法语词语", "法语词语" in p, p)
chk("系统提示词包含当前语言", "日语" in A.ai_system_prompt("ja"))

services = {s["key"]: s for s in A.AI_SERVICES}
chk("包含 DeepSeek 站内服务", services.get("deepseek_api", {}).get("internal")
    == "deepseek")

print("== 2) API 请求与 JSON 解析 ==")
old_cfg = dict(A.CONFIG)
old_open = A._open_url
captured = {}


def fake_open(req, timeout):
    captured["url"] = req.full_url
    captured["timeout"] = timeout
    captured["auth"] = req.get_header("Authorization")
    captured["body"] = json.loads(req.data.decode("utf-8"))
    return FakeResponse({
        "choices": [{"message": {"content": "这是 DeepSeek 的回答"}}]
    })


try:
    A.CONFIG.update({
        "deepseek_api_key": "test-key",
        "deepseek_model": "deepseek-chat",
        "deepseek_base_url": "https://api.deepseek.com",
        "deepseek_timeout": "60",
    })
    A._open_url = fake_open
    content, err = A.deepseek_chat([{"role": "user", "content": "测试"}])
    chk("解析 DeepSeek 正文", content == "这是 DeepSeek 的回答", repr(content))
    chk("请求成功时无错误", err == "", err)
    chk("使用 chat/completions 端点",
        captured.get("url") == "https://api.deepseek.com/chat/completions",
        captured.get("url"))
    chk("携带 Bearer API Key",
        captured.get("auth") == "Bearer test-key", captured.get("auth"))
    chk("模型名来自配置",
        captured.get("body", {}).get("model") == "deepseek-chat", captured)

    A.CONFIG["deepseek_api_key"] = ""
    no_key, no_key_err = A.deepseek_chat([{"role": "user", "content": "x"}])
    chk("无 Key 时给出明确提示",
        no_key is None and "API Key" in no_key_err, repr(no_key_err))
finally:
    A._open_url = old_open
    A.CONFIG.clear()
    A.CONFIG.update(old_cfg)

print("== 3) 单词笔记 ==")
with tempfile.TemporaryDirectory() as td:
    store = A.UserStore(os.path.join(td, "user.db"))
    chk("写入笔记成功", store.set_note("dog", "AI 笔记", 0))
    chk("读取笔记正确", store.get_note("dog", 0) == "AI 笔记",
        store.get_note("dog", 0))
    chk("笔记写入后已加入单词本", store.has_word("dog", 0))
    store.con.close()

print("== 4) 站内窗口可创建 ==")
w = A.MainWindow()
dlg = A.DeepSeekDialog(w, initial_prompt="", subject="dog", note_word="dog")
chk("窗口包含聊天区", hasattr(dlg, "chat"))
chk("窗口包含输入框", hasattr(dlg, "input_edit"))
chk("窗口包含发送按钮", hasattr(dlg, "send_btn"))
dlg.close()
w.close()

print()
print(f"RESULT  pass={ok}  fail={fail}")
sys.exit(1 if fail else 0)
