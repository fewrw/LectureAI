
import hashlib
import json
import os
import subprocess
import sys
import time

from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SESSION_ROOT = PROJECT_ROOT / "temp" / "audio_crash_tests"

sys.path.insert(0, str(PROJECT_ROOT / "src"))

from audio.audio_recovery import AudioRecovery
from audio.audio_manifest import AudioManifest


OUTPUT_DEVICE_INDEX = 22
CHECKPOINT_SECONDS = 3


def child_process(session_dir):
    from audio.audio_recorder import AudioRecorder

    recorder = AudioRecorder(
        checkpoint_seconds=CHECKPOINT_SECONDS
    )

    recorder.start(
        output_dir=session_dir,
        output_device_index=OUTPUT_DEVICE_INDEX,
    )

    print("Дочерний процесс начал запись.", flush=True)

    # Ожидаем принудительного завершения процесса.
    while True:
        time.sleep(1)


def read_manifest(session_dir):
    manifest_path = session_dir / "manifest.json"

    if not manifest_path.exists():
        return None

    try:
        with manifest_path.open("r", encoding="utf-8") as file:
            return json.load(file)
    except (OSError, json.JSONDecodeError):
        return None


def file_hash(path):
    digest = hashlib.sha256()

    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)

    return digest.hexdigest()


def get_segment_paths(session_dir, manifest):
    return [
        session_dir / segment["file"]
        for segment in manifest["segments"]
    ]


def verify_segments(session_dir):
    result = AudioManifest.inspect(session_dir)

    if result["invalid_segments"]:
        raise AssertionError(
            f"Обнаружены повреждённые сегменты: "
            f"{result['invalid_segments']}"
        )

    return result


