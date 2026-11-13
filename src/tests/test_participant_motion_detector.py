
import unittest

import numpy as np

from screen.participant_motion_detector import (
    ParticipantMotionDetector,
)


class TestParticipantMotionDetector(unittest.TestCase):

    def setUp(self):
        self.detector = ParticipantMotionDetector()

    def test_first_frame_returns_no_regions(self):
        frame = np.zeros((720, 1280, 3), dtype=np.uint8)

        regions = self.detector.update(frame)

        self.assertEqual(regions, [])

    def test_detects_persistent_movement(self):
        rng = np.random.default_rng(42)

        frame = np.zeros((720, 1280, 3), dtype=np.uint8)

        self.detector.update(frame)

        regions = []

        for _ in range(15):
            frame = np.zeros(
                (720, 1280, 3),
                dtype=np.uint8,
            )

            frame[100:350, 900:1200] = (
                rng.integers(
                    0,
                    256,
                    (250, 300, 3),
                    dtype=np.uint8,
                )
            )

            regions = self.detector.update(frame)

        self.assertGreater(len(regions), 0)

    def test_static_frames_do_not_create_regions(self):
        frame = np.zeros((720, 1280, 3), dtype=np.uint8)

        self.detector.update(frame)

        for _ in range(10):
            regions = self.detector.update(frame)

        self.assertEqual(regions, [])

    def test_reset_clears_detector(self):
        frame = np.zeros((720, 1280, 3), dtype=np.uint8)

        self.detector.update(frame)
        self.detector.reset()

        self.assertEqual(
            self.detector._previous_frame,
            None,
        )

        self.assertEqual(
            np.count_nonzero(self.detector._motion_map),
            0,
        )

    def test_rejects_invalid_frame(self):
        with self.assertRaises(ValueError):
            self.detector.update(
                np.array([], dtype=np.uint8)
            )


if __name__ == "__main__":
    unittest.main()
