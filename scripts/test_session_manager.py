
import sys
import time

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from core.session_manager import SessionManager


def main():
    output_dir = (
        PROJECT_ROOT
        / "temp"
        / "session_manager_test"
    )

    manager = SessionManager(
        checkpoint_seconds=5,
        screen_sample_interval=2,
    )

    print("Запускаем общую сессию LectureAI.")

    try:
        manager.start(
            session_dir=output_dir,
            window_name="Teams",
        )

        print(f"Статус: {manager.status}")
        print(f"Экран: {manager.screen_status}")

        print("\nСессия работает 20 секунд.")

        for second in range(20):
            time.sleep(1)

            if manager.audio.error is not None:
                raise RuntimeError(manager.audio.error)

            if second % 5 == 4:
                print(manager.get_statistics())

        manager.stop()

        print("\nСессия завершена.")
        print(manager.get_statistics())

    except Exception as error:
        print(f"\nОШИБКА: {error}")

        if manager.is_running:
            manager.stop()


if __name__ == "__main__":
    main()
