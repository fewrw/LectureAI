
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

    def recover_session(self, session_dir):
        session_dir = Path(session_dir)

        result = AudioManifest.inspect(session_dir)

        if result["status"] != "recording":
            raise RuntimeError(
                "Эта сессия не требует восстановления"
            )

        valid_segments = result["valid_segments"]
        invalid_segments = result["invalid_segments"]

        manifest = result["manifest"]

        manifest["segments"] = valid_segments

        manifest["total_frames"] = sum(
            segment["frames"]
            for segment in valid_segments
        )

        manifest["status"] = "interrupted"
        manifest["recovered_at"] = AudioManifest._now()

        manifest["invalid_segments"] = [
            segment["file"]
            for segment in invalid_segments
        ]

        temporary_path = session_dir / "manifest.json.tmp"
        manifest_path = session_dir / "manifest.json"

        import json
        import os

        with open(
            temporary_path,
            "w",
            encoding="utf-8"
        ) as file:
            json.dump(
                manifest,
                file,
                ensure_ascii=False,
                indent=4
            )

            file.flush()
            os.fsync(file.fileno())

        os.replace(
            temporary_path,
            manifest_path
        )

        return {
            "session": session_dir,
            "recovered_segments": len(valid_segments),
            "invalid_segments": len(invalid_segments),
            "total_frames": manifest["total_frames"]
        }
