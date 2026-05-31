"""
输入助手 — 主入口
Alt+3 语音输入；Alt+4 区域截图 OCR。

用法: pythonw voice_input.pyw  (后台运行，无控制台窗口)
      系统托盘会有图标，按 Alt+3 语音输入，按 Alt+4 OCR
"""

import ctypes
import logging
from logging.handlers import RotatingFileHandler
import os
import subprocess
import sys
import threading
import time
import traceback

try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    pass

from pynput.keyboard import Key, Listener, Controller as KBController

from config import (
    APP_NAME,
    CLIPBOARD_READY_TIMEOUT,
    HOTKEY_CHAR,
    HOTKEY_DISPLAY,
    HOTKEY_VK,
    OCR_ALT_HOTKEY_CHAR,
    OCR_ALT_HOTKEY_VK,
    OCR_HOTKEY_CHAR,
    OCR_HOTKEY_DISPLAY,
    OCR_HOTKEY_VK,
    RESTORE_CLIPBOARD,
    LOG_BACKUP_COUNT,
    LOG_MAX_BYTES,
)

# --- 日志 (自动轮转，避免无限增长) ---
LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "input_helper.log")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        RotatingFileHandler(
            LOG_FILE,
            maxBytes=LOG_MAX_BYTES,
            backupCount=LOG_BACKUP_COUNT,
            encoding="utf-8-sig",
        ),
    ],
)
log = logging.getLogger("input_helper")


# ============================================================
# 剪贴板 + 粘贴
# ============================================================
def _set_clipboard_win32(text):
    """Win32 API 后备方案"""
    CF_UNICODETEXT = 13
    GMEM_MOVEABLE = 0x0002

    if not ctypes.windll.user32.OpenClipboard(0):
        return False

    try:
        ctypes.windll.user32.EmptyClipboard()
        wbuf = ctypes.create_unicode_buffer(text)
        size = ctypes.sizeof(wbuf)
        h_mem = ctypes.windll.kernel32.GlobalAlloc(GMEM_MOVEABLE, size)
        if not h_mem:
            return False
        dst = ctypes.windll.kernel32.GlobalLock(h_mem)
        if not dst:
            return False
        ctypes.windll.kernel32.RtlMoveMemory(dst, ctypes.addressof(wbuf), size)
        ctypes.windll.kernel32.GlobalUnlock(h_mem)
        ctypes.windll.user32.SetClipboardData(CF_UNICODETEXT, h_mem)
        return True
    finally:
        ctypes.windll.user32.CloseClipboard()


def _press_ctrl_v():
    kb = KBController()
    try:
        kb.press(Key.ctrl)
        time.sleep(0.02)
        kb.press("v")
        time.sleep(0.02)
        kb.release("v")
        time.sleep(0.02)
    finally:
        kb.release(Key.ctrl)


def copy_to_clipboard(text):
    """只复制到剪贴板，不自动粘贴。"""
    if not text:
        return False
    try:
        import pyperclip
        pyperclip.copy(text)
        return True
    except Exception as e:
        log.warning("pyperclip 失败: %s", e)
        return _set_clipboard_win32(text)


def type_text(text):
    """将文本粘贴到当前光标位置，并尽量恢复用户原剪贴板。"""
    if not text:
        return

    log.info("输入: %s", text[:50])
    previous_clipboard = None
    clipboard_set = False

    try:
        import pyperclip

        try:
            previous_clipboard = pyperclip.paste()
        except Exception:
            previous_clipboard = None

        pyperclip.copy(text)
        deadline = time.time() + CLIPBOARD_READY_TIMEOUT
        while time.time() < deadline:
            try:
                if pyperclip.paste() == text:
                    clipboard_set = True
                    break
            except Exception:
                break
            time.sleep(0.02)

        if not clipboard_set:
            log.warning("剪贴板未确认写入，仍尝试粘贴")

    except Exception as e:
        log.warning("pyperclip 失败: %s", e)
        if not _set_clipboard_win32(text):
            log.error("剪贴板写入失败")
            return

    _press_ctrl_v()

    if RESTORE_CLIPBOARD and previous_clipboard is not None:
        try:
            time.sleep(0.2)
            import pyperclip
            pyperclip.copy(previous_clipboard)
        except Exception as e:
            log.debug("恢复剪贴板失败: %s", e)


