"""
输入助手配置
"""

import os

# --- 项目路径 ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
APP_NAME = "输入助手"
LOG_MAX_BYTES = 2 * 1024 * 1024
LOG_BACKUP_COUNT = 3

# --- Whisper 模型配置 ---
# 可选: tiny, base, small, medium, large-v2, large-v3
# medium 在 RTX 2060 8GB 上好用，CPU 上也够快
WHISPER_MODEL = "medium"
# 推理设备: "cuda" 或 "cpu" (设为 "auto" 自动选择)
WHISPER_DEVICE = "auto"
# int8 量化可省 ~40% VRAM，几乎不影响准确率
WHISPER_INT8 = True
# 推理精度
WHISPER_COMPUTE_TYPE = "int8_float16"  # CUDA 用 int8_float16, CPU 用 int8
# 语言
WHISPER_LANGUAGE = "zh"
# 初始提示词，帮助模型理解上下文
WHISPER_INITIAL_PROMPT = "以下是中文普通话。"
# beam_size: 越大越准但越慢，1-5 之间
WHISPER_BEAM_SIZE = 3

# --- 音频配置 ---
SAMPLE_RATE = 16000  # Whisper 要求 16kHz
CHANNELS = 1  # 单声道
AUDIO_DTYPE = "int16"

# --- 热键配置 ---
# Alt+3 触发录音：按住 Alt，按一下 3 开始，说完松开 Alt 停止
HOTKEY_COMBO = "alt+3"
HOTKEY_DISPLAY = "Alt+3"
HOTKEY_CHAR = "3"
HOTKEY_VK = 0x33  # '3' 键虚拟键码
# Alt+4 触发区域截图 OCR：拖选区域后文字进入剪贴板
OCR_HOTKEY_DISPLAY = "Alt+4 / Ctrl+Alt+O"
OCR_HOTKEY_CHAR = "4"
OCR_HOTKEY_VK = 0x34  # '4' 键虚拟键码
OCR_ALT_HOTKEY_CHAR = "o"
OCR_ALT_HOTKEY_VK = 0x4F  # 'O' 键虚拟键码
# OCR 截图预处理：对终端/网页小字更友好
OCR_IMAGE_SCALE = 2.5
OCR_CONTRAST = 1.35
OCR_SHARPNESS = 1.8
OCR_MIN_CONFIDENCE = 0.35
# 最长录音时间（秒），避免误按后无限录音
MAX_RECORD_SECONDS = 60
# 按着说、松手停的模式不需要静音检测，避免低音量麦克风误判
SILENCE_TIMEOUT = 0

# --- 输入配置 ---
# 语音输入后恢复用户原剪贴板，避免覆盖原本复制的内容
RESTORE_CLIPBOARD = True
# 复制到剪贴板后等待目标程序可粘贴的最长时间
CLIPBOARD_READY_TIMEOUT = 0.5

# --- LLM 纠错配置 ---
# Ollama 服务地址
OLLAMA_HOST = "http://localhost:11434"
# 模型名称 (qwen2.5:3b 是 3B 参数的中文优化模型，VRAM ~2GB)
OLLAMA_MODEL = "qwen2.5:3b"
# 正常使用不要等太久：超时就直接使用 Whisper 原文
OLLAMA_TIMEOUT = 8
# 是否启用 LLM 纠错（如果 Ollama 没装可设为 False）
LLM_ENABLED = True
# 保守纠错：只修明显识别错误和标点，不改写用户原意
LLM_SYSTEM_PROMPT = (
    "你是语音转文字的保守纠错器。只修正明显错别字、同音误识别和标点。"
    "不要扩写、不要总结、不要换说法、不要添加原文没有的信息。"
    "如果不确定就保持原文。只输出修正后的文本。"
)
# 最大 token 数
LLM_MAX_TOKENS = 160

# --- 悬浮提示配置 ---
OVERLAY_WIDTH = 360
OVERLAY_HEIGHT = 120
OVERLAY_ALPHA = 0.85  # 透明度
OVERLAY_BG = "#1e1e2e"
OVERLAY_FG = "#cdd6f4"
OVERLAY_ACCENT = "#89b4fa"
OVERLAY_ERROR = "#f38ba8"
OVERLAY_FONT = ("Microsoft YaHei UI", 14)
OVERLAY_POSITION = "bottom"  # bottom / top / center
