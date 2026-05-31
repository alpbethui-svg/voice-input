"""
模型准备/检查窗口。

安装包不内置 Whisper/Ollama/RapidOCR 模型；用户可在这里按需下载或预热。
"""

import subprocess
import threading
import tkinter as tk
from tkinter import ttk

import requests

from config import OLLAMA_HOST, OLLAMA_MODEL, WHISPER_MODEL


class ModelSetupWindow:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("输入助手 - 模型准备")
        self.root.geometry("640x430")
        self.root.minsize(560, 360)

        self._build_ui()

    def _build_ui(self):
        frame = ttk.Frame(self.root, padding=16)
        frame.pack(fill="both", expand=True)

        title = ttk.Label(frame, text="输入助手模型准备", font=("Microsoft YaHei UI", 14, "bold"))
        title.pack(anchor="w")

        desc = ttk.Label(
            frame,
            text=(
                "安装包不内置大模型。首次使用前可在这里下载/检查；"
                "也可以直接使用快捷键，程序会在首次加载时按需下载。"
            ),
            wraplength=590,
        )
        desc.pack(anchor="w", pady=(6, 12))

        buttons = ttk.Frame(frame)
        buttons.pack(fill="x", pady=(0, 10))

        ttk.Button(buttons, text=f"下载/预热 Whisper {WHISPER_MODEL}", command=self.prepare_whisper).pack(
            side="left", padx=(0, 8)
        )
        ttk.Button(buttons, text=f"检查 Ollama {OLLAMA_MODEL}", command=self.check_ollama).pack(
            side="left", padx=(0, 8)
        )
        ttk.Button(buttons, text=f"拉取 {OLLAMA_MODEL}", command=self.pull_ollama).pack(
            side="left", padx=(0, 8)
        )
        ttk.Button(buttons, text="预热 OCR", command=self.prepare_ocr).pack(side="left")

        self.output = tk.Text(frame, height=16, wrap="word")
        self.output.pack(fill="both", expand=True)
        self.output.configure(font=("Consolas", 10))

        self.log("说明：")
        self.log(f"- Whisper {WHISPER_MODEL} 用于 Alt+3 语音转文字，模型较大，首次下载会比较久。")
        self.log(f"- Ollama {OLLAMA_MODEL} 用于保守纠错；不可用时会直接使用 Whisper 原文。")
        self.log("- RapidOCR 用于 Alt+4 / Ctrl+Alt+O 截图识别，首次会准备 OCR 小模型。")

    def log(self, text):
        self.output.insert("end", text + "\n")
        self.output.see("end")

    def log_threadsafe(self, text):
        self.root.after(0, lambda: self.log(text))

    def run_task(self, title, func):
        def worker():
            self.log_threadsafe("")
            self.log_threadsafe(f"== {title} ==")
            try:
                func()
            except Exception as e:
                self.log_threadsafe(f"失败：{e}")

        threading.Thread(target=worker, daemon=True).start()

    def prepare_whisper(self):
        def work():
            self.log_threadsafe("开始加载 Whisper。若本机没有缓存，会从 Hugging Face 下载。")
            self.log_threadsafe("这一步可能需要几分钟；完成后 Alt+3 首次响应会更快。")
            from transcriber import _get_model

            _get_model()
            self.log_threadsafe("Whisper 已就绪。GPU/CPU 加载详情可查看 input_helper.log。")

        self.run_task(f"Whisper {WHISPER_MODEL}", work)

    def check_ollama(self):
        def work():
            self.log_threadsafe(f"检查 Ollama: {OLLAMA_HOST}")
            resp = requests.get(f"{OLLAMA_HOST}/api/tags", timeout=5)
            resp.raise_for_status()
            models = [m.get("name", "") for m in resp.json().get("models", [])]
            if any(name == OLLAMA_MODEL or name.startswith(OLLAMA_MODEL + ":") for name in models):
                self.log_threadsafe(f"Ollama 模型已存在：{OLLAMA_MODEL}")
            else:
                self.log_threadsafe(f"Ollama 正在运行，但未找到：{OLLAMA_MODEL}")
                if models:
                    self.log_threadsafe("当前模型：" + ", ".join(models))
                self.log_threadsafe(f"可点“拉取 {OLLAMA_MODEL}”，或在终端运行：ollama pull {OLLAMA_MODEL}")

        self.run_task("检查 Ollama", work)

    def pull_ollama(self):
        def work():
            self.log_threadsafe(f"开始拉取 Ollama 模型：{OLLAMA_MODEL}")
            cmd = ["ollama", "pull", OLLAMA_MODEL]
            creationflags = 0
            if hasattr(subprocess, "CREATE_NO_WINDOW"):
                creationflags = subprocess.CREATE_NO_WINDOW
            proc = subprocess.run(
                cmd,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                creationflags=creationflags,
            )
            if proc.stdout:
                for line in proc.stdout.splitlines():
                    if line.strip():
                        self.log_threadsafe(line.strip())
            if proc.returncode == 0:
                self.log_threadsafe(f"Ollama 模型已就绪：{OLLAMA_MODEL}")
            else:
                self.log_threadsafe(f"ollama pull 退出码：{proc.returncode}")

        self.run_task(f"拉取 {OLLAMA_MODEL}", work)

    def prepare_ocr(self):
        def work():
            self.log_threadsafe("开始预热 RapidOCR。")
            from ocr import _get_engine

            _get_engine()
            self.log_threadsafe("RapidOCR 已就绪。")

        self.run_task("预热 OCR", work)

    def run(self):
        self.root.mainloop()


def run_model_setup():
    ModelSetupWindow().run()


if __name__ == "__main__":
    run_model_setup()
