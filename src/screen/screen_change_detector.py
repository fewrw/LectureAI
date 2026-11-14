
import cv2
import numpy as np


class ScreenChangeDetector:

    def __init__(
        self,
        resize_width=320,
        resize_height=180,
        pixel_threshold=25,
        change_threshold=0.005,
    ):
        self.resize_width = resize_width
        self.resize_height = resize_height
        self.pixel_threshold = pixel_threshold
        self.change_threshold = change_threshold

        self._previous_frame = None
        self.last_change_ratio = 0.0

    def _prepare_frame(self, image):
        if not isinstance(image, np.ndarray):
            raise TypeError("Кадр должен быть NumPy-массивом")

        if image.size == 0:
            raise ValueError("Получен пустой кадр")

        if image.ndim == 2:
            gray = image

        elif image.ndim == 3 and image.shape[2] == 4:
            gray = cv2.cvtColor(image, cv2.COLOR_BGRA2GRAY)

        elif image.ndim == 3 and image.shape[2] == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        else:
            raise ValueError("Неподдерживаемый формат кадра")

        resized = cv2.resize(
            gray,
            (self.resize_width, self.resize_height),
            interpolation=cv2.INTER_AREA,
        )

        return cv2.GaussianBlur(resized, (5, 5), 0)

    def has_changed(self, image):
        current = self._prepare_frame(image)

        if self._previous_frame is None:
            self._previous_frame = current
            self.last_change_ratio = 1.0
            return True

        difference = cv2.absdiff(
            self._previous_frame,
            current,
        )

        changed_pixels = np.count_nonzero(
            difference > self.pixel_threshold
        )

        total_pixels = difference.size

        self.last_change_ratio = (
            changed_pixels / total_pixels
        )

        if self.last_change_ratio >= self.change_threshold:
            self._previous_frame = current
            return True

        return False

    def reset(self):
        self._previous_frame = None
        self.last_change_ratio = 0.0
