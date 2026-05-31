"""
Whisper 语音转文字模块
使用 faster-whisper (CTranslate2) 进行本地推理
"""

import logging
import threading

log = logging.getLogger("input_helper.transcriber")

from config import (
    WHISPER_MODEL,
    WHISPER_DEVICE,
    WHISPER_COMPUTE_TYPE,
    WHISPER_LANGUAGE,
    WHISPER_INITIAL_PROMPT,
    WHISPER_BEAM_SIZE,
)

# 全局单例模型
_model = None
_model_lock = threading.Lock()


def _get_model():
    """懒加载 Whisper 模型（全局单例，避免重复加载）"""
    global _model

    if _model is not None:
        return _model

    with _model_lock:
        if _model is not None:
            return _model

        _model = _load_model()
        return _model


def _load_model():
    """加载模型。auto 模式先尝试 CUDA，失败后回退 CPU。

    不再 import torch 只为检测 CUDA，避免 PyInstaller 把整套 PyTorch/CUDA
    打进安装包。CUDA 是否可用由 faster-whisper/CTranslate2 自己验证。
    """
    if WHISPER_DEVICE == "auto":
        try:
            return _create_model("cuda", "int8_float16")
        except Exception as e:
            log.warning("CUDA 加载失败，回退 CPU: %s", e)
            return _create_model("cpu", "int8")

    compute_type = WHISPER_COMPUTE_TYPE
    if WHISPER_DEVICE == "cpu":
        compute_type = "int8"
    return _create_model(WHISPER_DEVICE, compute_type)


def _create_model(device, compute_type):
    from faster_whisper import WhisperModel

    log.info("加载模型 '%s' (device=%s, %s)...", WHISPER_MODEL, device, compute_type)
    model = WhisperModel(
        WHISPER_MODEL,
        device=device,
        compute_type=compute_type,
        download_root=None,
        local_files_only=False,
        cpu_threads=4,
        num_workers=1,
    )
    log.info("模型加载完成 (device=%s)", device)
    return model


def transcribe(audio_array, on_progress=None):
    """
    转写音频为文本。
    先用 VAD 过滤静音；如果 VAD 把内容全过滤掉，再自动重试一次无 VAD。
    """
    if on_progress:
        on_progress("加载模型...")

    model = _get_model()

    if on_progress:
        on_progress("转写中...")

    result = _transcribe_once(model, audio_array, vad_filter=True)
    if not result:
        log.info("VAD 未识别到内容，重试无 VAD 转写")
        result = _transcribe_once(model, audio_array, vad_filter=False)

    if result:
        log.info("转写结果: %s", result[:80])
    else:
        log.info("未检测到语音")

    return result


def _transcribe_once(model, audio_array, vad_filter):
    kwargs = dict(
        language=WHISPER_LANGUAGE,
        beam_size=WHISPER_BEAM_SIZE,
        initial_prompt=WHISPER_INITIAL_PROMPT,
        condition_on_previous_text=False,
        no_speech_threshold=0.6,
    )

    if vad_filter:
        kwargs.update(
            vad_filter=True,
            vad_parameters=dict(
                min_silence_duration_ms=500,
                threshold=0.25,
            ),
        )
    else:
        kwargs.update(vad_filter=False)

    segments, info = model.transcribe(audio_array, **kwargs)

    texts = []
    for segment in segments:
        text = segment.text.strip()
        if text:
            texts.append(text)

    return "".join(texts)


def unload_model():
    """释放模型显存"""
    global _model
    _model = None
    log.info("模型已卸载")
