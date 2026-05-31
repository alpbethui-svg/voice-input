# 输入助手 / Voice Input Helper

Windows 本地输入助手：按热键录音，用 Whisper 本地转写，再可选调用本地 Ollama 做保守纠错；也支持区域截图 OCR，并把识别结果复制到剪贴板。

## 功能

- `Alt+3`：语音输入。按住 `Alt`，按一下 `3` 开始录音，松开 `Alt` 停止并输入到当前光标。
- `Alt+4` / `Ctrl+Alt+O`：区域截图 OCR，拖选区域后把识别结果复制到剪贴板。
- Whisper 使用 `faster-whisper` / CTranslate2，本地推理。
- LLM 纠错默认使用本机 Ollama，不需要云端大模型 API。
- OCR 使用 RapidOCR。
- 模型不随安装包打包，安装后通过模型准备窗口或首次使用时准备。

## 主要文件

| 文件 | 作用 |
| --- | --- |
| `voice_input.pyw` | 主程序入口、热键、托盘菜单 |
| `config.py` | 热键、Whisper、Ollama、OCR、悬浮提示配置 |
| `recorder.py` | 录音 |
| `transcriber.py` | Whisper 转写 |
| `polisher.py` | 本地 Ollama 保守纠错 |
| `ocr.py` | 区域截图 OCR |
| `overlay.py` | 悬浮提示 / OCR 框选 UI |
| `model_setup.py` | 模型准备/检查窗口 |
| `prepare_models.py` / `download_model.py` | 模型准备入口 |
| `input_helper.spec` | PyInstaller 打包配置 |
| `installer/` | Inno Setup 安装脚本和说明 |

## 安装开发依赖

建议使用 Python 3.10+，在虚拟环境中安装：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## 运行

```powershell
python .\voice_input.pyw
```

如需提前准备模型：

```powershell
python .\prepare_models.py
```

## 本地 LLM 配置

默认配置在 `config.py`：

```python
OLLAMA_HOST = "http://localhost:11434"
OLLAMA_MODEL = "qwen2.5:3b"
LLM_ENABLED = True
```

这是本机 Ollama 地址，不包含 API key。若后续改成云端 API，请不要把真实 key、token、cookie 或私钥提交到仓库；使用 `.env` 或 `config.local.py`，并保持这些文件被 `.gitignore` 排除。

## 打包

PyInstaller 配置文件为：

```powershell
pyinstaller .\input_helper.spec
```

安装包脚本在 `installer/` 下。生成物应放在 `dist/`、`build/` 或 `installer/Output/`，这些目录不会提交到 Git。

## 仓库内容说明

本仓库只保留源码、配置和安装脚本，不包含：

- Whisper / Ollama / HuggingFace 模型缓存；
- PyInstaller 生成的 `dist/`、`build/`；
- 安装包输出 `installer/Output/`；
- 运行日志；
- 录音、截图、OCR 输出和转写文本；
- API key、token、cookie、私钥等敏感凭据。

历史开发 handoff 见 `docs/handoff-2026-05-30.md`。
