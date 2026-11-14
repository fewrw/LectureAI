
import struct
import wave
from pathlib import Path
from shutil import copy2


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SESSIONS_DIR = PROJECT_ROOT / "temp" / "audio_crash_tests"


def main():
    sessions = [
        path for path in SESSIONS_DIR.iterdir()
        if path.is_dir()
    ]

    session = max(sessions, key=lambda p: p.stat().st_mtime)
    source = session / "segment_000003.wav"

    output_dir = PROJECT_ROOT / "temp" / "recovered_orphans"
    output_dir.mkdir(parents=True, exist_ok=True)

    destination = output_dir / f"{session.name}_segment_000003.wav"

    copy2(source, destination)

    file_size = destination.stat().st_size

    with destination.open("r+b") as file:
        header = file.read(44)

        if len(header) != 44:
            raise RuntimeError("Слишком короткий WAV-файл")

        riff_id, riff_size, wave_id = struct.unpack(
            "<4sI4s", header[:12]
        )

        fmt_id, fmt_size = struct.unpack(
            "<4sI", header[12:20]
        )

        audio_format, channels, sample_rate, byte_rate, block_align, bits = (
            struct.unpack("<HHIIHH", header[20:36])
        )

        data_id, old_data_size = struct.unpack(
            "<4sI", header[36:44]
        )

        if riff_id != b"RIFF" or wave_id != b"WAVE":
            raise RuntimeError("Некорректный RIFF/WAVE")

        if fmt_id != b"fmt " or fmt_size != 16:
            raise RuntimeError("Неожиданная структура fmt")

        if data_id != b"data":
            raise RuntimeError("Не найден стандартный data-блок")

        if audio_format != 1:
            raise RuntimeError("Поддерживается только PCM")

        if channels <= 0 or bits not in (8, 16, 24, 32):
            raise RuntimeError("Неизвестный формат аудио")

        if block_align != channels * (bits // 8):
            raise RuntimeError("Некорректный размер кадра")

        data_size = file_size - 44

        if data_size <= 0 or data_size % block_align:
            raise RuntimeError("Размер аудиоданных некорректен")

        # Обновляем размеры RIFF и data.
        file.seek(4)
        file.write(struct.pack("<I", file_size - 8))

        file.seek(40)
        file.write(struct.pack("<I", data_size))

    print(f"Исходный файл: {source}")
    print(f"Восстановленная копия: {destination}")
    print(f"Старый размер data: {old_data_size:,}")
    print(f"Новый размер data: {data_size:,}")

    with wave.open(str(destination), "rb") as wav:
        frames = wav.getnframes()

        print("\nПроверка восстановленного WAV:")
        print(f"Каналы: {wav.getnchannels()}")
        print(f"Частота: {wav.getframerate()}")
        print(f"Кадров: {frames:,}")
        print(f"Длительность: {frames / wav.getframerate():.3f} сек.")

        read_frames = 0

        while True:
            chunk = wav.readframes(65536)
            if not chunk:
                break
            read_frames += len(chunk) // wav.getnchannels() // (
                wav.getsampwidth()
            )

        print(f"Прочитано кадров: {read_frames:,}")

        if read_frames != frames:
            raise RuntimeError("Количество прочитанных кадров не совпадает")

    print("\nВОССТАНОВЛЕНИЕ КОПИИ УСПЕШНО!")


if __name__ == "__main__":
    main()
