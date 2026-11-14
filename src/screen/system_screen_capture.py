
import queue
import threading
import time

from dataclasses import dataclass
from datetime import datetime, timezone

import numpy as np
from windows_capture import WindowsCapture


@dataclass
class ScreenFrame:
    image: np.ndarray
    captured_at: str
    monotonic_at: float
    width: int
    height: int
    timespan: int


class SystemScreenCapture:

    def __init__(self, queue_size=2):
        self._capture = None
        self._control = None

        self._frames = queue.Queue(maxsize=queue_size)
        self._closed_event = threading.Event()

        self._error = None
        self._dropped_frames = 0

    @property
    def is_running(self):
        return (
            self._control is not None
            and not self._control.is_finished()
        )

    @property
    def is_closed(self):
        return self._closed_event.is_set()

    @property
    def error(self):
        return self._error

    @property
    def dropped_frames(self):
        return self._dropped_frames

    def start(self, window_name="Teams"):
        if self.is_running:
            raise RuntimeError("Захват экрана уже запущен")

        self._error = None
        self._dropped_frames = 0
        self._closed_event.clear()

        while not self._frames.empty():
            try:
                self._frames.get_nowait()
            except queue.Empty:
                break

        self._capture = WindowsCapture(
            cursor_capture=False,
            draw_border=False,
            secondary_window=True,
            minimum_update_interval=250,
            window_name=window_name,
        )

        @self._capture.event
        def on_frame_arrived(frame, capture_control):
            try:
                monotonic_at = time.monotonic()

                image = frame.frame_buffer.copy()

                screen_frame = ScreenFrame(
                    image=image,
                    captured_at=datetime.now(
                        timezone.utc
                    ).isoformat(),
                    monotonic_at=monotonic_at,
                    width=frame.width,
                    height=frame.height,
                    timespan=frame.timespan,
                )

                if self._frames.full():
                    try:
                        self._frames.get_nowait()
                        self._dropped_frames += 1
                    except queue.Empty:
                        pass

                self._frames.put_nowait(screen_frame)

            except Exception as error:
                self._error = error
                capture_control.stop()

        @self._capture.event
        def on_closed():
            self._closed_event.set()

        self._control = self._capture.start_free_threaded()

    def get_frame(self, timeout=1.0):
        try:
            return self._frames.get(timeout=timeout)
        except queue.Empty:
            return None

    def stop(self):
        if self._control is None:
            return

        try:
            self._control.stop()
            self._control.wait()
        finally:
            self._control = None
            self._capture = None
            self._closed_event.set()
