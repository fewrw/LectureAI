
import math

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class ContentRegion:
    # Координаты относительно всего кадра, от 0.0 до 1.0
    x: float
    y: float
    width: float
    height: float

    def __post_init__(self):
        values = (self.x, self.y, self.width, self.height)

        if not all(math.isfinite(value) for value in values):
            raise ValueError("Координаты должны быть конечными числами")

        if self.x < 0 or self.y < 0:
            raise ValueError("Координаты не могут быть отрицательными")

        if self.width <= 0 or self.height <= 0:
            raise ValueError("Размер области должен быть положительным")

        if self.x + self.width > 1 or self.y + self.height > 1:
            raise ValueError("Область выходит за границы кадра")


class ContentRegionCropper:

    def __init__(self, region=None):
        self.region = region

    def set_region(self, region):
        if not isinstance(region, ContentRegion):
            raise TypeError("Ожидается объект ContentRegion")

        self.region = region

    def crop(self, image):
        if not isinstance(image, np.ndarray):
            raise TypeError("Кадр должен быть NumPy-массивом")

        if image.ndim not in (2, 3) or image.size == 0:
            raise ValueError("Некорректный кадр")

        if self.region is None:
            raise RuntimeError("Область демонстрации ещё не настроена")

        image_height, image_width = image.shape[:2]

        region = self.region

        left = int(region.x * image_width)
        top = int(region.y * image_height)

        right = math.ceil(
            (region.x + region.width) * image_width
        )
        bottom = math.ceil(
            (region.y + region.height) * image_height
        )

        return image[top:bottom, left:right].copy()
