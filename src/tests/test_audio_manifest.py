
import json
import tempfile
import unittest
import wave

from pathlib import Path

from audio.audio_manifest import AudioManifest


class TestAudioManifest(unittest.TestCase):

    def test_resume_rejects_total_frames_mismatch(self):
        path = self.create_wav()
        self.manifest.add_segment(path)

        self.manifest.data["status"] = "interrupted"
        self.manifest.data["total_frames"] = 100
        self.manifest._save()

        with self.assertRaises(ValueError):
            self.manifest.load_for_resume()

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.session_dir = Path(self.temp_dir.name) / "session"

        self.manifest = AudioManifest(self.session_dir)

        self.sample_rate = 48000
        self.channels = 2

        self.manifest.create(
            sample_rate=self.sample_rate,
            channels=self.channels,
            checkpoint_seconds=5,
            device_name="Test Device"
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    def create_wav(
        self,
        filename="segment_000001.wav",
        frames=48000,
        sample_rate=48000,
        channels=2,
        sample_width=2
    ):
        path = self.session_dir / filename
        path.parent.mkdir(parents=True, exist_ok=True)

        with wave.open(str(path), "wb") as audio:
            audio.setnchannels(channels)
            audio.setsampwidth(sample_width)
            audio.setframerate(sample_rate)
            audio.writeframes(
                b"\x00" * frames * channels * sample_width
            )

        return path

    def test_create_manifest(self):
        data = self.manifest.data

        self.assertEqual(data["schema_version"], 1)
        self.assertEqual(data["status"], "recording")
        self.assertEqual(data["sample_rate"], 48000)
        self.assertEqual(data["channels"], 2)
        self.assertEqual(data["segments"], [])
        self.assertTrue(self.manifest.manifest_path.exists())

    def test_add_segment(self):
        path = self.create_wav()

        self.manifest.add_segment(path)

        data = self.manifest.data

        self.assertEqual(len(data["segments"]), 1)
        self.assertEqual(data["total_frames"], 48000)
        self.assertEqual(
            data["segments"][0]["file"],
            "segment_000001.wav"
        )

    def test_add_segment_rejects_duplicate(self):
        path = self.create_wav()

        self.manifest.add_segment(path)

        with self.assertRaises(ValueError):
            self.manifest.add_segment(path)

    def test_add_segment_rejects_external_file(self):
        external_dir = Path(self.temp_dir.name) / "external"
        external_dir.mkdir()

        external_path = external_dir / "outside.wav"

        with wave.open(str(external_path), "wb") as audio:
            audio.setnchannels(2)
            audio.setsampwidth(2)
            audio.setframerate(48000)
            audio.writeframes(b"\x00" * 192000)

        with self.assertRaises(ValueError):
            self.manifest.add_segment(external_path)

    def test_add_segment_rejects_wrong_sample_rate(self):
        path = self.create_wav(sample_rate=44100)

        with self.assertRaises(ValueError):
            self.manifest.add_segment(path)

    def test_add_segment_rejects_wrong_channels(self):
        path = self.create_wav(channels=1)

        with self.assertRaises(ValueError):
            self.manifest.add_segment(path)

    def test_add_segment_rejects_empty_wav(self):
        path = self.create_wav(frames=0)

        with self.assertRaises(ValueError):
            self.manifest.add_segment(path)

    def test_finish_manifest(self):
        self.manifest.finish(dropped_chunks=3)

        data = self.manifest.data

        self.assertEqual(data["status"], "completed")
        self.assertIsNotNone(data["ended_at"])
        self.assertEqual(data["dropped_chunks"], 3)

    def test_inspect_valid_manifest(self):
        path = self.create_wav()

        self.manifest.add_segment(path)

        result = AudioManifest.inspect(self.session_dir)

        self.assertEqual(result["status"], "recording")
        self.assertEqual(len(result["valid_segments"]), 1)
        self.assertEqual(len(result["invalid_segments"]), 0)
        self.assertTrue(result["total_frames_matches"])

    def test_inspect_detects_corrupted_wav(self):
        path = self.create_wav()

        self.manifest.add_segment(path)

        path.write_bytes(b"not a valid wav file")

        result = AudioManifest.inspect(self.session_dir)

        self.assertEqual(len(result["valid_segments"]), 0)
        self.assertEqual(len(result["invalid_segments"]), 1)

    def test_inspect_detects_total_frames_mismatch(self):
        path = self.create_wav()

        self.manifest.add_segment(path)

        self.manifest.data["total_frames"] = 100
        self.manifest._save()

        result = AudioManifest.inspect(self.session_dir)

        self.assertFalse(result["total_frames_matches"])
        self.assertEqual(result["actual_total_frames"], 48000)
        self.assertEqual(result["manifest_total_frames"], 100)

    def test_load_for_resume(self):
        path = self.create_wav()

        self.manifest.add_segment(path)

        self.manifest.data["status"] = "interrupted"
        self.manifest._save()

        resumed = self.manifest.load_for_resume()

        self.assertEqual(resumed["status"], "recording")
        self.assertIsNone(resumed["ended_at"])
        self.assertEqual(len(resumed["resume_history"]), 1)
        self.assertEqual(len(resumed["segments"]), 1)

    def test_resume_rejects_completed_session(self):
        self.manifest.finish()

        with self.assertRaises(ValueError):
            self.manifest.load_for_resume()

    def test_next_segment_number(self):
        self.create_wav("segment_000001.wav")
        self.create_wav("segment_000002.wav")
        self.create_wav("segment_000007.wav")

        self.assertEqual(
            self.manifest.next_segment_number(),
            8
        )

    def test_inspect_rejects_unsupported_schema(self):
        self.manifest.data["schema_version"] = 999
        self.manifest._save()

        with self.assertRaises(ValueError):
            AudioManifest.inspect(self.session_dir)

    def test_inspect_rejects_missing_manifest(self):
        missing_dir = Path(self.temp_dir.name) / "missing"

        with self.assertRaises(FileNotFoundError):
            AudioManifest.inspect(missing_dir)


if __name__ == "__main__":
    unittest.main()
