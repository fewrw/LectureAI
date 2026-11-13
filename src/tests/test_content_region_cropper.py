
import unittest

import numpy as np

from screen.content_region_cropper import (
    ContentRegion,
    ContentRegionCropper,
)


class TestContentRegionCropper(unittest.TestCase):

    def setUp(self):
        self.image = np.zeros(
            (720, 1280, 3),
            dtype=np.uint8,
        )

    def test_crop_full_frame(self):
        cropper = ContentRegionCropper(
            ContentRegion(0, 0, 1, 1)
        )

        result = cropper.crop(self.image)

        self.assertEqual(result.shape, self.image.shape)

    def test_crop_partial_region(self):
        cropper = ContentRegionCropper(
            ContentRegion(0.25, 0.25, 0.5, 0.5)
        )

        result = cropper.crop(self.image)

        self.assertEqual(result.shape, (360, 640, 3))

    def test_crop_returns_copy(self):
        cropper = ContentRegionCropper(
            ContentRegion(0, 0, 0.5, 0.5)
        )

        result = cropper.crop(self.image)
        result[:] = 255

        self.assertEqual(
            int(self.image.max()),
            0,
        )

    def test_missing_region_is_rejected(self):
        cropper = ContentRegionCropper()

        with self.assertRaises(RuntimeError):
            cropper.crop(self.image)

    def test_invalid_region_is_rejected(self):
        with self.assertRaises(ValueError):
            ContentRegion(0.8, 0.8, 0.5, 0.5)

    def test_invalid_image_is_rejected(self):
        cropper = ContentRegionCropper(
            ContentRegion(0, 0, 1, 1)
        )

        with self.assertRaises(ValueError):
            cropper.crop(np.array([]))


if __name__ == "__main__":
    unittest.main()
