
import json
import time
import wave

from pathlib import Path

from audio.audio_recorder import AudioRecorder
from audio.audio_recovery import AudioRecovery


sessions_dir = Path("temp/recovery_test")
session_dir = sessions_dir / "test_session"

session_dir.mkdir(parents=True, exist_ok=True)

# Создаём тестовую лекцию.
recorder = AudioRecorder(checkpoint_seconds=3)

recorder.start(
    output_dir=session_dir,
    output_device_index=22
)

print("Идёт тестовая запись...")
time.sleep(7)

# Имитируем аварийное завершение:
# останавливаем только системный захват,
# не вызывая штатное завершение AudioRecorder.
recorder._capture.stop()
recorder._stop_event.set()
recorder._thread.join()
recorder._thread = None

print("Имитировано аварийное завершение.")

# Проверяем обнаружение.
recovery = AudioRecovery(sessions_dir)

incomplete = recovery.find_incomplete_sessions()

print("\nНезавершённых сессий:", len(incomplete))

for session in incomplete:
    print("Найдена:", session["path"])

# Восстанавливаем сессию.
result = recovery.recover_session(session_dir)

print("\nРезультат восстановления:")
print("Корректных сегментов:", result["recovered_segments"])
print("Повреждённых сегментов:", result["invalid_segments"])

# Проверяем итоговые файлы.
manifest_path = session_dir / "manifest.json"

with open(manifest_path, "r", encoding="utf-8") as file:
    manifest = json.load(file)

print("Новый статус:", manifest["status"])

for segment in manifest["segments"]:
    path = session_dir / segment["file"]

    with wave.open(str(path), "rb") as audio:
        print(
            path.name,
            round(
                audio.getnframes() / audio.getframerate(),
                2
            ),
            "секунд"
        )
