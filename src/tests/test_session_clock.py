import unittest

from datetime import datetime, timezone
from unittest.mock import patch

from core.session_clock import SessionClock


class TestSessionClock(unittest.TestCase):

    def test_clock_must_be_started(self):
        clock = SessionClock()

        with self.assertRaises(RuntimeError):
            clock.elapsed()

    def test_elapsed_time(self):
        clock = SessionClock()

        with patch(
            "core.session_clock.time.time",
            return_value=1000.0
        ), patch(
            "core.session_clock.time.monotonic",
            return_value=50.0
        ):
            clock.start()

        self.assertEqual(
            clock.elapsed(52.5),
            2.5
        )

    def test_utc_conversion(self):
        clock = SessionClock()

        with patch(
            "core.session_clock.time.time",
            return_value=1000.0
        ), patch(
            "core.session_clock.time.monotonic",
            return_value=50.0
        ):
            clock.start()

        expected = datetime.fromtimestamp(
            1002.0,
            timezone.utc
        ).isoformat()

        self.assertEqual(
            clock.to_utc_iso(52.0),
            expected
        )

    def test_invalid_timestamp(self):
        clock = SessionClock()

        with patch(
            "core.session_clock.time.time",
            return_value=1000.0
        ), patch(
            "core.session_clock.time.monotonic",
            return_value=50.0
        ):
            clock.start()

        with self.assertRaises(ValueError):
            clock.elapsed(float("nan"))

    
    def test_restore_preserves_elapsed_time(self):
        clock = SessionClock()

        started_at = datetime.fromtimestamp(
            1000.0,
            timezone.utc
        ).isoformat()

        with patch(
            "core.session_clock.time.time",
            return_value=1015.0
        ), patch(
            "core.session_clock.time.monotonic",
            return_value=200.0
        ):
            clock.restore(started_at)

        self.assertEqual(
            clock.elapsed(200.0),
            15.0
        )

        self.assertEqual(
            clock.elapsed(202.5),
            17.5
        )

    def test_restore_preserves_utc_conversion(self):
        clock = SessionClock()

        started_at = datetime.fromtimestamp(
            1000.0,
            timezone.utc
        ).isoformat()

        with patch(
            "core.session_clock.time.time",
            return_value=1015.0
        ), patch(
            "core.session_clock.time.monotonic",
            return_value=200.0
        ):
            clock.restore(started_at)

        expected = datetime.fromtimestamp(
            1017.0,
            timezone.utc
        ).isoformat()

        self.assertEqual(
            clock.to_utc_iso(202.0),
            expected
        )

    def test_restore_rejects_invalid_iso(self):
        clock = SessionClock()

        with self.assertRaises(ValueError):
            clock.restore("not-a-date")

    def test_restore_rejects_naive_datetime(self):
        clock = SessionClock()

        with self.assertRaises(ValueError):
            clock.restore("2026-11-14T10:00:00")

    def test_restore_rejects_future_timestamp(self):
        clock = SessionClock()

        future_time = datetime.fromtimestamp(
            1001.0,
            timezone.utc
        ).isoformat()

        with patch(
            "core.session_clock.time.time",
            return_value=1000.0
        ), patch(
            "core.session_clock.time.monotonic",
            return_value=50.0
        ):
            with self.assertRaises(ValueError):
                clock.restore(future_time)

    def test_restore_requires_string(self):
        clock = SessionClock()

        with self.assertRaises(TypeError):
            clock.restore(None)



if __name__ == "__main__":
    unittest.main()