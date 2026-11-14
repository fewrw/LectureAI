
import json
import os
import threading
import wave

from pathlib import Path


import cv2

from core.session_clock import SessionClock
from audio.audio_recorder import AudioRecorder
from screen.system_screen_capture import SystemScreenCapture
from audio.audio_recovery import AudioRecovery
from audio.audio_manifest import AudioManifest


class SessionManager:

    def test_stop_after_resume_preserves_all_segments(self):
        # Создаём старый сегмент до аварийного завершения.
        old_segment = self._create_wav(
            "segment_000001.wav"
        )

        manifest = AudioManifest(self.audio_dir)
        manifest.data = AudioManifest.inspect(
            self.audio_dir
        )["manifest"]

        timestamp = datetime.now(
            timezone.utc
        ).isoformat()

        manifest.add_segment(
            old_segment,
            started_at=timestamp,
            ended_at=timestamp
        )

        # Имитируем аварийное восстановление.
        self.manager.resume(self.session_dir)

        self.assertEqual(
            self.manager.status,
            "recording"
        )

        # Имитируем появление нового сегмента после восстановления.
        new_segment = self._create_wav(
            "segment_000002.wav"
        )

        self.resumed_manifest.add_segment(
            new_segment,
            started_at=timestamp,
            ended_at=timestamp
        )

        self.audio.segments.append(new_segment)
        self.audio.frames_written += 480

        # Имитируем штатное завершение AudioRecorder.
        self.audio.stop.side_effect = (
            lambda: self.resumed_manifest.finish(
                dropped_chunks=self.audio.dropped_chunks
            )
        )

        self.manager.stop()

        # Проверяем состояние сессии.
        with (self.session_dir / "session.json").open(
            "r",
            encoding="utf-8"
        ) as file:
            session_data = json.load(file)

        self.assertEqual(
            session_data["status"],
            "completed"
        )

        self.assertIsNotNone(
            session_data["ended_at"]
        )

        # Проверяем аудиоманифест.
        result = AudioManifest.inspect(
            self.audio_dir
        )

        self.assertEqual(
            result["status"],
            "completed"
        )

        self.assertEqual(
            result["total_segments"],
            2
        )

        # Старый и новый файлы должны существовать.
        self.assertTrue(old_segment.exists())
        self.assertTrue(new_segment.exists())

        # Проверяем, что оба сегмента записаны в session.json.
        self.assertEqual(
            len(session_data["audio_segments"]),
            2
        )

        self.audio.stop.assert_called_once()

    def __init__(
        self,
        checkpoint_seconds=30,
        screen_sample_interval=5,
    ):
        if screen_sample_interval <= 0:
            raise ValueError(
                "Интервал сохранения кадров должен быть больше нуля"
            )

        self.clock = SessionClock()

        self.audio = AudioRecorder(
            checkpoint_seconds=checkpoint_seconds,
            session_clock=self.clock
        )

        self.screen = SystemScreenCapture()

        self.screen_sample_interval = screen_sample_interval

        self._session_dir = None
        self._screen_dir = None
        self._manifest_path = None

        self._screen_thread = None
        self._screen_stop_event = threading.Event()

        self._status = "idle"
        self._screen_status = "idle"

        self._screen_error = None
        self._session_error = None

        self._screen_frames_saved = 0
        self._started_at = None
        self._ended_at = None

    @property
    def is_running(self):
        return self._status == "recording"

    @property
    def status(self):
        return self._status

    @property
    def screen_status(self):
        return self._screen_status

    @property
    def error(self):
        return self._session_error or self.audio.error

    @property
    def screen_error(self):
        return self._screen_error or self.screen.error

    @property
    def session_dir(self):
        return self._session_dir

    def _restore_screen_frame_counter(self):
        """
        Находит последний использованный номер кадра.
        Проверяет и изображения, и metadata.
        """
        frames_dir = self._screen_dir
        max_number = 0

        # Проверяем существующие изображения.
        for path in frames_dir.glob("frame_*.jpg"):
            try:
                number = int(
                    path.stem.removeprefix("frame_")
                )
                max_number = max(max_number, number)

            except ValueError:
                continue

        # Проверяем также metadata.
        metadata_path = (
            self._session_dir / "screen" / "frames.jsonl"
        )

        if metadata_path.exists():
            with metadata_path.open(
                "r",
                encoding="utf-8"
            ) as file:

                for line in file:
                    try:
                        metadata = json.loads(line)

                        filename = Path(
                            metadata["file"]
                        ).stem

                        number = int(
                            filename.removeprefix("frame_")
                        )

                        max_number = max(
                            max_number,
                            number
                        )

                    except (
                        ValueError,
                        KeyError,
                        TypeError,
                        json.JSONDecodeError
                    ):
                        continue

        self._screen_frames_saved = max_number

    def _save_manifest(self):
        data = {
            "created_at": self._started_at,
            "ended_at": self._ended_at,
            "duration_seconds": self.clock.elapsed(),
            "status": self._status,
            "screen_status": self._screen_status,
            "screen_error": (
                str(self._screen_error)
                if self._screen_error else None
            ),
            "session_error": (
                str(self._session_error)
                if self._session_error else None
            ),
            "screen_frames_saved": self._screen_frames_saved,
            "audio_frames_written": self.audio.frames_written,
            "audio_segments": [
                str(
                    Path(path).resolve().relative_to(
                        self._session_dir
                    )
                )
                for path in self.audio.segments
            ],
            "audio_dropped_chunks": self.audio.dropped_chunks,
            "screen_dropped_frames": self.screen.dropped_frames,
        }

        temporary_path = self._manifest_path.with_suffix(".tmp")

        with temporary_path.open("w", encoding="utf-8") as file:
            json.dump(
                data,
                file,
                ensure_ascii=False,
                indent=4,
            )
            file.flush()
            os.fsync(file.fileno())

        temporary_path.replace(self._manifest_path)

    def start(
        self,
        session_dir,
        output_device_index=None,
        window_name="Teams",
    ):
        if self.is_running:
            raise RuntimeError("Сессия уже запущена")

        session_dir = Path(session_dir).resolve()

        if session_dir.exists():
            if not session_dir.is_dir():
                raise NotADirectoryError(session_dir)

            if any(session_dir.iterdir()):
                raise FileExistsError(
                    f"Папка сессии не пуста: {session_dir}"
                )

        session_dir.mkdir(parents=True, exist_ok=True)

        self._session_dir = session_dir
        self._screen_dir = session_dir / "screen" / "frames"
        self._screen_dir.mkdir(parents=True, exist_ok=True)

        self._manifest_path = session_dir / "session.json"

        self._status = "starting"
        self._screen_status = "starting"

        self._screen_error = None
        self._session_error = None

        self._screen_frames_saved = 0

        self.clock.start()

        self._started_at = self.clock.now()["utc"]
        self._ended_at = None

        self._screen_thread = None
        self._screen_stop_event.clear()

        try:
            self.audio.start(
                output_dir=session_dir / "audio",
                output_device_index=output_device_index,
            )

            try:
                self.screen.start(window_name=window_name)

                self._screen_status = "recording"

                self._screen_thread = threading.Thread(
                    target=self._screen_worker,
                    name="ScreenWorker",
                    daemon=False,
                )

                self._screen_thread.start()

            except Exception as error:
                self._screen_status = "unavailable"
                self._screen_error = error

                try:
                    self.screen.stop()
                except Exception:
                    pass

            self._status = "recording"
            self._save_manifest()

        except Exception:
            self._status = "failed"

            self._screen_stop_event.set()

            try:
                self.screen.stop()
            except Exception:
                pass

            try:
                self.audio.stop()
            except Exception:
                pass

            raise

    def resume(
        self,
        session_dir,
        output_device_index=None,
        window_name="Teams",
    ):
        """
        Восстанавливает ранее прерванную лекцию.
        """

        if self.is_running:
            raise RuntimeError(
                "Сессия уже запущена"
            )

        session_dir = Path(session_dir).resolve()

        manifest_path = session_dir / "session.json"
        audio_dir = session_dir / "audio"

        if not manifest_path.is_file():
            raise FileNotFoundError(
                "Не найден session.json"
            )

        if not audio_dir.is_dir():
            raise FileNotFoundError(
                "Не найдена папка аудиосессии"
            )

        # 1. Загружаем информацию о предыдущей сессии.
        with manifest_path.open(
            "r",
            encoding="utf-8"
        ) as file:
            session_data = json.load(file)

        if not isinstance(session_data, dict):
            raise ValueError(
                "Некорректный session.json"
            )

        if session_data.get("status") not in {
            "recording",
            "interrupted"
        }:
            raise RuntimeError(
                "Эту сессию нельзя продолжить. "
                "Она не находится в прерванном состоянии."
            )

        started_at = session_data.get("created_at")

        if not started_at:
            raise ValueError(
                "В session.json отсутствует время начала лекции"
            )

        # 2. Проверяем аудиоманифест.
        audio_result = AudioManifest.inspect(audio_dir)

        audio_status = audio_result["status"]

        if audio_status not in {
            "recording",
            "interrupted"
        }:
            raise RuntimeError(
                f"Нельзя продолжить аудиосессию: {audio_status}"
            )

        # 3. Восстанавливаем временную шкалу.
        self.clock.restore(started_at)

        # 4. Восстанавливаем внутреннее состояние менеджера.
        self._session_dir = session_dir

        self._screen_dir = (
            session_dir / "screen" / "frames"
        )

        self._screen_dir.mkdir(
            parents=True,
            exist_ok=True
        )

        self._manifest_path = manifest_path

        self._started_at = started_at
        self._ended_at = None

        self._status = "starting"
        self._screen_status = "starting"

        self._screen_error = None
        self._session_error = None

        self._screen_thread = None
        self._screen_stop_event.clear()

        # 5. Восстанавливаем нумерацию изображений.
        self._restore_screen_frame_counter()

        # 6. Если приложение аварийно завершилось
        # во время записи, восстанавливаем WAV.
        if audio_status == "recording":
            recovery = AudioRecovery(
                audio_dir.parent
            )

            recovery_result = recovery.recover_session(
                audio_dir
            )

            print(
                "Восстановление аудио:",
                recovery_result
            )

        # Если статус уже interrupted,
        # значит восстановление ранее выполнялось.
        # Повторно его запускать не нужно.

        # 7. Возобновляем аудиозапись.
        try:
            self.audio.resume(
                session_dir=audio_dir,
                output_device_index=output_device_index,
            )

        except Exception as error:
            self._status = "interrupted"
            self._session_error = error

            try:
                self._save_manifest()
            except Exception:
                pass

            raise

        # 8. Запускаем захват экрана.
        # Если экран недоступен, аудио продолжает работать.
        try:
            self.screen.start(
                window_name=window_name
            )

            self._screen_status = "recording"

            self._screen_thread = threading.Thread(
                target=self._screen_worker,
                name="ScreenWorker",
                daemon=False,
            )

            self._screen_thread.start()

        except Exception as error:
            self._screen_status = "unavailable"
            self._screen_error = error

            try:
                self.screen.stop()
            except Exception:
                pass

        # 9. Сохраняем восстановленное состояние.
        self._status = "recording"
        self._save_manifest()

    def _screen_worker(self):
        metadata_path = (
            self._session_dir / "screen" / "frames.jsonl"
        )

        last_saved = None

        try:
            with metadata_path.open(
                "a",
                encoding="utf-8",
            ) as metadata_file:

                while not self._screen_stop_event.is_set():

                    if self.screen.error is not None:
                        raise RuntimeError(
                            f"Ошибка захвата экрана: "
                            f"{self.screen.error}"
                        )

                    if (
                        self.screen.is_closed
                        and not self._screen_stop_event.is_set()
                    ):
                        raise RuntimeError(
                            "Windows завершила захват экрана"
                        )

                    frame = self.screen.get_frame(timeout=0.5)

                    if frame is None:
                        continue

                    now = frame.monotonic_at

                    if (
                        last_saved is not None
                        and now - last_saved < self.screen_sample_interval
                    ):
                        continue

                    elapsed_seconds = self.clock.elapsed(now)

                    self._screen_frames_saved += 1

                    filename = (
                        f"frame_{self._screen_frames_saved:06d}.jpg"
                    )

                    image_path = self._screen_dir / filename

                    success = cv2.imwrite(
                        str(image_path),
                        frame.image,
                    )

                    if not success:
                        raise RuntimeError(
                            f"Не удалось сохранить кадр: {image_path}"
                        )

                    metadata = {
                        "file": str(
                            image_path.relative_to(
                                self._session_dir
                            )
                        ),
                        "captured_at": frame.captured_at,
                        "elapsed_seconds": elapsed_seconds,
                        "width": frame.width,
                        "height": frame.height,
                        "timespan": frame.timespan,
                    }

                    metadata_file.write(
                        json.dumps(
                            metadata,
                            ensure_ascii=False,
                        ) + "\n"
                    )

                    metadata_file.flush()
                    last_saved = now

        except Exception as error:
            self._screen_error = error
            self._screen_status = "failed"

        finally:
            if self._screen_status == "recording":
                self._screen_status = "stopped"

    def stop(self):
        if self._status != "recording":
            return

        self._screen_stop_event.set()

        try:
            self.screen.stop()
        except Exception as error:
            self._screen_error = error
            self._screen_status = "failed"

        if self._screen_thread is not None:
            self._screen_thread.join()
            self._screen_thread = None

        if self._screen_status == "recording":
            self._screen_status = "stopped"

        audio_error = None

        try:
            self.audio.stop()
        except Exception as error:
            audio_error = error
            self._session_error = error

        self._ended_at = self.clock.now()["utc"]

        if audio_error is None:
            self._status = "completed"
        else:
            self._status = "failed"

        self._save_manifest()

        if audio_error is not None:
            raise RuntimeError(
                f"Ошибка завершения аудиозаписи: {audio_error}"
            )

    def get_statistics(self):
        return {
            "status": self._status,
            "screen_status": self._screen_status,
            "audio_frames_written": self.audio.frames_written,
            "audio_segments": len(self.audio.segments),
            "audio_dropped_chunks": self.audio.dropped_chunks,
            "screen_frames_saved": self._screen_frames_saved,
            "screen_dropped_frames": self.screen.dropped_frames,
        }
