"""
区域截图 OCR 模块 — 使用 RapidOCR。
"""

import logging
import os
import re
import tempfile
import threading

from PIL import Image, ImageEnhance, ImageFilter, ImageGrab

from config import (
    OCR_CONTRAST,
    OCR_IMAGE_SCALE,
    OCR_MIN_CONFIDENCE,
    OCR_SHARPNESS,
)

log = logging.getLogger("input_helper.ocr")

_engine = None
_engine_lock = threading.Lock()


def _get_engine():
    """懒加载 RapidOCR 引擎，避免每次截图都重新加载模型。"""
    global _engine
    if _engine is not None:
        return _engine

    with _engine_lock:
        if _engine is not None:
            return _engine

        from rapidocr import RapidOCR

        _engine = RapidOCR()
        log.info("RapidOCR 引擎已就绪")
        return _engine


def ocr_region(region):
    """截图指定屏幕区域并返回 RapidOCR 识别文本。"""
    left, top, right, bottom = region
    if right <= left or bottom <= top:
        return ""

    image_path = None
    try:
        image = ImageGrab.grab(bbox=(left, top, right, bottom)).convert("RGB")

        with tempfile.NamedTemporaryFile(
            suffix=".png", prefix="input_helper_ocr_", delete=False
        ) as tmp:
            image_path = tmp.name
        _preprocess_image(image).save(image_path)

        return ocr_image(image_path, already_preprocessed=True)
    finally:
        if image_path:
            try:
                os.unlink(image_path)
            except OSError:
                pass


def ocr_image(image_path, already_preprocessed=False):
    """识别图片文件。测试用图片默认也走同一套预处理。"""
    processed_path = None
    try:
        target_path = image_path
        if not already_preprocessed:
            image = Image.open(image_path).convert("RGB")
            with tempfile.NamedTemporaryFile(
                suffix=".png", prefix="input_helper_ocr_processed_", delete=False
            ) as tmp:
                processed_path = tmp.name
            _preprocess_image(image).save(processed_path)
            target_path = processed_path

        engine = _get_engine()
        result = engine(str(target_path))
        lines = _reconstruct_lines(result)
        if not lines:
            return ""

        log.info(
            "RapidOCR 识别 %d 行，耗时 %.2fs",
            len(lines),
            getattr(result, "elapse", 0.0) or 0.0,
        )
        return _cleanup_text("\n".join(lines))
    finally:
        if processed_path:
            try:
                os.unlink(processed_path)
            except OSError:
                pass


def _preprocess_image(image):
    """放大、增强对比和锐化，小字号终端/网页截图会更稳。"""
    scale = float(OCR_IMAGE_SCALE or 1.0)
    if scale != 1.0:
        width, height = image.size
        image = image.resize(
            (max(1, int(width * scale)), max(1, int(height * scale))),
            Image.Resampling.LANCZOS,
        )

    if OCR_CONTRAST and OCR_CONTRAST != 1:
        image = ImageEnhance.Contrast(image).enhance(float(OCR_CONTRAST))
    if OCR_SHARPNESS and OCR_SHARPNESS != 1:
        image = ImageEnhance.Sharpness(image).enhance(float(OCR_SHARPNESS))

    # 轻微锐化，不做二值化，避免彩色网页/终端主题丢细节。
    return image.filter(ImageFilter.SHARPEN)