# ============================================================
# 系统托盘图标
# ============================================================
def _create_tray_icon(color="blue"):
    """用 Pillow 画一个简笔麦克风图标"""
    from PIL import Image, ImageDraw
    size = 64
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    colors = {
        "blue": (137, 180, 250),
        "green": (166, 227, 161),
        "red": (243, 139, 168),
        "gray": (108, 112, 134),
    }
    c = colors.get(color, colors["blue"])

    draw.rounded_rectangle([22, 8, 42, 36], radius=8, fill=c)
    draw.arc([14, 34, 50, 58], start=220, end=320, fill=c, width=6)
    draw.line([(22, 52), (42, 52)], fill=c, width=5)
    draw.line([(32, 48), (32, 58)], fill=c, width=5)

    return img


def _open_model_setup():
    """打开模型准备窗口，不把大模型内置进安装包。"""
    try:
        if getattr(sys, "frozen", False):
            cmd = [sys.executable, "--model-setup"]
        else:
            cmd = [sys.executable, os.path.abspath(__file__), "--model-setup"]
        subprocess.Popen(cmd, cwd=os.path.dirname(os.path.abspath(__file__)))
    except Exception as e:
        log.warning("打开模型准备窗口失败: %s", e)


def _setup_tray(stop_callback):
    """创建系统托盘（运行在独立线程）"""
    import pystray

    def on_model_setup(icon, item):
        _open_model_setup()

    def on_exit(icon, item):
        log.info("用户从托盘退出")
        stop_callback()
        icon.stop()

    menu = pystray.Menu(
        pystray.MenuItem(f"{APP_NAME}", None, enabled=False),
        pystray.MenuItem(f"🎤 语音 {HOTKEY_DISPLAY}", None, enabled=False),
        pystray.MenuItem(f"🔍 OCR {OCR_HOTKEY_DISPLAY}", None, enabled=False),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("模型准备/检查", on_model_setup),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("退出", on_exit),
    )

    icon = pystray.Icon(
        "input_helper",
        _create_tray_icon("blue"),
        f"{APP_NAME}\n{HOTKEY_DISPLAY} 说话 / {OCR_HOTKEY_DISPLAY} OCR",
        menu,
    )

    icon.run()


# ============================================================
# 热键
# ============================================================
def _is_voice_hotkey(key):
    if hasattr(key, "vk") and key.vk == HOTKEY_VK:
        return True
    if hasattr(key, "char") and key.char == HOTKEY_CHAR:
        return True
    return False


def _is_ocr_hotkey(key):
    if hasattr(key, "vk") and key.vk == OCR_HOTKEY_VK:
        return True
    if hasattr(key, "char") and key.char == OCR_HOTKEY_CHAR:
        return True
    return False


def _is_ocr_alt_hotkey(key):
    if hasattr(key, "vk") and key.vk == OCR_ALT_HOTKEY_VK:
        return True
    if hasattr(key, "char") and key.char and key.char.lower() == OCR_ALT_HOTKEY_CHAR:
        return True
    return False


# ============================================================
# 主应用
# ============================================================
class AppState:
    IDLE = "idle"
    RECORDING = "recording"
    PROCESSING = "processing"
    OCR_SELECTING = "ocr_selecting"
    OCR_PROCESSING = "ocr_processing"


