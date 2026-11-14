
import ctypes
import time

from ctypes import wintypes


user32 = ctypes.WinDLL("user32", use_last_error=True)

EnumWindowsProc = ctypes.WINFUNCTYPE(
    wintypes.BOOL,
    wintypes.HWND,
    wintypes.LPARAM
)

user32.EnumWindows.argtypes = [EnumWindowsProc, wintypes.LPARAM]
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


def find_main_teams_window():
    result = []

    def callback(hwnd, _):
        if not user32.IsWindowVisible(hwnd):
            return True

        length = user32.GetWindowTextLengthW(hwnd)

        if length == 0:
            return True

        buffer = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buffer, length + 1)

        title = buffer.value
        normalized = title.casefold()

        if "microsoft teams" not in normalized:
            return True

        if "компактное представление" in normalized:
            return True

        result.append({
            "hwnd": int(hwnd),
            "title": title,
            "minimized": bool(user32.IsIconic(hwnd))
        })

        return True

    user32.EnumWindows(EnumWindowsProc(callback), 0)

    return result


def main():
    print("Мониторинг основного окна Teams.")
    print("Тест длится 40 секунд.")
    print("Сворачивай и разворачивай Teams.\n")

    previous_state = None

    for second in range(40):
        windows = find_main_teams_window()

        if not windows:
            state = "ОКНО НЕ НАЙДЕНО"
            hwnd = None
        else:
            window = windows[0]
            hwnd = window["hwnd"]

            state = (
                "СВЁРНУТО"
                if window["minimized"]
                else "НЕ СВЁРНУТО"
            )

        current_state = (hwnd, state)

        if current_state != previous_state:
            print(
                f"[{second:02d} сек.] {state}"
                + (f" | HWND: {hwnd:#x}" if hwnd else "")
            )

            previous_state = current_state

        time.sleep(1)


if __name__ == "__main__":
    main()
