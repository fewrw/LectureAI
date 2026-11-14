
import json
import tempfile
import unittest
import wave

from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from audio.audio_manifest import AudioManifest
from audio.audio_recovery import AudioRecovery
from core.session_manager import SessionManager


class TestSessionManager(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)

        self.session_dir = self.root / "lecture_001"
        self.audio_dir = self.session_dir / "audio"
        self.frames_dir = (
            self.session_dir / "screen" / "frames"
        )

        self.audio_dir.mkdir(parents=True)
        self.frames_dir.mkdir(parents=True)

        self.started_at = datetime.now(
            timezone.utc
        ).isoformat()

        self._create_session_manifest("recording")
        self._create_audio_manifest()

        self.audio_patcher = patch(
            "core.session_manager.AudioRecorder"
        )

        self.screen_patcher = patch(
            "core.session_manager.SystemScreenCapture"
        )

        self.MockAudio = self.audio_patcher.start()
        self.MockScreen = self.screen_patcher.start()

        self.audio = self.MockAudio.return_value
        self.screen = self.MockScreen.return_value

        self.audio.frames_written = 0
        self.audio.segments = []
        self.audio.dropped_chunks = 0
        self.audio.error = None

        self.screen.dropped_frames = 0
        self.screen.error = None

        # Не запускаем настоящий захват экрана.
        self.screen.start.side_effect = RuntimeError(
            "Тест: экран недоступен"
        )

        self.audio.resume.side_effect = (
            self._fake_audio_resume
        )

        self.manager = SessionManager()

    def tearDown(self):
        self.audio_patcher.stop()
        self.screen_patcher.stop()
        self.temp_dir.cleanup()

    def _create_session_manifest(self, status):
        data = {
            "created_at": self.started_at,
            "ended_at": None,
            "duration_seconds": 0,
            "status": status,
            "screen_status": "recording",
            "screen_error": None,
            "session_error": None,
            "screen_frames_saved": 0,
            "audio_frames_written": 0,
            "audio_segments": [],
            "audio_dropped_chunks": 0,
            "screen_dropped_frames": 0,
        }

        path = self.session_dir / "session.json"

        path.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        path.write_text(
            json.dumps(data),
            encoding="utf-8"
        )

    def _create_audio_manifest(self):
        manifest = AudioManifest(self.audio_dir)

        manifest.create(
            sample_rate=48000,
            channels=2,
            checkpoint_seconds=30,
            device_name="Test device"
        )

    def _create_wav(self, filename, frames=480):
        path = self.audio_dir / filename

        with wave.open(str(path), "wb") as wav:
            wav.setnchannels(2)
            wav.setsampwidth(2)
            wav.setframerate(48000)
            wav.writeframes(b"\x00" * frames * 4)

        return path

    def _fake_audio_resume(
        self,
        session_dir,
        output_device_index=None
    ):
        # Имитируем реальное поведение AudioRecorder.resume().
        manifest = AudioManifest(session_dir)
        data = manifest.load_for_resume()

        self.resumed_manifest = manifest

        self.audio.segments = [
            Path(session_dir) / segment["file"]
            for segment in data["segments"]
        ]

        self.audio.frames_written = data["total_frames"]

    def test_resume_recovers_recording_session(self):
        self.manager.resume(self.session_dir)

        result = AudioManifest.inspect(
            self.audio_dir
        )

        self.assertEqual(
            result["status"],
            "recording"
        )

        self.assertEqual(
            self.manager.status,
            "recording"
        )

        self.assertEqual(
            self.manager.screen_status,
            "unavailable"
        )

        self.audio.resume.assert_called_once()

    def test_resume_does_not_recover_already_interrupted_audio(self):
        recovery = AudioRecovery(self.root)

        recovery.recover_session(
            self.audio_dir
        )

        self.assertEqual(
            AudioManifest.inspect(
                self.audio_dir
            )["status"],
            "interrupted"
        )

        self.manager.resume(self.session_dir)

        self.audio.resume.assert_called_once()

        self.assertEqual(
            self.manager.status,
            "recording"
        )

    def test_resume_rejects_completed_session(self):
        self._create_session_manifest("completed")

        manifest = AudioManifest(self.audio_dir)

        manifest.data = AudioManifest.inspect(
            self.audio_dir
        )["manifest"]

        manifest.finish()

        with self.assertRaises(RuntimeError):
            self.manager.resume(self.session_dir)

        self.audio.resume.assert_not_called()

    def test_restores_screen_frame_counter(self):
        old_frame = self.frames_dir / "frame_000004.jpg"
        old_frame.write_bytes(b"test")

        metadata_path = (
            self.session_dir / "screen" / "frames.jsonl"
        )

        metadata_path.write_text(
            json.dumps({
                "file": "screen/frames/frame_000009.jpg"
            }) + "\n",
            encoding="utf-8"
        )

        self.manager._session_dir = self.session_dir
        self.manager._screen_dir = self.frames_dir

        self.manager._restore_screen_frame_counter()

        self.assertEqual(
            self.manager._screen_frames_saved,
            9
        )

        self.assertTrue(old_frame.exists())

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

        # Оба сегмента должны присутствовать в session.json.
        self.assertEqual(
            len(session_data["audio_segments"]),
            2
        )

        self.audio.stop.assert_called_once()


if __name__ == "__main__":
    unittest.main()
