"""
打开输入助手模型准备窗口。

安装包不内置大模型；此脚本用于首次使用前下载/检查 Whisper、Ollama、RapidOCR。
"""

from model_setup import run_model_setup


if __name__ == "__main__":
    run_model_setup()
