
from dataclasses import dataclass

import cv2
import numpy as np


@dataclass
class MotionRegion:
    x: int
    y: int
    width: int
    height: int
    activity: float


class ParticipantMotionDetector:

    def __init__(
        self,
        resize_width=320,
        resize_height=180,
        grid_columns=16,
        grid_rows=9,
        pixel_threshold=20,
        activity_threshold=0.015,
        min_region_area=0.008,
        max_region_area=0.25,
    ):
        if resize_width % grid_columns != 0:
            raise ValueError(
                "Ширина должна делиться на количество колонок"
            )

        if resize_height % grid_rows != 0:
            raise ValueError(
                "Высота должна делиться на количество строк"
            )

        self.resize_width = resize_width
        self.resize_height = resize_height

        self.grid_columns = grid_columns
        self.grid_rows = grid_rows

        self.pixel_threshold = pixel_threshold
        self.activity_threshold = activity_threshold

        self.min_region_area = min_region_area
        self.max_region_area = max_region_area

        self._previous_frame = None
        self._motion_map = np.zeros(
            (resize_height, resize_width),
            dtype=np.float32,
        )

    def _prepare_frame(self, image):
        if not isinstance(image, np.ndarray):
            raise TypeError("Кадр должен быть NumPy-массивом")

        if image.size == 0:
            raise ValueError("Получен пустой кадр")

        if image.ndim == 2:
            gray = image

        elif image.ndim == 3 and image.shape[2] == 4:
            gray = cv2.cvtColor(
                image,
                cv2.COLOR_BGRA2GRAY,
            )

        elif image.ndim == 3 and image.shape[2] == 3:
            gray = cv2.cvtColor(
                image,
                cv2.COLOR_BGR2GRAY,
            )

        else:
            raise ValueError("Неподдерживаемый формат кадра")

        resized = cv2.resize(
            gray,
            (self.resize_width, self.resize_height),
            interpolation=cv2.INTER_AREA,
        )

        return cv2.GaussianBlur(
            resized,
            (5, 5),
            0,
        )

    def update(self, image):
        current = self._prepare_frame(image)

        if self._previous_frame is None:
            self._previous_frame = current
            return []

        difference = cv2.absdiff(
            self._previous_frame,
            current,
        )

        moving_pixels = (
            difference > self.pixel_threshold
        ).astype(np.float32)

        # Движение постепенно затухает,
        # если область перестаёт изменяться.
        self._motion_map *= 0.85
        self._motion_map = np.maximum(
            self._motion_map,
            moving_pixels,
        )

        self._previous_frame = current

        return self._find_regions()

    def _find_regions(self):
        activity_grid = cv2.resize(
            self._motion_map,
            (self.grid_columns, self.grid_rows),
            interpolation=cv2.INTER_AREA,
        )

        active_cells = (
            activity_grid >= self.activity_threshold
        ).astype(np.uint8)

        # Объединяем соседние активные ячейки.
        kernel = np.ones((3, 3), dtype=np.uint8)

        active_cells = cv2.morphologyEx(
            active_cells,
            cv2.MORPH_CLOSE,
            kernel,
        )

        count, labels, stats, _ = (
            cv2.connectedComponentsWithStats(
                active_cells,
                connectivity=8,
            )
        )

        regions = []

        cell_width = (
            self.resize_width // self.grid_columns
        )
        cell_height = (
            self.resize_height // self.grid_rows
        )

        total_cells = (
            self.grid_columns * self.grid_rows
        )

        for index in range(1, count):
            grid_x, grid_y, grid_w, grid_h, area = (
                stats[index]
            )

            area_ratio = area / total_cells

            if not (
                self.min_region_area
                <= area_ratio
                <= self.max_region_area
            ):
                continue

            region_mask = labels[
                grid_y:grid_y + grid_h,
                grid_x:grid_x + grid_w,
            ] == index

            region_activity = activity_grid[
                grid_y:grid_y + grid_h,
                grid_x:grid_x + grid_w,
            ][region_mask]

            activity = float(
                np.mean(region_activity)
            )

            regions.append(
                MotionRegion(
                    x=grid_x * cell_width,
                    y=grid_y * cell_height,
                    width=grid_w * cell_width,
                    height=grid_h * cell_height,
                    activity=activity,
                )
            )

        return regions

    def reset(self):
        self._previous_frame = None
        self._motion_map.fill(0)
