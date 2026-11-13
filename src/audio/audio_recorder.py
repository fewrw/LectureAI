
import threading
import wave

from pathlib import Path

from audio.system_audio_capture import SystemAudioCapture
from audio.audio_manifest import AudioManifest


class AudioRecorder:
    def __init__(self, checkpoint_seconds=30):
        self._capture = SystemAudioCapture()
        self._thread = None
        self._stop_event = threading.Event()

        self._output_dir = None
        self._error = None
        self._manifest = None

        self.checkpoint_seconds = checkpoint_seconds
        self.frames_written = 0
        self.segments = []

    @property
    def is_running(self):
        return (
            self._thread is not None
            and self._thread.is_alive()
        )

    @property
    def error(self):
        return self._error

    @property
    def dropped_chunks(self):
        return self._capture.dropped_chunks

    def _start_writer(self):
        self._stop_event.clear()

        self._thread = threading.Thread(
            target=self._write_audio,
            name="AudioWriter",
            daemon=False
        )

        self._thread.start()

    def start(self, output_dir, output_device_index=None):
        if self.is_running:
            raise RuntimeError("Запись уже запущена")

        self._output_dir = Path(output_dir)
        self._output_dir.mkdir(
            parents=True,
            exist_ok=True
        )

        self._error = None
        self.frames_written = 0
        self.segments = []
        self._manifest = None

        self._capture.start(
            output_device_index=output_device_index
        )

        try:
            self._manifest = AudioManifest(
                self._output_dir
            )

            self._manifest.create(
                sample_rate=self._capture.sample_rate,
                channels=self._capture.channels,
                checkpoint_seconds=self.checkpoint_seconds,
                device_name=self._capture.device_name
            )

            self._start_writer()

        except Exception:
            self._capture.stop()
            raise

    def resume(self, session_dir, output_device_index=None):
        """
        Продолжает ранее восстановленную аудиосессию.
        Старые сегменты остаются на месте.
        """
        if self.is_running:
            raise RuntimeError("Запись уже запущена")

        self._output_dir = Path(session_dir)

        self._error = None
        self.frames_written = 0
        self.segments = []
        self._manifest = AudioManifest(
            self._output_dir
        )

        # Сначала проверяем и загружаем старую сессию.
        data = self._manifest.load_for_resume()

        # Продолжаем использовать исходные параметры сегментации.
        self.checkpoint_seconds = data["checkpoint_seconds"]

        self.frames_written = data["total_frames"]

        self.segments = [
            self._output_dir / segment["file"]
            for segment in data["segments"]
        ]

        try:
            self._capture.start(
                output_device_index=output_device_index
            )

            if (
                self._capture.sample_rate != data["sample_rate"]
                or self._capture.channels != data["channels"]
            ):
                raise RuntimeError(
                    "Параметры выбранного устройства "
                    "не совпадают с исходной записью"
                )

            self._start_writer()

        except Exception:
            try:
                self._capture.stop()
            finally:
                # Возвращаем сессию в состояние,
                # в котором её можно восстановить повторно.
                self._manifest.data["status"] = "interrupted"
                self._manifest.data["ended_at"] = (
                    AudioManifest._now()
                )
                self._manifest._save()

            raise

    def _write_audio(self):
        writer = None
        segment_path = None

        segment_number = (
            self._manifest.next_segment_number() - 1
        )

        segment_frames = 0

        frames_per_segment = (
            self._capture.sample_rate
            * self.checkpoint_seconds
        )

        bytes_per_frame = (
            2 * self._capture.channels
        )

        try:
            while True:
                chunk = self._capture.get_chunk(
                    timeout=0.2
                )

                if chunk is None:
                    if self._stop_event.is_set():
                        break
                    continue

                data = chunk.data
                offset = 0

                if len(data) % bytes_per_frame != 0:
                    raise RuntimeError(
                        "Получен аудиоблок неполной длины"
                    )

                while offset < len(data):
                    if writer is None:
                        segment_number += 1
                        segment_frames = 0

                        segment_path = (
                            self._output_dir
                            / f"segment_{segment_number:06d}.wav"
                        )

                        if segment_path.exists():
                            raise FileExistsError(
                                f"Отказ от перезаписи: {segment_path}"
                            )

                        writer = wave.open(
                            str(segment_path),
                            "wb"
                        )

                        writer.setnchannels(chunk.channels)
                        writer.setsampwidth(2)
                        writer.setframerate(chunk.sample_rate)

                    remaining_frames = (
                        frames_per_segment - segment_frames
                    )

                    remaining_bytes = (
                        remaining_frames * bytes_per_frame
                    )

                    part = data[
                        offset:offset + remaining_bytes
                    ]

                    writer.writeframesraw(part)

                    written_frames = (
                        len(part) // bytes_per_frame
                    )

                    segment_frames += written_frames
                    self.frames_written += written_frames
                    offset += len(part)

                    if segment_frames >= frames_per_segment:
                        writer.close()
                        writer = None

                        self._manifest.add_segment(
                            segment_path
                        )

                        self.segments.append(segment_path)
                        segment_path = None

        except Exception as error:
            self._error = error

        finally:
            if writer is not None:
                writer.close()

                if self._error is None:
                    try:
                        self._manifest.add_segment(
                            segment_path
                        )

                        self.segments.append(segment_path)

                    except Exception as error:
                        self._error = error

    def stop(self):
        if self._thread is None:
            return self.segments

        capture_error = None

        try:
            self._capture.stop()
        except Exception as error:
            capture_error = error
        finally:
            self._stop_event.set()

            self._thread.join()
            self._thread = None

        if capture_error is not None and self._error is None:
            self._error = capture_error

        if self._error is None:
            self._manifest.finish(
                dropped_chunks=self.dropped_chunks
            )

        if self._error is not None:
            raise RuntimeError(
                f"Ошибка сохранения аудио: {self._error}"
            )

        return self.segments
