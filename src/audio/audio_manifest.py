
import json
import os
import re
import wave

from datetime import datetime, timezone
from pathlib import Path


class AudioManifest:
    def __init__(self, session_dir):
        self.session_dir = Path(session_dir)
        self.manifest_path = self.session_dir / "manifest.json"
        self.data = None

    @staticmethod
    def _now():
        return datetime.now(timezone.utc).isoformat()

    def create(
        self,
        sample_rate,
        channels,
        checkpoint_seconds,
        device_name
    ):
        self.session_dir.mkdir(
            parents=True,
            exist_ok=True
        )

        if self.manifest_path.exists():
            raise FileExistsError(
                f"Журнал уже существует: {self.manifest_path}"
            )

        self.data = {
            "schema_version": 1,
            "created_at": self._now(),
            "ended_at": None,
            "status": "recording",
            "device_name": device_name,
            "sample_rate": sample_rate,
            "channels": channels,
            "sample_width": 2,
            "checkpoint_seconds": checkpoint_seconds,
            "segments": [],
            "total_frames": 0,
            "dropped_chunks": 0,
            "resume_history": []
        }

        self._save()

    def load_for_resume(self):
        """
        Загружает прерванную сессию и подготавливает её
        к продолжению записи.
        """
        result = self.inspect(self.session_dir)

        if result["status"] != "interrupted":
            raise RuntimeError(
                "Продолжить можно только сессию "
                "со статусом interrupted"
            )

        if result["invalid_segments"]:
            raise RuntimeError(
                "В сессии есть повреждённые сегменты. "
                "Возобновление запрещено."
            )

        self.data = result["manifest"]

        self.data["status"] = "recording"
        self.data["ended_at"] = None

        self.data.setdefault("resume_history", [])
        self.data["resume_history"].append({
            "resumed_at": self._now()
        })

        self._save()

        return self.data

    def next_segment_number(self):
        """
        Находит следующий свободный номер сегмента.
        Учитывает даже файлы, отсутствующие в manifest.json.
        """
        pattern = re.compile(r"segment_(\d+)\.wav$")
        max_number = 0

        for path in self.session_dir.iterdir():
            if not path.is_file():
                continue

            match = pattern.fullmatch(path.name)

            if match:
                max_number = max(
                    max_number,
                    int(match.group(1))
                )

        return max_number + 1

    def _save(self):
        if self.data is None:
            raise RuntimeError("Журнал не создан")

        temporary_path = self.manifest_path.with_suffix(
            ".json.tmp"
        )

        with open(
            temporary_path,
            "w",
            encoding="utf-8"
        ) as file:
            json.dump(
                self.data,
                file,
                ensure_ascii=False,
                indent=4
            )

            file.flush()
            os.fsync(file.fileno())

        os.replace(
            temporary_path,
            self.manifest_path
        )

    def add_segment(self, segment_path):
        segment_path = Path(segment_path).resolve()
        session_root = self.session_dir.resolve()

        try:
            relative_path = segment_path.relative_to(
                session_root
            )
        except ValueError:
            raise ValueError(
                "Сегмент должен находиться внутри папки сессии"
            )

        relative_name = str(relative_path)

        existing_files = {
            segment["file"]
            for segment in self.data["segments"]
        }

        if relative_name in existing_files:
            raise ValueError(
                f"Сегмент уже есть в журнале: {relative_name}"
            )

        if not segment_path.is_file():
            raise FileNotFoundError(segment_path)

        with wave.open(str(segment_path), "rb") as audio:
            frames = audio.getnframes()
            sample_rate = audio.getframerate()
            channels = audio.getnchannels()
            sample_width = audio.getsampwidth()

        if sample_width != self.data["sample_width"]:
            raise ValueError("Неожиданная разрядность аудио")

        if sample_rate != self.data["sample_rate"]:
            raise ValueError("Частота аудио не совпадает")

        if channels != self.data["channels"]:
            raise ValueError(
                "Количество каналов не совпадает"
            )

        self.data["segments"].append({
            "file": relative_name,
            "frames": frames,
            "duration_seconds": round(
                frames / sample_rate,
                3
            ),
            "completed_at": self._now()
        })

        self.data["total_frames"] += frames

        self._save()

    def finish(self, dropped_chunks=0):
        if self.data is None:
            raise RuntimeError("Журнал не загружен")

        self.data["status"] = "completed"
        self.data["ended_at"] = self._now()
        self.data["dropped_chunks"] = dropped_chunks

        self._save()

    @classmethod
    def inspect(cls, session_dir):
        session_dir = Path(session_dir)
        manifest_path = session_dir / "manifest.json"

        if not manifest_path.exists():
            raise FileNotFoundError(
                "Журнал аудиосессии не найден"
            )

        with open(
            manifest_path,
            "r",
            encoding="utf-8"
        ) as file:
            data = json.load(file)

        valid_segments = []
        invalid_segments = []

        for segment in data["segments"]:
            try:
                relative_path = Path(segment["file"])

                if relative_path.is_absolute() or ".." in relative_path.parts:
                    raise ValueError(
                        "Недопустимый путь сегмента"
                    )

                path = session_dir / relative_path

                with wave.open(str(path), "rb") as audio:
                    valid = (
                        audio.getnframes() == segment["frames"]
                        and audio.getframerate()
                        == data["sample_rate"]
                        and audio.getnchannels()
                        == data["channels"]
                        and audio.getsampwidth()
                        == data["sample_width"]
                    )

                if valid:
                    valid_segments.append(segment)
                else:
                    invalid_segments.append(segment)

            except (
                OSError,
                EOFError,
                wave.Error,
                KeyError,
                ValueError
            ):
                invalid_segments.append(segment)

        return {
            "status": data["status"],
            "valid_segments": valid_segments,
            "invalid_segments": invalid_segments,
            "total_segments": len(data["segments"]),
            "manifest": data
        }
