
import struct
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SESSIONS_DIR = PROJECT_ROOT / "temp" / "audio_crash_tests"


def main():
    if len(sys.argv) > 1:
        session_dir = Path(sys.argv[1])
    else:
        sessions = [
            p for p in SESSIONS_DIR.iterdir()
            if p.is_dir()
        ]
        session_dir = max(sessions, key=lambda p: p.stat().st_mtime)

    path = session_dir / "segment_000003.wav"

    with path.open("rb") as file:
        file_size = path.stat().st_size

        riff_id, riff_size, wave_id = struct.unpack(
            "<4sI4s", file.read(12)
        )

        print(f"Файл: {path}")
        print(f"Фактический размер: {file_size:,}")
        print(f"RIFF: {riff_id!r}")
        print(f"Размер RIFF по заголовку: {riff_size:,}")
        print(f"WAVE: {wave_id!r}")

        offset = 12
        data_chunk = None
        channels = None
        sample_width = None
        sample_rate = None

        while offset + 8 <= file_size:
            file.seek(offset)

            chunk_id, chunk_size = struct.unpack(
                "<4sI", file.read(8)
            )

            data_offset = offset + 8
            available = max(0, file_size - data_offset)
            actual_chunk_bytes = min(chunk_size, available)

            print(f"\nChunk: {chunk_id!r}")
            print(f"  Размер по заголовку: {chunk_size:,}")
            print(f"  Доступно в файле: {available:,}")

            if chunk_id == b"fmt ":
                file.seek(data_offset)
                fmt = file.read(min(chunk_size, 40))

                if len(fmt) >= 16:
                    audio_format, channels, sample_rate, byte_rate, block_align, bits = (
                        struct.unpack("<HHIIHH", fmt[:16])
                    )
                    sample_width = bits // 8

                    print(f"  Формат: {audio_format}")
                    print(f"  Каналы: {channels}")
                    print(f"  Частота: {sample_rate}")
                    print(f"  Разрядность: {bits}")

            elif chunk_id == b"data":
                data_chunk = {
                    "offset": data_offset,
                    "declared": chunk_size,
                    "available": available,
                }

                print("  Найден аудиоблок")

                if channels and sample_width:
                    frame_size = channels * sample_width
                    print(
                        f"  Кадров по размеру заголовка: "
                        f"{chunk_size // frame_size:,}"
                    )
                    print(
                        f"  Кадров по доступным байтам: "
                        f"{available // frame_size:,}"
                    )
                    print(
                        f"  Остаток байтов: "
                        f"{available % frame_size}"
                    )

            offset = data_offset + chunk_size + (chunk_size % 2)

        print("\n--- ИТОГ ---")

        if data_chunk:
            extra = (
                data_chunk["available"]
                - data_chunk["declared"]
            )

            print(f"Размер data по заголовку: {data_chunk['declared']:,}")
            print(f"Доступно после data-заголовка: {data_chunk['available']:,}")
            print(f"Дополнительные байты: {extra:,}")
        else:
            print("Блок data не найден.")


if __name__ == "__main__":
    main()
