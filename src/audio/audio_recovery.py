
import shutil
import struct
import wave

from pathlib import Path

from audio.audio_manifest import AudioManifest


class AudioRecovery:

    def __init__(self, sessions_dir):
        self.sessions_dir = Path(sessions_dir)

    def find_incomplete_sessions(self):
        if not self.sessions_dir.exists():
            return []

        incomplete = []

        for session_dir in self.sessions_dir.iterdir():
            if not session_dir.is_dir():
                continue

            manifest_path = session_dir / "manifest.json"

            if not manifest_path.exists():
                continue

            try:
                result = AudioManifest.inspect(session_dir)

                if result["status"] == "recording":
                    incomplete.append({
                        "path": session_dir,
                        "result": result
                    })

            except Exception as error:
                incomplete.append({
                    "path": session_dir,
                    "error": str(error)
                })

        return incomplete

    def inspect_session(self, session_dir):
        return AudioManifest.inspect(session_dir)

    @staticmethod
    def _repair_orphan(source, session_dir, manifest):
        """
        Создаёт восстановленную копию аварийного PCM WAV.
        Исходный файл не изменяется.
        """

        file_size = source.stat().st_size

        if file_size < 44:
            raise ValueError("Файл слишком короткий")

        if file_size > 0xFFFFFFFF + 8:
            raise ValueError("Файл превышает лимит RIFF WAV")

        with source.open("rb") as file:
            header = file.read(44)

        (
            riff_id,
            riff_size,
            wave_id
        ) = struct.unpack("<4sI4s", header[:12])

        (
            fmt_id,
            fmt_size
        ) = struct.unpack("<4sI", header[12:20])

        (
            audio_format,
            channels,
            sample_rate,
            byte_rate,
            block_align,
            bits
        ) = struct.unpack("<HHIIHH", header[20:36])

        (
            data_id,
            old_data_size
        ) = struct.unpack("<4sI", header[36:44])

        if riff_id != b"RIFF" or wave_id != b"WAVE":
            raise ValueError("Некорректный RIFF/WAVE")

        if fmt_id != b"fmt " or fmt_size != 16:
            raise ValueError("Неожиданная структура fmt")

        if data_id != b"data":
            raise ValueError("Не найден стандартный data-блок")

        if audio_format != 1:
            raise ValueError("Поддерживается только PCM")

        expected_channels = manifest["channels"]
        expected_rate = manifest["sample_rate"]
        expected_width = manifest["sample_width"]

        if channels != expected_channels:
            raise ValueError("Количество каналов не совпадает")

        if sample_rate != expected_rate:
            raise ValueError("Частота аудио не совпадает")

        if bits != expected_width * 8:
            raise ValueError("Разрядность аудио не совпадает")

        expected_align = channels * expected_width

        if block_align != expected_align:
            raise ValueError("Некорректный размер аудиокадра")

        if byte_rate != sample_rate * block_align:
            raise ValueError("Некорректный byte_rate")

        # Проверяем, что исходный заголовок был корректным
        # до аварийного завершения записи.
        if riff_size != 36 + old_data_size:
            raise ValueError("Исходный размер RIFF некорректен")

        if old_data_size % block_align != 0:
            raise ValueError("Исходный размер data некорректен")

        actual_data_size = file_size - 44

        if actual_data_size <= old_data_size:
            raise ValueError("Нет дополнительных данных для восстановления")

        if actual_data_size % block_align != 0:
            raise ValueError("Дополнительные данные содержат неполный кадр")

        recovered_dir = session_dir / "recovered"
        recovered_dir.mkdir(parents=True, exist_ok=True)

        destination = recovered_dir / source.name

        counter = 1

        while destination.exists():
            destination = recovered_dir / (
                f"{source.stem}_{counter:03d}.wav"
            )
            counter += 1

        # Создаём копию. Оригинал остаётся нетронутым.
        shutil.copy2(source, destination)

        try:
            with destination.open("r+b") as file:
                file.seek(4)
                file.write(struct.pack("<I", file_size - 8))

                file.seek(40)
                file.write(struct.pack("<I", actual_data_size))

            # Проверяем восстановленную копию полностью.
            with wave.open(str(destination), "rb") as audio:
                if audio.getnchannels() != expected_channels:
                    raise ValueError("Ошибка проверки каналов")

                if audio.getframerate() != expected_rate:
                    raise ValueError("Ошибка проверки частоты")

                if audio.getsampwidth() != expected_width:
                    raise ValueError("Ошибка проверки разрядности")

                expected_frames = actual_data_size // block_align

                if audio.getnframes() != expected_frames:
                    raise ValueError("Ошибка количества кадров")

                read_frames = 0

                while True:
                    chunk = audio.readframes(65536)

                    if not chunk:
                        break

                    if len(chunk) % block_align != 0:
                        raise ValueError("Неполный аудиокадр")

                    read_frames += len(chunk) // block_align

                if read_frames != expected_frames:
                    raise ValueError("Не все аудиоданные удалось прочитать")

        except Exception:
            destination.unlink(missing_ok=True)
            raise

        return destination

    def recover_session(self, session_dir):
        session_dir = Path(session_dir)

        result = AudioManifest.inspect(session_dir)

        if result["status"] != "recording":
            raise RuntimeError(
                "Эта сессия не требует восстановления"
            )

        manifest = result["manifest"]

        valid_segments = result["valid_segments"]
        invalid_segments = result["invalid_segments"]
        original_registered_files = {
            segment["file"]
            for segment in manifest["segments"]
        }

        # Оставляем только проверенные зарегистрированные сегменты.
        manifest["segments"] = list(valid_segments)

        manifest["total_frames"] = sum(
            segment["frames"]
            for segment in valid_segments
        )

        manifest["invalid_segments"] = [
            segment["file"]
            for segment in invalid_segments
        ]

        manifest.setdefault("orphan_files", [])

        registered_files = original_registered_files

        already_processed = {
            item["file"]
            for item in manifest["orphan_files"]
        }

        recovered_orphans = 0
        failed_orphans = 0

        # Ищем только сегменты в корне сессии.
        # Файлы внутри recovered повторно не обрабатываем.
        orphan_paths = sorted(
            session_dir.glob("segment_*.wav")
        )

        for source in orphan_paths:
            relative_name = source.relative_to(
                session_dir
            ).as_posix()

            if relative_name in registered_files:
                continue

            if relative_name in already_processed:
                continue

            record = {
                "file": relative_name,
                "discovered_at": AudioManifest._now(),
                "status": "unrecoverable",
                "recovered_to": None,
                "reason": None
            }

            try:
                recovered_path = self._repair_orphan(
                    source,
                    session_dir,
                    manifest
                )

                relative_recovered = recovered_path.relative_to(
                    session_dir
                ).as_posix()

                # Получаем параметры восстановленного WAV.
                with wave.open(str(recovered_path), "rb") as audio:
                    frames = audio.getnframes()
                    sample_rate = audio.getframerate()

                # Регистрируем сегмент в manifest.
                manifest["segments"].append({
                    "file": relative_recovered,
                    "frames": frames,
                    "duration_seconds": round(
                        frames / sample_rate,
                        3
                    ),
                    "completed_at": AudioManifest._now()
                })

                manifest["total_frames"] += frames

                record["status"] = "recovered"
                record["recovered_to"] = relative_recovered

                recovered_orphans += 1

            except Exception as error:
                record["reason"] = str(error)
                failed_orphans += 1

            manifest["orphan_files"].append(record)

        manifest["status"] = "interrupted"
        manifest["ended_at"] = AudioManifest._now()
        manifest["recovered_at"] = AudioManifest._now()

        # Атомарно сохраняем обновлённый manifest.
        manifest_writer = AudioManifest(session_dir)
        manifest_writer.data = manifest
        manifest_writer._save()

        return {
            "session": session_dir,
            "recovered_segments": len(valid_segments),
            "invalid_segments": len(invalid_segments),
            "recovered_orphans": recovered_orphans,
            "failed_orphans": failed_orphans,
            "total_frames": manifest["total_frames"]
        }
