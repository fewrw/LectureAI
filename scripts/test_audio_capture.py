import pyaudiowpatch as pyaudio
import wave
from pathlib import Path


DURATION = 10
OUTPUT_DIR = Path("temp")
OUTPUT_FILE = OUTPUT_DIR / "audio_test.wav"


def main():
    OUTPUT_DIR.mkdir(exist_ok=True)

    audio = pyaudio.PyAudio()

    try:
        # Получаем текущее устройство вывода Windows
        wasapi = audio.get_host_api_info_by_type(
            pyaudio.paWASAPI
        )

        output_device = audio.get_device_info_by_index(
            wasapi["defaultOutputDevice"]
        )

        output_name = output_device["name"]

        print(f"Устройство вывода: {output_name}")

        # Ищем соответствующее loopback-устройство
        loopback_device = None

        for device in audio.get_loopback_device_info_generator():
            if output_name.casefold() in device["name"].casefold():
                loopback_device = device
                break

        if loopback_device is None:
            raise RuntimeError(
                "Не найдено loopback-устройство для текущего вывода."
            )

        print(f"Захват: {loopback_device['name']}")

        channels = loopback_device["maxInputChannels"]
        sample_rate = int(loopback_device["defaultSampleRate"])

        stream = audio.open(
            format=pyaudio.paInt16,
            channels=channels,
            rate=sample_rate,
            input=True,
            input_device_index=loopback_device["index"],
            frames_per_buffer=1024
        )

        print(f"\nЗапись {DURATION} секунд...")
        print("Включи любой звук на компьютере.")

        frames = []

        for _ in range(
            int(sample_rate / 1024 * DURATION)
        ):
            data = stream.read(
                1024,
                exception_on_overflow=False
            )
            frames.append(data)

        stream.stop_stream()
        stream.close()

        # Сохраняем WAV
        with wave.open(str(OUTPUT_FILE), "wb") as wav:
            wav.setnchannels(channels)
            wav.setsampwidth(
                audio.get_sample_size(pyaudio.paInt16)
            )
            wav.setframerate(sample_rate)
            wav.writeframes(b"".join(frames))

        print(f"\nЗапись сохранена: {OUTPUT_FILE.resolve()}")

    finally:
        audio.terminate()


if __name__ == "__main__":
    main()