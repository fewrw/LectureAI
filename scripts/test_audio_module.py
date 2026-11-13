
import wave
import time
from pathlib import Path

from audio.system_audio_capture import SystemAudioCapture


def main():
    output_dir = Path("temp")
    output_dir.mkdir(exist_ok=True)

    capture = SystemAudioCapture()

    try:
        capture.start()

        print("Устройство:", capture.device_name)
        print("Частота:", capture.sample_rate)
        print("Каналы:", capture.channels)
        print("\nЗапись 10 секунд... Включи звук.")

        chunks = []
        start_time = time.monotonic()
        duration = 10

        while time.monotonic() - start_time < duration:
            chunk = capture.get_chunk(timeout=0.1)

            if chunk is not None:
                chunks.append(chunk.data)

        print("Получено сегментов:", len(chunks))

        capture.stop()

        output_file = output_dir / "module_test.wav"

        with wave.open(str(output_file), "wb") as wav:
            wav.setnchannels(capture.channels)
            wav.setsampwidth(2)
            wav.setframerate(capture.sample_rate)
            wav.writeframes(b"".join(chunks))

        print("\nФайл сохранён:", output_file.resolve())
        print("Пропущено сегментов:", capture.dropped_chunks)

    except Exception as error:
        print("Ошибка:", repr(error))

    finally:
        capture.stop()


if __name__ == "__main__":
    main()
