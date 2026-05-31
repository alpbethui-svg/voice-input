"""
悬浮提示窗口 — 显示输入助手状态
"""

import threading
import tkinter as tk

from config import (
    APP_NAME,
    HOTKEY_DISPLAY,
    OCR_HOTKEY_DISPLAY,
    OVERLAY_WIDTH,
    OVERLAY_HEIGHT,
    OVERLAY_ALPHA,
    OVERLAY_BG,
    OVERLAY_FG,
    OVERLAY_ACCENT,
    OVERLAY_ERROR,
    OVERLAY_FONT,
    OVERLAY_POSITION,
)


class OverlayWindow:
    """半透明悬浮提示窗口"""

    def __init__(self):
        self._root = None
        self._label = None
        self._sub_label = None
        self._ready = threading.Event()

    def start(self):
        """启动 tkinter 主循环（阻塞，需在主线程调用）"""
        self._root = tk.Tk()
        self._root.title(f"{APP_NAME}-overlay")
        self._root.overrideredirect(True)  # 无边框
        self._root.attributes("-topmost", True)
        self._root.attributes("-alpha", OVERLAY_ALPHA)
        self._root.configure(bg=OVERLAY_BG)

        # 窗口尺寸
        self._root.geometry(f"{OVERLAY_WIDTH}x{OVERLAY_HEIGHT}+{self._x()}+{self._y()}")

        # 主标签
        self._label = tk.Label(
            self._root,
            text="",
            font=OVERLAY_FONT,
            bg=OVERLAY_BG,
            fg=OVERLAY_FG,
            wraplength=OVERLAY_WIDTH - 20,
        )
        self._label.pack(expand=True, pady=(15, 0))

        # 副标签（显示提示文本）
        self._sub_label = tk.Label(
            self._root,
            text="",
            font=("Microsoft YaHei UI", 9),
            bg=OVERLAY_BG,
            fg="#6c7086",
        )
        self._sub_label.pack(pady=(0, 10))

        self._root.withdraw()  # 初始隐藏
        self._ready.set()
        self._root.mainloop()

    def _x(self):
        """计算窗口 X 坐标"""
        screen_w = self._root.winfo_screenwidth()
        return (screen_w - OVERLAY_WIDTH) // 2

    def _y(self):
        """计算窗口 Y 坐标"""
        screen_h = self._root.winfo_screenheight()
        if OVERLAY_POSITION == "bottom":
            return screen_h - OVERLAY_HEIGHT - 120
        elif OVERLAY_POSITION == "top":
            return 60
        else:  # center
            return (screen_h - OVERLAY_HEIGHT) // 2

    def show_recording(self):
        """显示录音中"""
        self._wait_ready()
        if self._root:
            self._root.after(0, self._show_recording_ui)

    def _show_recording_ui(self):
        self._label.config(text="🎤 正在聆听...", fg=OVERLAY_ACCENT)
        self._sub_label.config(text=f"松开 {HOTKEY_DISPLAY} 的 Alt 结束录音")
        self._root.deiconify()
        self._root.lift()

    def show_processing(self, text=""):
        """显示处理中"""
        self._wait_ready()
        if self._root:
            self._root.after(0, lambda: self._show_processing_ui(text))

    def _show_processing_ui(self, text):
        self._label.config(text="⏳ 识别中...", fg=OVERLAY_FG)
        if text:
            self._sub_label.config(text=text)
        self._root.deiconify()
        self._root.lift()

    def show_result(self, text, duration_ms=1500):
        """显示结果并自动隐藏（兼容旧接口）"""
        self._wait_ready()
        if self._root:
            self._root.after(0, lambda: self._show_result_both_ui("", text, duration_ms))

    def show_result_both(self, raw_text, polished_text, duration_ms=2500):
        """显示原始转写 + LLM纠错后的对比"""
        self._wait_ready()
        if self._root:
            self._root.after(
                0, lambda: self._show_result_both_ui(raw_text, polished_text, duration_ms)
            )

    def _show_result_both_ui(self, raw_text, polished_text, duration_ms):
        # 主标签：纠错后文字（绿色）
        polished_display = polished_text[:40] + "..." if len(polished_text) > 40 else polished_text
        self._label.config(text=f"✓ {polished_display}", fg="#a6e3a1")

        # 副标签：原始 Whisper 输出（灰色，用于对比）
        if raw_text and raw_text != polished_text:
            raw_display = raw_text[:50] + "..." if len(raw_text) > 50 else raw_text
            self._sub_label.config(text=f"原始: {raw_display}", fg="#6c7086")
        else:
            self._sub_label.config(text="文字已输入", fg="#6c7086")

        self._root.deiconify()
        self._root.lift()
        self._root.after(duration_ms, self._root.withdraw)

    def select_region(self, on_selected):
        """显示全屏拖选层，选中后回调 (left, top, right, bottom)，取消则回调 None。"""
        self._wait_ready()
        if self._root:
            self._root.after(0, lambda: self._select_region_ui(on_selected))

    def _select_region_ui(self, on_selected):
        self._root.withdraw()

        selector = tk.Toplevel(self._root)
        selector.title("voice-input-ocr-selector")
        selector.attributes("-topmost", True)
        selector.attributes("-alpha", 0.25)
        selector.overrideredirect(True)
        selector.configure(bg="black")
        selector.geometry(
            f"{selector.winfo_screenwidth()}x{selector.winfo_screenheight()}+0+0"
        )
        selector.config(cursor="crosshair")

        canvas = tk.Canvas(selector, bg="black", highlightthickness=0)
        canvas.pack(fill="both", expand=True)
        tip = canvas.create_text(
            20,
            20,
            anchor="nw",
            text=f"{OCR_HOTKEY_DISPLAY} OCR：拖选文字区域，Esc 取消",
            fill="white",
            font=("Microsoft YaHei UI", 14),
        )

        state = {"start": None, "rect": None}

        def finish(region):
            try:
                selector.destroy()
            finally:
                on_selected(region)

        def on_down(event):
            state["start"] = (event.x_root, event.y_root)
            if state["rect"]:
                canvas.delete(state["rect"])
            state["rect"] = canvas.create_rectangle(
                event.x,
                event.y,
                event.x,
                event.y,
                outline="#ffd60a",
                width=5,
            )

        def on_move(event):
            if not state["start"] or not state["rect"]:
                return
            x0, y0 = state["start"]
            canvas.coords(
                state["rect"],
                x0 - selector.winfo_rootx(),
                y0 - selector.winfo_rooty(),
                event.x,
                event.y,
            )

        def on_up(event):
            if not state["start"]:
                finish(None)
                return
            x0, y0 = state["start"]
            x1, y1 = event.x_root, event.y_root
            left, right = sorted((int(x0), int(x1)))
            top, bottom = sorted((int(y0), int(y1)))
            if right - left < 8 or bottom - top < 8:
                finish(None)
                return
            finish((left, top, right, bottom))

        selector.bind("<Escape>", lambda event: finish(None))
        canvas.bind("<ButtonPress-1>", on_down)
        canvas.bind("<B1-Motion>", on_move)
        canvas.bind("<ButtonRelease-1>", on_up)
        selector.focus_force()

    def show_error(self, message="出错了"):
        """显示错误"""
        self._wait_ready()
        if self._root:
            self._root.after(0, lambda: self._show_error_ui(message))

    def _show_error_ui(self, message):
        self._label.config(text=f"✗ {message}", fg=OVERLAY_ERROR)
        self._sub_label.config(text="")
        self._root.deiconify()
        self._root.lift()
        self._root.after(2000, self._root.withdraw)

    def hide(self):
        """隐藏窗口"""
        self._wait_ready()
        if self._root:
            self._root.after(0, self._root.withdraw)

    def _wait_ready(self):
        """等待初始化完成"""
        if self._root:
            return
        self._ready.wait(timeout=3)

    def quit(self):
        """退出 tkinter"""
        if self._root:
            self._root.after(0, self._root.quit)
