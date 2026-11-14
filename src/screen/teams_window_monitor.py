
import ctypes

from ctypes import wintypes
from dataclasses import dataclass


user32 = ctypes.WinDLL("user32", use_last_error=True)


EnumWindowsProc = ctypes.WINFUNCTYPE(
    wintypes.BOOL,
    wintypes.HWND,
    wintypes.LPARAM
)


user32.EnumWindows.argtypes = [
    EnumWindowsProc,
    wintypes.LPARAM
]
user32.EnumWindows.restype = wintypes.BOOL

user32.IsWindowVisible.argtypes = [wintypes.HWND]
user32.IsWindowVisible.restype = wintypes.BOOL

user32.IsIconic.argtypes = [wintypes.HWND]
user32.IsIconic.restype = wintypes.BOOL

user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
user32.GetWindowTextLengthW.restype = ctypes.c_int

user32.GetWindowTextW.argtypes = [
    wintypes.HWND,
    wintypes.LPWSTR,
    ctypes.c_int
]
user32.GetWindowTextW.restype = ctypes.c_int


@dataclass
class TeamsWindowState:
    hwnd: int
    title: str
    is_minimized: bool


class TeamsWindowMonitor:

    def find_window(self):
        windows = []

        def callback(hwnd, _):
            if not user32.IsWindowVisible(hwnd):
                return True

            length = user32.GetWindowTextLengthW(hwnd)

            if length == 0:
                return True

            buffer = ctypes.create_unicode_buffer(length + 1)

            user32.GetWindowTextW(
                hwnd,
                buffer,
                length + 1
            )

            title = buffer.value
            normalized = title.casefold()

            if "microsoft teams" not in normalized:
                return True

            excluded_titles = (
                "компактное представление",
                "compact meeting",
                "compact view"
            )

            if any(
                word in normalized
                for word in excluded_titles
            ):
                return True

            windows.append(
                TeamsWindowState(
                    hwnd=int(hwnd),
                    title=title,
                    is_minimized=bool(
                        user32.IsIconic(hwnd)
                    )
                )
            )

            return True

        user32.EnumWindows(
            EnumWindowsProc(callback),
            0
        )

        if not windows:
            return None

        return windows[0]

    def get_state(self):
        window = self.find_window()

        if window is None:
            return "not_found"

        if window.is_minimized:
            return "minimized"

        return "normal"