def _reconstruct_lines(result):
    raw_texts = getattr(result, "txts", None)
    raw_boxes = getattr(result, "boxes", None)
    raw_scores = getattr(result, "scores", None)
    texts = list(raw_texts) if raw_texts is not None else []
    boxes = list(raw_boxes) if raw_boxes is not None else []
    scores = list(raw_scores) if raw_scores is not None else []

    if not texts:
        return []

    if not boxes or len(boxes) != len(texts):
        return [t.strip() for t in texts if t and t.strip()]

    items = []
    for index, text in enumerate(texts):
        text = (text or "").strip()
        if not text:
            continue

        score = float(scores[index]) if index < len(scores) else 1.0
        if score < OCR_MIN_CONFIDENCE:
            continue

        box = boxes[index]
        xs = [float(point[0]) for point in box]
        ys = [float(point[1]) for point in box]
        x0, x1 = min(xs), max(xs)
        y0, y1 = min(ys), max(ys)
        items.append(
            {
                "text": text,
                "x0": x0,
                "x1": x1,
                "y0": y0,
                "y1": y1,
                "cy": (y0 + y1) / 2,
                "height": max(1.0, y1 - y0),
            }
        )

    if not items:
        return []

    items.sort(key=lambda item: (item["cy"], item["x0"]))
    groups = []
    for item in items:
        if not groups:
            groups.append([item])
            continue

        group = groups[-1]
        avg_cy = sum(i["cy"] for i in group) / len(group)
        avg_h = sum(i["height"] for i in group) / len(group)
        if abs(item["cy"] - avg_cy) <= max(10.0, avg_h * 0.65):
            group.append(item)
        else:
            groups.append([item])

    lines = []
    for group in groups:
        group.sort(key=lambda item: item["x0"])
        line = _merge_line_items(group)
        if line:
            lines.append(line)
    return lines


def _merge_line_items(items):
    text = ""
    prev = None
    for item in items:
        cur = item["text"].strip()
        if not cur:
            continue

        if not text:
            text = cur
            prev = item
            continue

        # OCR 分框重叠时，前一段末尾可能重复后一段开头，例如 log2 + 2MB。
        new_text = _remove_suffix_prefix_overlap(text, cur)
        overlap_removed = new_text != text
        text = new_text

        gap = item["x0"] - (prev["x1"] if prev else item["x0"])
        avg_h = ((prev["height"] if prev else item["height"]) + item["height"]) / 2
        if overlap_removed or _needs_space(text, cur, gap, avg_h):
            text += " "
        text += cur
        prev = item

    return text.strip()


def _remove_suffix_prefix_overlap(left, right):
    max_overlap = min(8, len(left), len(right))
    for size in range(max_overlap, 0, -1):
        if left[-size:] == right[:size]:
            return left[:-size]
    return left


def _needs_space(left, right, gap, avg_h):
    if not left or not right:
        return False
    if _is_cjk(left[-1]) and _is_cjk(right[0]):
        return False

    # 明显有横向间隔时补空格；小间隔通常是同一个 token 被拆框。
    if gap > max(6.0, avg_h * 0.22):
        return True

    # 即便框略重叠，两个英文/数字 token 合并时也通常需要空格。
    if gap > -avg_h * 0.15 and _is_token_char(left[-1]) and _is_token_char(right[0]):
        return True

    return False


def _cleanup_text(text):
    if not text:
        return ""

    lines = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        lines.append(_cleanup_codeish_line(line))
    return "\n".join(lines)


def _cleanup_codeish_line(line):
    # 仅对包含明显代码/路径/日志特征的行做保守修正，避免改坏普通中文。
    codeish = bool(re.search(r"[A-Za-z0-9_\\/$:.>\-]", line))
    if not codeish:
        return line

    replacements = {
        "INF0": "INFO",
        "[INF0]": "[INFO]",
        "Rapid0cR": "RapidOCR",
        "Rapid0CR": "RapidOCR",
        "RapidocR": "RapidOCR",
        "RapidOCR": "RapidOCR",
        "0CR": "OCR",
        "0k": "OK",
        " Ok": " OK",
        "$nuII": "$null",
        "$nulI": "$null",
        "$nuli": "$null",
        "voice—input": "voice-input",
        "input—helper": "input_helper",
        "voice—input.pyw": "voice_input.pyw",
    }
    for old, new in replacements.items():
        line = line.replace(old, new)

    # 常见 OCR 标点：只在代码/路径行里替换。
    line = line.replace("—", "-").replace("–", "-").replace("−", "-")
    line = re.sub(r"\bIog\b", "log", line)
    line = re.sub(r"\.Iog\b", ".log", line)
    line = re.sub(r"\biines\b", "lines", line)
    line = re.sub(r"\bIines\b", "lines", line)
    line = re.sub(r"\bNoProfiIe\b", "NoProfile", line)
    return line


def _is_cjk(ch):
    return "一" <= ch <= "鿿"


def _is_token_char(ch):
    return ch.isalnum() or ch in "_.$:/\\-"
