
import sys
import time
from pathlib import Path

import cv2

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from screen.system_screen_capture import SystemScreenCapture
from screen.teams_window_monitor import TeamsWindowMonitor
from screen.screen_change_detector import ScreenChangeDetector


def main():
    output_dir = (
        PROJECT_ROOT / "temp" / "screen_pipeline_events"
    )
    output_dir.mkdir(parents=True, exist_ok=True)

    monitor = TeamsWindowMonitor()
    detector = ScreenChangeDetector()
    capture = SystemScreenCapture()

    duration = 45
    frames = 0
    changes = 0

    window = monitor.find_window()

    if window is None:
        print("Главное окно Teams не найдено.")
        return

    print(f"Окно: {window.title}")
    print("Тест: 45 секунд.")
    print(f"Кадры сохраняются в: {output_dir}\n")

    start = time.monotonic()

    try:
        capture.start(window_name="Teams")

        while time.monotonic() - start < duration:
            if capture.error is not None:
                raise RuntimeError(capture.error)

            if capture.is_closed:
                raise RuntimeError(
                    "Сессия захвата завершена Windows."
                )

            frame = capture.get_frame(timeout=0.5)

            if frame is None:
                continue

            frames += 1

            if detector.has_changed(frame.image):
                changes += 1
                elapsed = time.monotonic() - start

                filename = (
                    f"event_{changes:03d}_"
                    f"{elapsed:.1f}s.png"
                )

                path = output_dir / filename

                success = cv2.imwrite(
                    str(path),
                    frame.image
                )

                print(
                    f"[{elapsed:.1f} сек.] "
                    f"Изменение #{changes}, "
                    f"{detector.last_change_ratio:.2%}, "
                    f"сохранено: {success}"
                )

        print("\n========== РЕЗУЛЬТАТ ==========")
        print(f"Кадров: {frames}")
        print(f"Изменений: {changes}")
        print(f"Пропущено кадров: {capture.dropped_frames}")

    finally:
        capture.stop()
        print("Захват остановлен.")


if __name__ == "__main__":
    main()
