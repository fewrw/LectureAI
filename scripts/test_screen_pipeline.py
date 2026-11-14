
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from screen.system_screen_capture import SystemScreenCapture
from screen.teams_window_monitor import TeamsWindowMonitor
from screen.screen_change_detector import ScreenChangeDetector


def main():
    monitor = TeamsWindowMonitor()
    detector = ScreenChangeDetector()
    capture = SystemScreenCapture()

    duration = 45
    frames_received = 0
    changes_detected = 0
    previous_state = None

    window = monitor.find_window()

    if window is None:
        print("ОШИБКА: главное окно Teams не найдено.")
        return

    print(f"Окно: {window.title}")
    print(f"Свёрнуто: {window.is_minimized}")
    print("Запускаем интеграционный тест на 45 секунд.\n")

    start_time = time.monotonic()
    last_state_check = 0

    try:
        capture.start(window_name="Teams")

        while time.monotonic() - start_time < duration:
            elapsed = time.monotonic() - start_time

            if capture.error is not None:
                raise RuntimeError(capture.error)

            if capture.is_closed:
                raise RuntimeError(
                    "Windows завершила сессию захвата."
                )

            if elapsed - last_state_check >= 0.5:
                window = monitor.find_window()

                if window is None:
                    state = "not_found"
                elif window.is_minimized:
                    state = "minimized"
                else:
                    state = "normal"

                if state != previous_state:
                    print(
                        f"[{elapsed:.1f} сек.] "
                        f"Состояние Teams: {state}"
                    )
                    previous_state = state

                last_state_check = elapsed

            frame = capture.get_frame(timeout=0.2)

            if frame is None:
                continue

            frames_received += 1

            if detector.has_changed(frame.image):
                changes_detected += 1

                print(
                    f"[{elapsed:.1f} сек.] "
                    f"Изменение изображения №{changes_detected} "
                    f"(кадр №{frames_received}, "
                    f"изменение: "
                    f"{detector.last_change_ratio:.2%})"
                )

        print("\n========== РЕЗУЛЬТАТ ==========")
        print(f"Получено кадров: {frames_received}")
        print(f"Обнаружено изменений: {changes_detected}")
        print(f"Пропущено кадров: {capture.dropped_frames}")

    finally:
        capture.stop()
        print("Захват остановлен.")


if __name__ == "__main__":
    main()
