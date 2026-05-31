"""
录音模块 — 按下说话，松开停止
"""

import logging
import threading
import time
from collections import deque

import numpy as np
import sounddevice as sd

log = logging.getLogger("voice_input.recorder")

from config import SAMPLE_RATE, CHANNELS, MAX_RECORD_SECONDS, SILENCE_TIMEOUT


class AudioRecorder:
    """音频录制器，支持按住说话模式"""

    def __init__(self):
        self._recording = False
        self._audio_buffer = deque()
        self._thread = None
        self._stream = None
        self._on_start_callback = None
        self._on_stop_callback = None
        self._peak_callback = None
        self._buffer_lock = threading.Lock()
        self._finished = threading.Event()
        self._stop_reason = "manual"

        # 检查可用的输入设备
        self._check_device()

    def _check_device(self):
        """列出可用的录音设备"""
        devices = sd.query_devices()
        input_devices = [d for d in devices if d["max_input_channels"] > 0]
        if not input_devices:
            log.warning("没有找到录音设备!")
        else:
            default = sd.query_devices(kind="input")
            log.info("录音设备: %s, 采样率: %dHz", default["name"], SAMPLE_RATE)

    def set_callbacks(self, on_start=None, on_stop=None, on_peak=None):
        """设置状态回调"""
        self._on_start_callback = on_start
        self._on_stop_callback = on_stop
        self._peak_callback = on_peak

    def start(self):
        """开始录音"""
        if self._recording:
            return False

        with self._buffer_lock:
            self._audio_buffer.clear()

        self._stop_reason = "manual"
        self._finished.clear()
        self._recording = True
        self._thread = threading.Thread(target=self._record_loop, daemon=True)
        self._thread.start()

        if self._on_start_callback:
            self._on_start_callback()
        return True

    def stop(self):
        """停止录音，返回音频数据 (numpy array, float32, shape=(samples,))。
        即使已被最大时长自动停止，也会返回已录制的音频。
        """
        self._recording = False

        if self._thread:
            self._thread.join(timeout=3.0)
            if self._thread.is_alive():
                log.warning("录音线程未及时退出，使用当前已录音频")

        if self._on_stop_callback:
            self._on_stop_callback()

        with self._buffer_lock:
            if not self._audio_buffer:
                return None
            audio = np.concatenate(list(self._audio_buffer))

        # sounddevice 单声道也是 (N,1)，Whisper 要 1D float32
        return (audio.astype(np.float32) / 32768.0).flatten()

    def is_recording(self):
        return self._recording

    def stop_reason(self):
        return self._stop_reason

    def _record_loop(self):
        """录音循环（独立线程）"""
        try:
            self._stream = sd.InputStream(
                samplerate=SAMPLE_RATE,
                channels=CHANNELS,
                dtype="int16",
                callback=self._audio_callback,
                blocksize=1024,
            )
            self._stream.start()

            start_time = time.time()
            last_sound_time = time.time()

            while self._recording:
                time.sleep(0.05)

                elapsed = time.time() - start_time
                if elapsed > MAX_RECORD_SECONDS:
                    self._stop_reason = "max_duration"
                    log.info("达到最大录音时长，自动停止")
                    self._recording = False
                    break

                if SILENCE_TIMEOUT > 0 and hasattr(self, "_last_peak"):
                    if self._last_peak > 0.02:
                        last_sound_time = time.time()
                    elif time.time() - last_sound_time > SILENCE_TIMEOUT:
                        self._stop_reason = "silence"
                        log.info("检测到静音，自动停止")
                        self._recording = False
                        break

            self._stream.stop()
            self._stream.close()
            self._stream = None

        except Exception as e:
            log.error("录音错误: %s", e)
            self._recording = False
        finally:
            self._finished.set()

    def _audio_callback(self, indata, frames, time_info, status):
        """音频数据回调"""
        if status:
            log.debug("录音状态: %s", status)

        if self._recording:
            with self._buffer_lock:
                self._audio_buffer.append(indata.copy())

            peak = np.abs(indata).mean() / 32768.0
            self._last_peak = peak
            if self._peak_callback:
                self._peak_callback(peak)
