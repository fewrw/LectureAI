
import sys
import time
from pathlib import Path

import cv2

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from screen.system_screen_capture import SystemScreenCapture


def main():
    output_dir = PROJECT_ROOT / "temp" / "screen_capture_test"
    output_dir.mkdir(parents=True, exist_ok=True)

    capture = SystemScreenCapture()

    duration = 60
    frame_number = 0
    start_time = time.monotonic()

    print("Запускаем захват Teams...")
    print("Тест продлится 60 секунд.")

    try:
        capture.start(window_name="Teams")

        while time.monotonic() - start_time < duration:
            if capture.error is not None:
                raise RuntimeError(
                    f"Ошибка захвата: {capture.error}"
                )

            if capture.is_closed:
                raise RuntimeError(
                    "Сессия захвата завершена Windows."
                )

            frame = capture.get_frame(timeout=0.5)

            if frame is None:
                continue

            frame_number += 1

            output_path = (
                output_dir / f"frame_{frame_number:04d}.png"
            )

            success = cv2.imwrite(
                str(output_path),
                frame.image
            )

            if success:
                elapsed = time.monotonic() - start_time
                print(
                    f"[{elapsed:.1f} сек.] "
                    f"Получен кадр №{frame_number}"
                )

        print("\nТест завершён.")
        print(f"Получено кадров: {frame_number}")
        print(f"Пропущено кадров: {capture.dropped_frames}")

    finally:
        capture.stop()
        print("Захват остановлен.")


if __name__ == "__main__":
    main()
