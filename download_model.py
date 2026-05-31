"""
兼容旧入口：打开输入助手模型准备窗口。

安装包不会内置 Whisper/Ollama/RapidOCR 模型；需要时在窗口里下载或检查。
"""

from model_setup import run_model_setup


if __name__ == "__main__":
    run_model_setup()