def parent_process():
    SESSION_ROOT.mkdir(parents=True, exist_ok=True)

    session_dir = SESSION_ROOT / (
        "session_" + datetime.now().strftime("%Y%m%d_%H%M%S")
    )

    session_dir.mkdir(parents=True)

    env = os.environ.copy()
    env["PYTHONPATH"] = str(PROJECT_ROOT / "src")

    # --------------------------------------------------
    # ЭТАП 1. Запуск отдельного процесса записи
    # --------------------------------------------------

    print("Этап 1. Запускаем отдельный процесс записи...")

    process = subprocess.Popen(
        [
            sys.executable,
            "-u",
            str(Path(__file__).resolve()),
            "--child",
            str(session_dir),
        ],
        cwd=PROJECT_ROOT,
        env=env,
    )

    try:
        deadline = time.time() + 30

        print("Ожидаем сохранения двух WAV-сегментов...")

        while time.time() < deadline:
            if process.poll() is not None:
                raise RuntimeError(
                    f"Дочерний процесс неожиданно завершился: "
                    f"{process.returncode}"
                )

            manifest = read_manifest(session_dir)

            if manifest and len(manifest.get("segments", [])) >= 2:
                break

            time.sleep(0.2)

        else:
            raise TimeoutError(
                "За 30 секунд не удалось получить два сегмента."
            )

        print("Два сегмента сохранены.")

        # Даём начаться записи следующего сегмента.
        time.sleep(1.5)

        print("Этап 2. Принудительно завершаем процесс...")

        process.kill()
        process.wait(timeout=10)

        print(f"Процесс завершён. Код выхода: {process.returncode}")

    finally:
        if process.poll() is None:
            process.kill()
            process.wait()

    # --------------------------------------------------
    # ЭТАП 2. Восстановление аварийной записи
    # --------------------------------------------------

    print("\nЭтап 3. Восстанавливаем аудиосессию...")

    recovery = AudioRecovery(SESSION_ROOT)
    recovery_result = recovery.recover_session(session_dir)

    manifest = read_manifest(session_dir)

    if manifest is None:
        raise RuntimeError(
            "Не удалось прочитать manifest после восстановления."
        )

    if manifest["status"] != "interrupted":
        raise AssertionError(
            "Сессия не получила статус interrupted."
        )

    if recovery_result["recovered_orphans"] < 1:
        raise AssertionError(
            "Аварийный WAV не был восстановлен."
        )

    recovery_check = verify_segments(session_dir)

    print(f"Статус: {manifest['status']}")
    print(f"Сегментов: {len(manifest['segments'])}")
    print(
        f"Восстановленных аварийных файлов: "
        f"{recovery_result['recovered_orphans']}"
    )

    # Сохраняем контрольные хеши всех файлов,
    # которые уже зарегистрированы после восстановления.
    old_paths = get_segment_paths(session_dir, manifest)

    old_hashes = {
        path: file_hash(path)
        for path in old_paths
    }

    # Также сохраняем исходный аварийный WAV.
    orphan_records = manifest.get("orphan_files", [])

    for record in orphan_records:
        original_path = session_dir / record["file"]

        if original_path.exists():
            old_hashes[original_path] = file_hash(original_path)

    print("Контрольные SHA-256 сохранены.")

    # --------------------------------------------------
    # ЭТАП 3. Продолжение записи
    # --------------------------------------------------

    print("\nЭтап 4. Продолжаем прерванную запись...")

    from audio.audio_recorder import AudioRecorder

    recorder = AudioRecorder()

    recorder.resume(
        session_dir=session_dir,
        output_device_index=OUTPUT_DEVICE_INDEX,
    )

    print("Запись успешно возобновлена.")

    # Записываем достаточно, чтобы получить новые сегменты.
    time.sleep(7)

    print("Останавливаем продолженную запись...")

    new_segments = recorder.stop()

    print(f"Новых сегментов: {len(new_segments)}")

    # --------------------------------------------------
    # ЭТАП 4. Финальная проверка
    # --------------------------------------------------

    print("\nЭтап 5. Проверяем итоговую сессию...")

    final_check = verify_segments(session_dir)
    final_manifest = final_check["manifest"]

    if final_manifest["status"] != "completed":
        raise AssertionError(
            f"Ожидался статус completed, "
            f"получен {final_manifest['status']}"
        )

    # Проверяем, что старые файлы не изменились.
    changed_files = []

    for path, old_hash in old_hashes.items():
        if not path.exists():
            changed_files.append(str(path))
            continue

        if file_hash(path) != old_hash:
            changed_files.append(str(path))

    if changed_files:
        raise AssertionError(
            f"Старые файлы были изменены: {changed_files}"
        )

    # Проверяем нумерацию новых сегментов.
    root_segment_numbers = []

    for path in session_dir.glob("segment_*.wav"):
        try:
            number = int(
                path.stem.replace("segment_", "")
            )
            root_segment_numbers.append(number)
        except ValueError:
            continue

    if len(root_segment_numbers) != len(set(root_segment_numbers)):
        raise AssertionError("Обнаружены повторяющиеся номера сегментов.")

    # Проверяем все WAV-файлы, включая recovered.
    all_wav_files = list(session_dir.rglob("*.wav"))

    print(f"Статус: {final_manifest['status']}")
    print(f"Всего сегментов: {len(final_manifest['segments'])}")
    print(f"Всего WAV-файлов: {len(all_wav_files)}")
    print(f"Общее количество кадров: {final_manifest['total_frames']}")

    total_duration = (
        final_manifest["total_frames"]
        / final_manifest["sample_rate"]
    )

    print(f"Общая длительность: {total_duration:.2f} сек.")

    print(f"Повреждённых сегментов: {len(final_check['invalid_segments'])}")
    print(f"Изменённых старых файлов: {len(changed_files)}")

    if len(final_manifest["segments"]) <= len(old_paths):
        raise AssertionError(
            "После продолжения не появилось новых сегментов."
        )

    if len(final_check["valid_segments"]) != len(final_manifest["segments"]):
        raise AssertionError(
            "Не все сегменты прошли проверку."
        )

    print("\nВСЕ ЭТАПЫ ТЕСТА УСПЕШНО ПРОЙДЕНЫ!")


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--child":
        child_process(Path(sys.argv[2]))
    else:
        parent_process()
