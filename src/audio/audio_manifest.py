
import json
import os
import re
import wave
import math

from datetime import datetime, timezone
from pathlib import Path


class AudioManifest:
    SCHEMA_VERSION = 1
    SAMPLE_WIDTH = 2

    def __init__(self, session_dir):
        self.session_dir = Path(session_dir)
        self.manifest_path = self.session_dir / "manifest.json"
        self.data = None

    @staticmethod
    def _now():
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _validate_elapsed_times(start, end):
        if (start is None) != (end is None):
            raise ValueError(
                "Время начала и окончания должны "
                "указываться одновременно"
            )

        if start is None:
            return

        values = {
            "start_elapsed_seconds": start,
            "end_elapsed_seconds": end,
        }

        for name, value in values.items():
            if isinstance(value, bool) or not isinstance(
                value, (int, float)
            ):
                raise ValueError(
                    f"{name}: значение должно быть числом"
                )

            if not math.isfinite(value) or value < 0:
                raise ValueError(
                    f"{name}: некорректное значение времени"
                )

        if end < start:
            raise ValueError(
                "Время окончания не может быть раньше времени начала"
            )

    def create(
        self,
        sample_rate,
        channels,
        checkpoint_seconds,
        device_name
    ):
        self.session_dir.mkdir(parents=True, exist_ok=True)

        if self.manifest_path.exists():
            raise FileExistsError(
                f"Манифест уже существует: {self.manifest_path}"
            )

        if sample_rate <= 0:
            raise ValueError(
                "Частота дискретизации должна быть больше нуля."
            )

        if channels <= 0:
            raise ValueError(
                "Количество каналов должно быть больше нуля."
            )

        if checkpoint_seconds <= 0:
            raise ValueError(
                "Длительность сегмента должна быть больше нуля."
            )

        self.data = {
            "schema_version": self.SCHEMA_VERSION,
            "created_at": self._now(),
            "ended_at": None,
            "status": "recording",
            "device_name": device_name,
            "sample_rate": sample_rate,
            "channels": channels,
            "sample_width": self.SAMPLE_WIDTH,
            "checkpoint_seconds": checkpoint_seconds,
            "segments": [],
            "total_frames": 0,
            "dropped_chunks": 0,
            "resume_history": []
        }

        self._save()

    def load_for_resume(self):
        result = self.inspect(self.session_dir)

        if result["status"] != "interrupted":
            raise ValueError(
                "Продолжить можно только прерванную аудиосессию."
            )

        if not result["total_frames_matches"]:
            raise ValueError(
                "Количество кадров в манифесте не совпадает "
                "с фактическим количеством кадров WAV-файлов."
            )

        if result["invalid_segments"]:
            raise ValueError(
                "Нельзя продолжить сессию: обнаружены "
                "некорректные аудиосегменты."
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
        pattern = re.compile(r"segment_(\d+)\.wav$")

        max_number = 0

        for path in self.session_dir.iterdir():
            if not path.is_file():
                continue

            match = pattern.fullmatch(path.name)

            if match:
                number = int(match.group(1))
                max_number = max(max_number, number)

        return max_number + 1

    def _save(self):
        if self.data is None:
            raise RuntimeError(
                "Нет данных манифеста для сохранения."
            )

        self.session_dir.mkdir(parents=True, exist_ok=True)

        temporary_path = self.manifest_path.with_name(
            self.manifest_path.name + ".tmp"
        )

        try:
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

            os.replace(temporary_path, self.manifest_path)

        finally:
            if temporary_path.exists():
                try:
                    temporary_path.unlink()
                except OSError:
                    pass

    def add_segment(
        self,
        segment_path,
        started_at=None,
        ended_at=None,
        start_elapsed_seconds=None,
        end_elapsed_seconds=None
    ):
        self._validate_elapsed_times(
            start_elapsed_seconds,
            end_elapsed_seconds
        )

        if self.data is None:
            raise RuntimeError(
                "Манифест не инициализирован."
            )

        segment_path = Path(segment_path).resolve()
        session_root = self.session_dir.resolve()

        try:
            relative_path = segment_path.relative_to(session_root)
        except ValueError:
            raise ValueError(
                "WAV-файл должен находиться внутри папки аудиосессии."
            )

        relative_name = relative_path.as_posix()

        existing_files = {
            segment["file"]
            for segment in self.data["segments"]
        }

        if relative_name in existing_files:
            raise ValueError(
                f"Сегмент уже зарегистрирован: {relative_name}"
            )

        if not segment_path.is_file():
            raise FileNotFoundError(
                f"Файл сегмента не найден: {segment_path}"
            )

        with wave.open(str(segment_path), "rb") as audio:
            frames = audio.getnframes()
            sample_rate = audio.getframerate()
            channels = audio.getnchannels()
            sample_width = audio.getsampwidth()
            compression = audio.getcomptype()

        if compression != "NONE":
            raise ValueError(
                "Поддерживаются только WAV PCM без сжатия."
            )

        if sample_width != self.SAMPLE_WIDTH:
            raise ValueError(
                f"Неверная глубина аудио: {sample_width} байт."
            )

        if sample_rate != self.data["sample_rate"]:
            raise ValueError(
                "Частота дискретизации сегмента "
                "не совпадает с манифестом."
            )

        if channels != self.data["channels"]:
            raise ValueError(
                "Количество каналов сегмента "
                "не совпадает с манифестом."
            )

        if frames <= 0:
            raise ValueError("Аудиосегмент пустой.")

        segment_data = {
            "file": relative_name,
            "frames": frames,
            "duration_seconds": round(
                frames / sample_rate,
                3
            ),
            "completed_at": self._now()
        }

        if started_at is not None:
            segment_data["started_at"] = started_at

        if ended_at is not None:
            segment_data["ended_at"] = ended_at

        if start_elapsed_seconds is not None:
            segment_data["start_elapsed_seconds"] = float(
                start_elapsed_seconds
            )

            segment_data["end_elapsed_seconds"] = float(
                end_elapsed_seconds
            )

        updated_data = dict(self.data)
        updated_segments = list(self.data["segments"])

        updated_segments.append(segment_data)

        updated_data["segments"] = updated_segments
        updated_data["total_frames"] = (
            self.data["total_frames"] + frames
        )

        previous_data = self.data
        self.data = updated_data

        try:
            self._save()
        except Exception:
            self.data = previous_data
            raise

    def finish(self, dropped_chunks=0):
        if self.data is None:
            raise RuntimeError(
                "Манифест не инициализирован."
            )

        updated_data = dict(self.data)

        updated_data["status"] = "completed"
        updated_data["ended_at"] = self._now()
        updated_data["dropped_chunks"] = dropped_chunks

        previous_data = self.data
        self.data = updated_data

        try:
            self._save()
        except Exception:
            self.data = previous_data
            raise

    @classmethod
    def inspect(cls, session_dir):
        session_dir = Path(session_dir).resolve()
        manifest_path = session_dir / "manifest.json"

        if not manifest_path.is_file():
            raise FileNotFoundError(
                f"Манифест не найден: {manifest_path}"
            )

        with open(
            manifest_path,
            "r",
            encoding="utf-8"
        ) as file:
            data = json.load(file)

        if not isinstance(data, dict):
            raise ValueError(
                "Некорректная структура манифеста."
            )

        required_fields = {
            "schema_version",
            "status",
            "sample_rate",
            "channels",
            "sample_width",
            "segments",
            "total_frames"
        }

        missing_fields = required_fields - data.keys()

        if missing_fields:
            raise ValueError(
                f"В манифесте отсутствуют поля: {missing_fields}"
            )

        if data["schema_version"] != cls.SCHEMA_VERSION:
            raise ValueError(
                "Неподдерживаемая версия схемы манифеста: "
                f"{data['schema_version']}"
            )

        if data["status"] not in {
            "recording",
            "interrupted",
            "completed"
        }:
            raise ValueError(
                f"Неизвестный статус сессии: {data['status']}"
            )

        if not isinstance(data["segments"], list):
            raise ValueError(
                "Поле segments должно быть списком."
            )

        if (
            isinstance(data["sample_rate"], bool)
            or not isinstance(data["sample_rate"], int)
            or data["sample_rate"] <= 0
        ):
            raise ValueError(
                "Некорректная частота дискретизации."
            )

        if (
            isinstance(data["channels"], bool)
            or not isinstance(data["channels"], int)
            or data["channels"] <= 0
        ):
            raise ValueError(
                "Некорректное количество каналов."
            )

        if data["sample_width"] != cls.SAMPLE_WIDTH:
            raise ValueError(
                "Неподдерживаемая глубина аудио."
            )

        valid_segments = []
        invalid_segments = []
        registered_files = set()
        actual_total_frames = 0

        for segment in data["segments"]:
            if not isinstance(segment, dict):
                invalid_segments.append({
                    "segment": segment,
                    "error": "Некорректная структура записи сегмента."
                })
                continue

            # Проверка временных меток
            has_start = "start_elapsed_seconds" in segment
            has_end = "end_elapsed_seconds" in segment

            if has_start != has_end:
                invalid_segments.append({
                    "segment": segment,
                    "error": "Отсутствует одна из временных меток."
                })
                continue

            if has_start:
                try:
                    cls._validate_elapsed_times(
                        segment["start_elapsed_seconds"],
                        segment["end_elapsed_seconds"]
                    )
                except (ValueError, TypeError) as error:
                    invalid_segments.append({
                        "segment": segment,
                        "error": str(error)
                    })
                    continue

            relative_name = segment.get("file")

            if (
                not isinstance(relative_name, str)
                or not relative_name
            ):
                invalid_segments.append({
                    "segment": segment,
                    "error": "Отсутствует имя файла."
                })
                continue

            relative_path = Path(relative_name)

            if (
                relative_path.is_absolute()
                or ".." in relative_path.parts
            ):
                invalid_segments.append({
                    "file": relative_name,
                    "error": "Недопустимый путь к файлу."
                })
                continue

            normalized_name = relative_path.as_posix()

            if normalized_name in registered_files:
                invalid_segments.append({
                    "file": relative_name,
                    "error": "Повторная регистрация одного файла."
                })
                continue

            registered_files.add(normalized_name)

            segment_path = (
                session_dir / relative_path
            ).resolve()

            try:
                segment_path.relative_to(session_dir)
            except ValueError:
                invalid_segments.append({
                    "file": relative_name,
                    "error": "Путь выходит за пределы аудиосессии."
                })
                continue

            try:
                if not segment_path.is_file():
                    raise FileNotFoundError(
                        "Файл не найден."
                    )

                with wave.open(
                    str(segment_path),
                    "rb"
                ) as audio:
                    frames = audio.getnframes()
                    sample_rate = audio.getframerate()
                    channels = audio.getnchannels()
                    sample_width = audio.getsampwidth()
                    compression = audio.getcomptype()

                if compression != "NONE":
                    raise ValueError(
                        "WAV использует сжатие."
                    )

                if frames <= 0:
                    raise ValueError(
                        "Сегмент пустой."
                    )

                if sample_rate != data["sample_rate"]:
                    raise ValueError(
                        "Не совпадает частота дискретизации."
                    )

                if channels != data["channels"]:
                    raise ValueError(
                        "Не совпадает количество каналов."
                    )

                if sample_width != data["sample_width"]:
                    raise ValueError(
                        "Не совпадает глубина аудио."
                    )

                if segment.get("frames") != frames:
                    raise ValueError(
                        "Количество кадров не совпадает."
                    )

                valid_segments.append(segment)
                actual_total_frames += frames

            except (
                OSError,
                EOFError,
                wave.Error,
                KeyError,
                ValueError
            ) as error:
                invalid_segments.append({
                    "file": relative_name,
                    "error": str(error)
                })

        manifest_total_frames = data["total_frames"]

        total_frames_matches = (
            actual_total_frames == manifest_total_frames
        )

        return {
            "status": data["status"],
            "valid_segments": valid_segments,
            "invalid_segments": invalid_segments,
            "total_segments": len(data["segments"]),
            "actual_total_frames": actual_total_frames,
            "manifest_total_frames": manifest_total_frames,
            "total_frames_matches": total_frames_matches,
            "manifest": data
        }