class VoiceInputApp:
    def __init__(self):
        self.state = AppState.IDLE
        self.recorder = None
        self.overlay = None
        self._hotkey_listener = None
        self._alt_held = False
        self._hotkey_armed = False
        self._ctrl_held = False
        self._state_lock = threading.Lock()

    def run(self):
        log.info("%s v1.6 启动 (%s 语音 / %s OCR)", APP_NAME, HOTKEY_DISPLAY, OCR_HOTKEY_DISPLAY)

        from recorder import AudioRecorder
        self.recorder = AudioRecorder()

        from overlay import OverlayWindow
        self.overlay = OverlayWindow()

        t = threading.Thread(target=self._start_hotkey, daemon=True)
        t.start()

        tray_thread = threading.Thread(
            target=_setup_tray, args=(self.shutdown,), daemon=True
        )
        tray_thread.start()

        # 不在启动时自动预下载/预加载 Whisper，避免安装后立刻拉取大模型。
        # 需要时可从托盘“模型准备/检查”手动预热，或首次语音输入时再加载。

        try:
            self.overlay.start()
        except KeyboardInterrupt:
            pass
        finally:
            self._cleanup()

    def shutdown(self):
        """外部关闭（托盘退出）"""
        if self.overlay:
            self.overlay.quit()

    def _start_hotkey(self):
        self._hotkey_listener = Listener(
            on_press=self._on_key_press, on_release=self._on_key_release
        )
        self._hotkey_listener.start()
        log.info("热键就绪: %s 语音 / %s OCR", HOTKEY_DISPLAY, OCR_HOTKEY_DISPLAY)
        self._hotkey_listener.join()

    def _on_key_press(self, key):
        if key in (Key.alt, Key.alt_l, Key.alt_r):
            self._alt_held = True
            return
        if key in (Key.ctrl, Key.ctrl_l, Key.ctrl_r):
            self._ctrl_held = True
            return

        if not self._alt_held:
            return

        if _is_voice_hotkey(key) and not self._ctrl_held:
            should_start = False
            with self._state_lock:
                if not self._hotkey_armed and self.state == AppState.IDLE:
                    self._hotkey_armed = True
                    self.state = AppState.RECORDING
                    should_start = True

            if should_start:
                self._start_recording()
            return

        if _is_ocr_hotkey(key) or (self._ctrl_held and _is_ocr_alt_hotkey(key)):
            should_start = False
            with self._state_lock:
                if self.state == AppState.IDLE:
                    self.state = AppState.OCR_SELECTING
                    should_start = True

            if should_start:
                self._start_ocr_selection()

    def _on_key_release(self, key):
        if key in (Key.ctrl, Key.ctrl_l, Key.ctrl_r):
            self._ctrl_held = False
            return
        if key in (Key.alt, Key.alt_l, Key.alt_r):
            self._alt_held = False
            self._stop_and_process()
            return

        # 松开数字 3 不停止录音；按住 Alt 说完，松开 Alt 才停止。
        # 这样避免“按一下 3 就立刻停止”导致的说话太短。

    def _preload_model(self):
        try:
            from transcriber import _get_model
            _get_model()
            log.info("Whisper 模型就绪")
        except Exception as e:
            log.warning("模型预加载: %s", e)

    def _set_idle(self):
        with self._state_lock:
            self.state = AppState.IDLE
            self._hotkey_armed = False

    def _start_recording(self):
        log.info("开始录音")
        self.overlay.show_recording()
        if not self.recorder.start():
            self.overlay.show_error("录音启动失败")
            self._set_idle()

    def _start_ocr_selection(self):
        log.info("开始 OCR 区域选择")
        self.overlay.show_processing("拖选要识别的文字区域...")
        self.overlay.select_region(self._on_ocr_region_selected)

    def _on_ocr_region_selected(self, region):
        if not region:
            log.info("OCR 已取消")
            self.overlay.show_error("已取消 OCR")
            self._set_idle()
            return

        with self._state_lock:
            self.state = AppState.OCR_PROCESSING

        log.info("OCR 区域: %s", region)
        self.overlay.show_processing("OCR 识别中...")
        threading.Thread(target=self._process_ocr, args=(region,), daemon=True).start()

    def _process_ocr(self, region):
        try:
            from ocr import ocr_region
            text = ocr_region(region)
            if not text:
                self.overlay.show_error("未识别到文字")
                self._set_idle()
                return

            log.info("OCR: %s", text[:120])
            if copy_to_clipboard(text):
                self.overlay.show_result(f"OCR 已复制: {text}", duration_ms=2500)
            else:
                self.overlay.show_error("剪贴板写入失败")
            self._set_idle()
        except Exception as e:
            log.error("OCR 失败: %s\n%s", e, traceback.format_exc())
            self.overlay.show_error("OCR 失败")
            self._set_idle()

    def _stop_and_process(self):
        with self._state_lock:
            if self.state != AppState.RECORDING:
                return
            self.state = AppState.PROCESSING
            self._hotkey_armed = False

        log.info("停止录音")
        audio = self.recorder.stop()
        if audio is None or len(audio) < 1600:
            self.overlay.show_error("说话太短")
            self._set_idle()
            return

        log.info("录音 %.1fs, %d 样本", len(audio) / 16000, len(audio))
        threading.Thread(target=self._process_audio, args=(audio,), daemon=True).start()

    def _process_audio(self, audio):
        try:
            self.overlay.show_processing("Whisper 转写中...")
            from transcriber import transcribe
            raw_text = transcribe(audio)
            if not raw_text or not raw_text.strip():
                self.overlay.show_error("未能识别")
                self._set_idle()
                return

            log.info("Whisper: %s", raw_text)

            self.overlay.show_processing("保守纠错中...")
            from polisher import polish
            final = polish(raw_text) or raw_text

            log.info("最终: %s", final)
            type_text(final)
            self.overlay.show_result_both(raw_text, final)
            self._set_idle()
        except Exception as e:
            log.error("处理失败: %s\n%s", e, traceback.format_exc())
            self.overlay.show_error(str(e)[:40])
            self._set_idle()

    def _cleanup(self):
        log.info("退出")
        if self._hotkey_listener:
            self._hotkey_listener.stop()


if __name__ == "__main__":
    if "--model-setup" in sys.argv:
        from model_setup import run_model_setup
        run_model_setup()
    else:
        app = VoiceInputApp()
        app.run()

