
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from screen.system_screen_capture import SystemScreenCapture
from screen.participant_motion_detector import (
    ParticipantMotionDetector,
)


def main():
    capture = SystemScreenCapture()
    detector = ParticipantMotionDetector()

    duration = 45
    frames_received = 0
    last_report = 0

    print("Запускаем анализ движения в Teams.")
    print("Продолжительность: 45 секунд.\n")

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

            frames_received += 1

            regions = detector.update(frame.image)

            elapsed = time.monotonic() - start

            if elapsed - last_report >= 2:
                last_report = elapsed

                print(
                    f"\n[{elapsed:.1f} сек.] "
                    f"Кадр №{frames_received}"
                )

                if not regions:
                    print("Движущиеся области не обнаружены.")
                    continue

                for index, region in enumerate(regions, 1):
                    x = region.x / 320 * 100
                    y = region.y / 180 * 100
                    width = region.width / 320 * 100
                    height = region.height / 180 * 100

                    print(
                        f"Область {index}: "
                        f"X={x:.1f}%, "
                        f"Y={y:.1f}%, "
                        f"W={width:.1f}%, "
                        f"H={height:.1f}%, "
                        f"активность={region.activity:.2f}"
                    )

        print("\n========== РЕЗУЛЬТАТ ==========")
        print(f"Получено кадров: {frames_received}")
        print(f"Пропущено кадров: {capture.dropped_frames}")

    finally:
        capture.stop()
        print("Захват остановлен.")


if __name__ == "__main__":
    main()
