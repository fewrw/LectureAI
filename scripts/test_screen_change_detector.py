
import unittest

import numpy as np

from screen.screen_change_detector import ScreenChangeDetector


class TestScreenChangeDetector(unittest.TestCase):

    def setUp(self):
        self.detector = ScreenChangeDetector()

        self.frame = np.zeros(
            (720, 1280, 3),
            dtype=np.uint8,
        )

    def test_first_frame_is_detected(self):
        self.assertTrue(
            self.detector.has_changed(self.frame)
        )

    def test_identical_frame_is_not_detected(self):
        self.detector.has_changed(self.frame)

        self.assertFalse(
            self.detector.has_changed(self.frame.copy())
        )

    def test_small_noise_is_ignored(self):
        self.detector.has_changed(self.frame)

        noisy_frame = self.frame.copy()
        noisy_frame[:] = 3

        self.assertFalse(
            self.detector.has_changed(noisy_frame)
        )

    def test_large_change_is_detected(self):
        self.detector.has_changed(self.frame)

        changed_frame = self.frame.copy()

        changed_frame[100:600, 200:1000] = 255

        self.assertTrue(
            self.detector.has_changed(changed_frame)
        )

    def test_reset_clears_previous_frame(self):
        self.detector.has_changed(self.frame)
        self.detector.reset()

        self.assertTrue(
            self.detector.has_changed(self.frame)
        )

    def test_invalid_frame_is_rejected(self):
        with self.assertRaises(ValueError):
            self.detector.has_changed(
                np.array([])
            )


if __name__ == "__main__":
    unittest.main()
