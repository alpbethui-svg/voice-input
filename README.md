# 输入助手

这是一个 Windows 小工具，主要解决两件事：

1. 按快捷键说话，自动把语音转成文字并输入到当前光标位置。
2. 框选屏幕上的一块区域，识别里面的文字并复制到剪贴板。

适合在微信、浏览器、记事本、Claude Code、Cursor、各种输入框里临时输入一段话，或者从截图、网页、终端里抠文字。

## 下载安装

普通用户不用装 Python，直接去右侧 **Releases** 下载安装包：

- `InputHelper-Setup.exe`

安装后开始菜单里会有两个入口：

- `输入助手`：启动主程序。
- `输入助手 - 模型准备`：检查或下载本地模型。

第一次安装后，建议先打开一次 `输入助手 - 模型准备`。Whisper 模型和 Ollama 模型没有打进安装包，需要在本机准备；这样安装包不会变成几个 GB。

## 怎么用

启动 `输入助手` 后，程序会在后台运行，系统托盘里会有图标。

### 语音输入

按法：

1. 按住 `Alt`。
2. 按一下 `3`，开始录音。
3. 说话。
4. 松开 `Alt`，停止录音。
5. 稍等片刻，识别出的文字会输入到当前光标位置。

默认流程是：本地 Whisper 转文字，然后用本机 Ollama 小模型做一次保守纠错。Ollama 不可用或超时时，会直接使用 Whisper 原文，不会卡住太久。

### 截图 OCR

按法：

1. 按 `Alt+4`，或者 `Ctrl+Alt+O`。
2. 用鼠标拖选要识别的区域。
3. 识别结果会复制到剪贴板。
4. 到目标位置手动粘贴即可。

OCR 不会自动粘贴，避免误把识别结果塞到不该输入的地方。

## 本机模型

当前默认配置在 `config.py`：

```python
WHISPER_MODEL = "medium"
OLLAMA_HOST = "http://localhost:11434"
OLLAMA_MODEL = "qwen2.5:3b"
```

也就是说：

- 语音识别用本地 Whisper `medium`。
- 纠错用本机 Ollama 的 `qwen2.5:3b`。
- 不需要云端大模型 API key。

如果你不想用 Ollama 纠错，可以在 `config.py` 里改：

```python
LLM_ENABLED = False
```

## 常见问题

### 运行后没反应？

先看系统托盘有没有 `输入助手` 图标。它不是一个一直显示窗口的软件，主要靠快捷键触发。

### 第一次语音输入很慢？

第一次加载或下载 Whisper 模型会慢一些。先运行 `输入助手 - 模型准备` 会更稳。

### OCR 结果在哪里？

OCR 结果在剪贴板里，需要你自己 `Ctrl+V` 粘贴。

### 会上传我的录音或截图吗？

默认不会。语音识别、OCR 和纠错都是本机流程：Whisper、本机 Ollama、RapidOCR。录音目前在内存中处理，OCR 临时截图正常会在识别后删除。

## 开发运行

如果你要改代码，再用源码方式运行。建议 Python 3.10+：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python .\voice_input.pyw
```

模型准备窗口：

```powershell
python .\prepare_models.py
```

打包：

```powershell
pyinstaller .\input_helper.spec
```

安装包脚本在 `installer/` 目录里，生成的安装包输出在 `installer/Output/`，不会提交到 Git。

## 仓库里有什么

| 文件 | 说明 |
| --- | --- |
| `voice_input.pyw` | 主程序入口、热键、托盘菜单 |
| `config.py` | 热键、Whisper、Ollama、OCR 配置 |
| `recorder.py` | 录音 |
| `transcriber.py` | Whisper 转写 |
| `polisher.py` | Ollama 保守纠错 |
| `ocr.py` | 截图 OCR |
| `overlay.py` | 悬浮提示和框选界面 |
| `model_setup.py` | 模型准备窗口 |
| `input_helper.spec` | PyInstaller 打包配置 |
| `installer/` | Inno Setup 安装脚本 |

仓库不放这些东西：模型缓存、打包生成的 `dist/`、安装包输出目录、运行日志、真实录音、截图、转写文本、API key、token、cookie、私钥。历史开发记录见 `docs/handoff-2026-05-30.md`。
