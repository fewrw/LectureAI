
import time

from datetime import datetime
from pathlib import Path

from audio.audio_recorder import AudioRecorder
from audio.audio_recovery import AudioRecovery
from audio.audio_manifest import AudioManifest


def main():
    session_dir = (
        Path("temp/audio_resume_tests")
        / datetime.now().strftime("session_%Y%m%d_%H%M%S")
    )

    session_dir.mkdir(
        parents=True,
        exist_ok=False
    )

    print("ПАПКА ТЕСТА:", session_dir)

    # ЭТАП 1. Первая запись
    print("\nЭтап 1. Записываем первую часть...")

    recorder = AudioRecorder(checkpoint_seconds=3)

    recorder.start(
        output_dir=session_dir,
        output_device_index=22
    )

    time.sleep(7)

    # ЭТАП 2. Имитируем аварийное завершение
    print("\nЭтап 2. Имитируем аварийное завершение...")

    recorder._capture.stop()
    recorder._stop_event.set()

    recorder._thread.join()
    recorder._thread = None

    old_files = sorted(
        path.name
        for path in session_dir.glob("segment_*.wav")
    )

    print("Сохранённые старые сегменты:")

    for name in old_files:
        print(" ", name)

    # ЭТАП 3. Восстанавливаем сессию
    print("\nЭтап 3. Восстанавливаем сессию...")

    recovery = AudioRecovery(
        session_dir.parent
    )

    result = recovery.recover_session(session_dir)

    print("Статус после восстановления: interrupted")
    print("Восстановлено сегментов:", result["recovered_segments"])
    print("Повреждённых сегментов:", result["invalid_segments"])

    # ЭТАП 4. Продолжаем запись
    print("\nЭтап 4. Продолжаем запись...")

    resumed_recorder = AudioRecorder()

    resumed_recorder.resume(
        session_dir=session_dir,
        output_device_index=22
    )

    print("Запись продолжается. Подожди 7 секунд...")

    time.sleep(7)

    resumed_recorder.stop()

    print("Продолжение завершено.")

    # ЭТАП 5. Проверяем результат
    print("\nЭтап 5. Проверяем итоговый журнал...")

    inspection = AudioManifest.inspect(session_dir)
    manifest = inspection["manifest"]

    new_files = sorted(
        path.name
        for path in session_dir.glob("segment_*.wav")
    )

    print("\nСтарые файлы сохранились:")

    for name in old_files:
        print(
            name,
            "OK" if name in new_files else "ОТСУТСТВУЕТ"
        )

    print("\nВсе сегменты:")

    for segment in manifest["segments"]:
        print(
            segment["file"],
            "|",
            segment["duration_seconds"],
            "секунд"
        )

    total_duration = (
        manifest["total_frames"]
        / manifest["sample_rate"]
    )

    print("\nИТОГ:")
    print("Статус:", manifest["status"])
    print("Всего сегментов:", len(manifest["segments"]))
    print("Корректных:", len(inspection["valid_segments"]))
    print("Повреждённых:", len(inspection["invalid_segments"]))
    print("Общая длительность:", round(total_duration, 2), "секунд")
    print("Потерянных блоков:", manifest["dropped_chunks"])

    assert manifest["status"] == "completed"
    assert len(inspection["invalid_segments"]) == 0
    assert len(old_files) > 0
    assert all(name in new_files for name in old_files)
    assert len(new_files) > len(old_files)

    print("\nТЕСТ УСПЕШНО ПРОЙДЕН!")


if __name__ == "__main__":
    main()
