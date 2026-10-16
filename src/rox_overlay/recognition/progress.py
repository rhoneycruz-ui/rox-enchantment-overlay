"""Progress-bar segmentation for normalized enchantment panel crops."""

from __future__ import annotations

import cv2
import numpy as np

from .models import FieldReading


def _longest_left_run(active: np.ndarray, max_start: int) -> tuple[int, int] | None:
    best: tuple[int, int] | None = None
    start: int | None = None
    for index, value in enumerate(np.append(active, False)):
        if value and start is None:
            start = index
        elif not value and start is not None:
            if start <= max_start and (best is None or index - start > best[1] - best[0]):
                best = (start, index)
            start = None
    return best


def read_progress(image: np.ndarray) -> FieldReading[float]:
    if image.size == 0 or image.ndim not in (2, 3):
        return FieldReading(None, 0.0)
    if image.shape[0] < 8 or image.shape[1] < 40:
        return FieldReading(None, 0.0)

    bgr = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR) if image.ndim == 2 else image
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    if float(gray.mean()) < 8 or float(gray.std()) < 5:
        return FieldReading(None, 0.0)

    height, width = bgr.shape[:2]
    x_margin = max(2, round(width * 0.02))
    y_margin = max(2, round(height * 0.24))
    inner = bgr[y_margin : height - y_margin, x_margin : width - x_margin]
    if inner.size == 0:
        return FieldReading(None, 0.0)

    hsv = cv2.cvtColor(inner, cv2.COLOR_BGR2HSV)
    cyan = cv2.inRange(hsv, np.array([75, 55, 75]), np.array([110, 255, 255]))
    kernel = np.ones((3, 3), dtype=np.uint8)
    cyan = cv2.morphologyEx(cyan, cv2.MORPH_CLOSE, kernel)

    active = (cyan > 0).mean(axis=0) >= 0.28
    tolerance = max(2, round(active.size * 0.025))
    if active.any():
        active = cv2.morphologyEx(
            active.astype(np.uint8).reshape(1, -1),
            cv2.MORPH_CLOSE,
            np.ones((1, tolerance), dtype=np.uint8),
        ).ravel().astype(bool)

    run = _longest_left_run(active, max_start=max(4, round(active.size * 0.08)))
    progress = 0.0 if run is None else min(1.0, (run[1] - run[0]) / active.size)
    confidence = min(1.0, 0.55 + float(gray.std()) / 180)
    return FieldReading(round(progress, 4), confidence)

