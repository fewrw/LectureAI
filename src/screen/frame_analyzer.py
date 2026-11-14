
from dataclasses import dataclass
from enum import Enum
from typing import Optional

import cv2
import numpy as np

from screen.content_region_cropper import ContentRegion


class FrameMode(str, Enum):
    GALLERY = "gallery"
    PRESENTATION_TOP = "presentation_top"
    PRESENTATION_LEFT = "presentation_left"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class FrameAnalysis:
    mode: FrameMode
    content_region: Optional[ContentRegion]
    confidence: float
    reason: str

    @property
    def has_presentation(self):
        return self.mode in {
            FrameMode.PRESENTATION_TOP,
            FrameMode.PRESENTATION_LEFT,
        }


class FrameAnalyzer:
    def __init__(
        self,
        resize_width=320,
        resize_height=180,
        line_threshold=10.0,
        line_ratio_threshold=1.8,
        min_grid_lines=2,
        min_confidence=0.35,
        min_boundary_support=0.65,
    ):
        if resize_width < 32 or resize_height < 32:
            raise ValueError("Размер анализа слишком маленький")

        if line_threshold <= 0:
            raise ValueError("line_threshold должен быть больше нуля")

        if line_ratio_threshold <= 1:
            raise ValueError(
                "line_ratio_threshold должен быть больше единицы"
            )

        if min_grid_lines < 1 or min_grid_lines > 3:
            raise ValueError("min_grid_lines должен быть от 1 до 3")

        if not 0 <= min_confidence <= 1:
            raise ValueError("min_confidence должен быть от 0 до 1")

        if not 0 < min_boundary_support <= 1:
            raise ValueError(
                "min_boundary_support должен быть от 0 до 1"
            )

        self.resize_width = resize_width
        self.resize_height = resize_height
        self.line_threshold = line_threshold
        self.line_ratio_threshold = line_ratio_threshold
        self.min_grid_lines = min_grid_lines
        self.min_confidence = min_confidence
        self.min_boundary_support = min_boundary_support

    def _prepare_frame(self, image):
        if not isinstance(image, np.ndarray):
            raise TypeError("Кадр должен быть NumPy-массивом")

        if image.size == 0:
            raise ValueError("Получен пустой кадр")

        if image.ndim == 2:
            gray = image

        elif image.ndim == 3 and image.shape[2] == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        elif image.ndim == 3 and image.shape[2] == 4:
            gray = cv2.cvtColor(image, cv2.COLOR_BGRA2GRAY)

        else:
            raise ValueError("Неподдерживаемый формат кадра")

        resized = cv2.resize(
            gray,
            (self.resize_width, self.resize_height),
            interpolation=cv2.INTER_AREA,
        )

        return cv2.GaussianBlur(resized, (3, 3), 0)

    @staticmethod
    def _horizontal_scores(image):
        if image.shape[0] < 2:
            return np.zeros(0, dtype=np.float32)

        difference = np.abs(
            image[1:, :].astype(np.float32)
            - image[:-1, :].astype(np.float32)
        )

        return np.mean(difference, axis=1)

    @staticmethod
    def _vertical_scores(image):
        if image.shape[1] < 2:
            return np.zeros(0, dtype=np.float32)

        difference = np.abs(
            image[:, 1:].astype(np.float32)
            - image[:, :-1].astype(np.float32)
        )

        return np.mean(difference, axis=0)

    def _count_lines(self, scores, start, end):
        start = max(0, int(start))
        end = min(len(scores), int(end))

        if end <= start:
            return []

        section = scores[start:end]

        if len(section) == 0:
            return []

        baseline = float(np.median(section))

        threshold = max(
            self.line_threshold,
            baseline * self.line_ratio_threshold,
        )

        active = section >= threshold

        positions = []
        index = 0

        while index < len(active):
            if not active[index]:
                index += 1
                continue

            group_start = index

            while index < len(active) and active[index]:
                index += 1

            group_end = index

            peak_index = (
                group_start
                + int(np.argmax(section[group_start:group_end]))
            )

            positions.append(start + peak_index)

        return positions

    def _find_split(self, scores, minimum, maximum):
        axis_size = len(scores)

        start = int(axis_size * minimum)
        end = int(axis_size * maximum)

        if end <= start:
            return None

        candidates = scores[start:end]

        if len(candidates) == 0:
            return None

        baseline = float(np.median(scores))

        index = int(np.argmax(candidates))
        score = float(candidates[index])

        if score < self.line_threshold:
            return None

        if score < baseline * self.line_ratio_threshold:
            return None

        return start + index + 1, score

    def _boundary_support(self, image, position, orientation):
        """
        Проверяет, насколько большая часть границы
        действительно проходит через весь кадр.

        orientation='horizontal':
            проверяется граница между строками.

        orientation='vertical':
            проверяется граница между столбцами.
        """
        if orientation == "horizontal":
            if not 0 < position < image.shape[0]:
                return 0.0

            difference = np.abs(
                image[position, :].astype(np.float32)
                - image[position - 1, :].astype(np.float32)
            )

        elif orientation == "vertical":
            if not 0 < position < image.shape[1]:
                return 0.0

            difference = np.abs(
                image[:, position].astype(np.float32)
                - image[:, position - 1].astype(np.float32)
            )

        else:
            raise ValueError("Неизвестная ориентация границы")

        return float(
            np.mean(difference >= self.line_threshold)
        )

    def _grid_signature(self, scores, axis_size):
        if len(scores) == 0:
            return 0, 0.0

        baseline = float(np.median(scores))

        threshold = max(
            self.line_threshold,
            baseline * self.line_ratio_threshold,
        )

        found = 0
        strengths = []

        for fraction in (0.25, 0.50, 0.75):
            expected = int(axis_size * fraction)

            left = max(0, expected - 2)
            right = min(len(scores), expected + 2)

            if right <= left:
                continue

            score = float(np.max(scores[left:right]))

            if score >= threshold:
                found += 1
                strengths.append(score)

        average_strength = (
            float(np.mean(strengths))
            if strengths else 0.0
        )

        return found, average_strength

    def _presentation_top(self, image, horizontal_scores):
        split = self._find_split(
            horizontal_scores,
            minimum=0.15,
            maximum=0.42,
        )

        if split is None:
            return None

        split_y, split_strength = split

        support = self._boundary_support(
            image,
            split_y,
            "horizontal",
        )

        if support < self.min_boundary_support:
            return None

        top_region = image[:split_y, :]

        vertical_scores = self._vertical_scores(top_region)

        separators = self._count_lines(
            vertical_scores,
            0,
            len(vertical_scores),
        )

        if len(separators) < 2:
            return None

        height, width = image.shape

        region = ContentRegion(
            x=0.0,
            y=split_y / height,
            width=1.0,
            height=(height - split_y) / height,
        )

        confidence = min(
            1.0,
            0.35
            + min(len(separators), 6) * 0.07
            + split_strength / 255.0 * 0.25
            + support * 0.15,
        )

        return FrameAnalysis(
            mode=FrameMode.PRESENTATION_TOP,
            content_region=region,
            confidence=confidence,
            reason=(
                "Обнаружена протяжённая горизонтальная граница "
                "и разделители видеоплиток сверху"
            ),
        )

    def _presentation_left(self, image, vertical_scores):
        split = self._find_split(
            vertical_scores,
            minimum=0.15,
            maximum=0.42,
        )

        if split is None:
            return None

        split_x, split_strength = split

        support = self._boundary_support(
            image,
            split_x,
            "vertical",
        )

        if support < self.min_boundary_support:
            return None

        left_region = image[:, :split_x]

        horizontal_scores = self._horizontal_scores(left_region)

        separators = self._count_lines(
            horizontal_scores,
            0,
            len(horizontal_scores),
        )

        if len(separators) < 2:
            return None

        height, width = image.shape

        region = ContentRegion(
            x=split_x / width,
            y=0.0,
            width=(width - split_x) / width,
            height=1.0,
        )

        confidence = min(
            1.0,
            0.35
            + min(len(separators), 6) * 0.07
            + split_strength / 255.0 * 0.25
            + support * 0.15,
        )

        return FrameAnalysis(
            mode=FrameMode.PRESENTATION_LEFT,
            content_region=region,
            confidence=confidence,
            reason=(
                "Обнаружена протяжённая вертикальная граница "
                "и разделители видеоплиток слева"
            ),
        )

    def _is_gallery(self, image):
        horizontal_scores = self._horizontal_scores(image)
        vertical_scores = self._vertical_scores(image)

        horizontal_count, horizontal_strength = self._grid_signature(
            horizontal_scores,
            image.shape[0],
        )

        vertical_count, vertical_strength = self._grid_signature(
            vertical_scores,
            image.shape[1],
        )

        if (
            horizontal_count < self.min_grid_lines
            or vertical_count < self.min_grid_lines
        ):
            return None

        confidence = min(
            1.0,
            0.35
            + (horizontal_count + vertical_count) * 0.08
            + (horizontal_strength + vertical_strength) / 510.0,
        )

        return FrameAnalysis(
            mode=FrameMode.GALLERY,
            content_region=None,
            confidence=confidence,
            reason=(
                "Обнаружена регулярная сетка "
                "горизонтальных и вертикальных разделителей"
            ),
        )

    def analyze(self, image):
        prepared = self._prepare_frame(image)

        # Сначала проверяем галерею.
        # Регулярная сетка плиток важнее отдельных линий.
        gallery = self._is_gallery(prepared)

        if (
            gallery is not None
            and gallery.confidence >= self.min_confidence
        ):
            return gallery

        horizontal_scores = self._horizontal_scores(prepared)
        vertical_scores = self._vertical_scores(prepared)

        top = self._presentation_top(
            prepared,
            horizontal_scores,
        )

        left = self._presentation_left(
            prepared,
            vertical_scores,
        )

        candidates = [
            candidate
            for candidate in (top, left)
            if candidate is not None
            and candidate.confidence >= self.min_confidence
        ]

        if candidates:
            return max(
                candidates,
                key=lambda item: item.confidence,
            )

        return FrameAnalysis(
            mode=FrameMode.UNKNOWN,
            content_region=None,
            confidence=0.0,
            reason=(
                "Недостаточно геометрических признаков "
                "для определения режима Teams"
            ),
        )