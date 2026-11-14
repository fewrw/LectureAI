
import unittest

import numpy as np

from screen.frame_analyzer import (
    FrameAnalyzer,
    FrameMode,
)


class TestFrameAnalyzer(unittest.TestCase):

    def setUp(self):
        self.analyzer = FrameAnalyzer()

    @staticmethod
    def make_gallery():
        image = np.full(
            (180, 320, 3),
            100,
            dtype=np.uint8,
        )

        # Сетка 4x4.
        for x in (80, 160, 240):
            image[:, x - 1:x + 2] = 0

        for y in (45, 90, 135):
            image[y - 1:y + 2, :] = 0

        return image

    @staticmethod
    def make_presentation_top():
        image = np.full(
            (180, 320, 3),
            180,
            dtype=np.uint8,
        )

        # Полоса участников сверху.
        image[44:47, :] = 0

        for x in (80, 160, 240):
            image[:45, x - 1:x + 2] = 0

        # Имитация содержимого демонстрации.
        image[65:75, 30:250] = 230
        image[100:110, 40:280] = 30

        return image

    @staticmethod
    def make_presentation_left():
        image = np.full(
            (180, 320, 3),
            180,
            dtype=np.uint8,
        )

        # Полоса участников слева.
        image[:, 79:82] = 0

        for y in (45, 90, 135):
            image[y - 1:y + 2, :80] = 0

        # Имитация содержимого демонстрации.
        image[30:40, 110:290] = 230
        image[80:90, 120:280] = 30

        return image

    def test_uniform_frame_is_unknown(self):
        image = np.full(
            (720, 1280, 3),
            100,
            dtype=np.uint8,
        )

        result = self.analyzer.analyze(image)

        self.assertEqual(
            result.mode,
            FrameMode.UNKNOWN,
        )

        self.assertIsNone(
            result.content_region,
        )

    def test_detects_gallery(self):
        result = self.analyzer.analyze(
            self.make_gallery()
        )

        self.assertEqual(
            result.mode,
            FrameMode.GALLERY,
        )

        self.assertIsNone(
            result.content_region,
        )

    def test_detects_presentation_with_people_on_top(self):
        result = self.analyzer.analyze(
            self.make_presentation_top()
        )

        self.assertEqual(
            result.mode,
            FrameMode.PRESENTATION_TOP,
        )

        self.assertIsNotNone(
            result.content_region,
        )

        self.assertGreater(
            result.content_region.y,
            0.15,
        )

        self.assertEqual(
            result.content_region.x,
            0.0,
        )

    def test_detects_presentation_with_people_on_left(self):
        result = self.analyzer.analyze(
            self.make_presentation_left()
        )

        self.assertEqual(
            result.mode,
            FrameMode.PRESENTATION_LEFT,
        )

        self.assertIsNotNone(
            result.content_region,
        )

        self.assertGreater(
            result.content_region.x,
            0.15,
        )

        self.assertEqual(
            result.content_region.y,
            0.0,
        )

    def test_invalid_empty_frame_is_rejected(self):
        with self.assertRaises(ValueError):
            self.analyzer.analyze(
                np.array([], dtype=np.uint8)
            )

    def test_invalid_frame_dimensions_are_rejected(self):
        image = np.zeros(
            (100, 100, 2),
            dtype=np.uint8,
        )

        with self.assertRaises(ValueError):
            self.analyzer.analyze(image)

    def test_non_numpy_input_is_rejected(self):
        with self.assertRaises(TypeError):
            self.analyzer.analyze("invalid")

    def test_confidence_is_in_valid_range(self):
        result = self.analyzer.analyze(
            self.make_gallery()
        )

        self.assertGreaterEqual(
            result.confidence,
            0.0,
        )

        self.assertLessEqual(
            result.confidence,
            1.0,
        )


if __name__ == "__main__":
    unittest.main()
