
import json
import time
import wave

from datetime import datetime

from audio.audio_recorder import AudioRecorder
from audio.audio_manifest import AudioManifest


session_name = datetime.now().strftime(
    "test_%Y%m%d_%H%M%S"
)

output_dir = f"temp/audio_sessions/{session_name}"

recorder = AudioRecorder(checkpoint_seconds=5)

try:
    print("Запускаем запись...")

    recorder.start(
        output_dir=output_dir,
        output_device_index=22
    )

    print("Запись идёт 17 секунд.")
    print("Включи музыку или видео.")

    time.sleep(17)

finally:
    segments = recorder.stop()
    print("Запись остановлена.")

print("\nСегменты:")

for path in segments:
    with wave.open(str(path), "rb") as audio:
        duration = (
            audio.getnframes() / audio.getframerate()
        )

        print(
            path.name,
            "|",
            round(duration, 2),
            "секунд"
        )

print("\nПроверяем журнал...")

result = AudioManifest.inspect(output_dir)

print("Статус:", result["status"])
print("Всего сегментов:", result["total_segments"])
print("Корректных:", len(result["valid_segments"]))
print("Повреждённых:", len(result["invalid_segments"]))

print("\nСодержимое manifest.json:")

with open(
    f"{output_dir}/manifest.json",
    "r",
    encoding="utf-8"
) as file:
    manifest = json.load(file)

print(json.dumps(
    manifest,
    ensure_ascii=False,
    indent=4
))

print("\nПуть:", output_dir)
