"""
LLM 纠错模块
通过 Ollama API 调用本地 LLM 进行语音识别后纠错
"""

import logging
from difflib import SequenceMatcher
import time

import requests

from config import (
    OLLAMA_HOST,
    OLLAMA_MODEL,
    OLLAMA_TIMEOUT,
    LLM_ENABLED,
    LLM_SYSTEM_PROMPT,
    LLM_MAX_TOKENS,
)

log = logging.getLogger("voice_input.polisher")


def polish(text, on_progress=None):
    """
    使用本地 LLM 对 Whisper 输出进行保守纠错。
    失败、超时或改动过大时直接返回原文，优先保证输入流畅和不乱改意思。
    """
    if not LLM_ENABLED:
        return text

    if not text or len(text.strip()) < 2:
        return text

    if on_progress:
        on_progress("LLM 纠错中...")

    start = time.time()
    result = _call_ollama(text)
    elapsed = time.time() - start

    if not result:
        log.info("LLM 未返回结果，使用原文")
        return text

    result = _normalize_result(result)
    if _changed_too_much(text, result):
        log.warning("LLM 改动过大，使用原文: raw=%s / llm=%s", text[:80], result[:80])
        return text

    log.info("LLM 纠错完成 %.1fs: %s", elapsed, result[:80])
    return result


def _normalize_result(result):
    result = result.strip()
    # 模型偶尔会把结果包在引号里
    return result.strip('"“”')


def _changed_too_much(raw, polished):
    """防止 LLM 把口述内容扩写/改写成另一句话。"""
    if not polished:
        return True

    raw_clean = "".join(raw.split())
    polished_clean = "".join(polished.split())
    if not raw_clean:
        return True

    # 明显扩写基本都不是“纠错”
    if len(polished_clean) > len(raw_clean) + 20 and len(polished_clean) > len(raw_clean) * 1.4:
        return True

    similarity = SequenceMatcher(None, raw_clean, polished_clean).ratio()
    return similarity < 0.45


def _call_ollama(text):
    """调用 Ollama 聊天 API"""
    url = f"{OLLAMA_HOST}/api/chat"

    payload = {
        "model": OLLAMA_MODEL,
        "messages": [
            {"role": "system", "content": LLM_SYSTEM_PROMPT},
            {"role": "user", "content": text},
        ],
        "stream": False,
        "options": {
            "num_predict": LLM_MAX_TOKENS,
            "temperature": 0.0,
            "top_p": 0.8,
        },
    }

    try:
        resp = requests.post(
            url,
            json=payload,
            timeout=OLLAMA_TIMEOUT,
            headers={"Content-Type": "application/json"},
        )
        resp.raise_for_status()
        data = resp.json()
        return data.get("message", {}).get("content", "").strip()

    except requests.exceptions.ConnectionError:
        log.info("Ollama 连接失败，使用原文")
        return None
    except requests.exceptions.Timeout:
        log.info("Ollama 请求超时 %ss，使用原文", OLLAMA_TIMEOUT)
        return None
    except Exception as e:
        log.warning("Ollama 错误: %s", e)
        return None


def check_ollama():
    """检查 Ollama 服务是否可用"""
    try:
        resp = requests.get(f"{OLLAMA_HOST}/api/tags", timeout=3)
        if resp.status_code == 200:
            data = resp.json()
            models = [m["name"] for m in data.get("models", [])]
            log.info("Ollama 已连接，可用模型: %s", models)
            return OLLAMA_MODEL in models or any(
                OLLAMA_MODEL.split(":")[0] in m for m in models
            )
        return False
    except Exception:
        return False
