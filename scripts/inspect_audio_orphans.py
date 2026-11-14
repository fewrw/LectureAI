
import sys
import json
import wave
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SESSIONS_DIR = PROJECT_ROOT / "temp" / "audio_crash_tests"


def find_session():
    if len(sys.argv) > 1:
        return Path(sys.argv[1]).resolve()

    sessions = [
        path for path in SESSIONS_DIR.iterdir()
        if path.is_dir()
    ] if SESSIONS_DIR.exists() else []

    if not sessions:
        raise FileNotFoundError(
            f"Тестовые сессии не найдены: {SESSIONS_DIR}"
        )

    return max(sessions, key=lambda path: path.stat().st_mtime)


def extract_wav_paths(value):
    """Ищет пути к WAV-файлам внутри структуры manifest."""
    result = []

    if isinstance(value, dict):
        for item in value.values():
            result.extend(extract_wav_paths(item))

    elif isinstance(value, list):
        for item in value:
            result.extend(extract_wav_paths(item))

    elif isinstance(value, str) and value.lower().endswith(".wav"):
        result.append(value)

    return result


def inspect_wav(path):
    print(f"\nФайл: {path.name}")
    print(f"Размер: {path.stat().st_size:,} байт")

    try:
        with wave.open(str(path), "rb") as wav:
            channels = wav.getnchannels()
            sample_rate = wav.getframerate()
            sample_width = wav.getsampwidth()
            declared_frames = wav.getnframes()

            frame_size = channels * sample_width
            actual_bytes = 0

            while True:
                data = wav.readframes(65536)

                if not data:
                    break

                actual_bytes += len(data)

            actual_frames = actual_bytes // frame_size
            remainder = actual_bytes % frame_size

            print("Заголовок WAV: читается")
            print(f"Каналы: {channels}")
            print(f"Частота: {sample_rate} Hz")
            print(f"Разрядность: {sample_width * 8} bit")
            print(f"Кадров по заголовку: {declared_frames:,}")
            print(f"Фактически прочитано: {actual_frames:,}")
            print(f"Байт аудиоданных: {actual_bytes:,}")

            if remainder:
                print("ПРЕДУПРЕЖДЕНИЕ: неполный аудиокадр")

            if actual_frames == declared_frames and not remainder:
                print("Результат: данные соответствуют заголовку")
            else:
                print("Результат: возможное повреждение WAV")

    except (wave.Error, EOFError, OSError) as error:
        print(f"Ошибка чтения WAV: {type(error).__name__}: {error}")


def main():
    session_dir = find_session()
    manifest_path = session_dir / "manifest.json"

    print(f"Сессия: {session_dir}")

    if not manifest_path.exists():
        raise FileNotFoundError("manifest.json не найден")

    with manifest_path.open("r", encoding="utf-8") as file:
        manifest = json.load(file)

    registered_paths = extract_wav_paths(manifest.get("segments", []))

    registered_files = {
        (session_dir / relative_path).resolve()
        for relative_path in registered_paths
    }

    disk_files = sorted(session_dir.rglob("segment_*.wav"))

    print(f"\nСегментов в manifest: {len(registered_files)}")
    print(f"WAV-файлов на диске: {len(disk_files)}")

    orphans = []

    for path in disk_files:
        if path.resolve() not in registered_files:
            orphans.append(path)

    print(f"Незарегистрированных файлов: {len(orphans)}")

    for path in disk_files:
        status = (
            "ЗАРЕГИСТРИРОВАН"
            if path.resolve() in registered_files
            else "ORPHAN"
        )
        print(f"  [{status}] {path.relative_to(session_dir)}")

    if orphans:
        print("\n--- ДИАГНОСТИКА ORPHAN-ФАЙЛОВ ---")

        for path in orphans:
            inspect_wav(path)

    else:
        print("\nНезарегистрированных WAV-файлов нет.")

    print("\nДиагностика завершена. Файлы не изменялись.")


if __name__ == "__main__":
    main()
