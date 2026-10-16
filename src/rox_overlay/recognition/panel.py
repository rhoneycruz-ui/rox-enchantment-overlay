"""Resolution-independent enchantment panel detection."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

from .models import Rect


@dataclass(frozen=True)
class PanelDetection:
    rect: Rect
    scale: float
    confidence: float


@dataclass(frozen=True)
class PanelRegions:
    title: np.ndarray
    level: np.ndarray
    progress: np.ndarray


class PanelDetector:
    def __init__(self, anchor_template: np.ndarray | None = None) -> None:
        if anchor_template is None:
            path = Path(__file__).parents[1] / "assets" / "search-anchor.png"
            anchor_template = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
        if anchor_template is None or anchor_template.size == 0:
            raise ValueError("search anchor template is unavailable")
        self._anchor = anchor_template

    def detect(self, frame: np.ndarray) -> PanelDetection | None:
        if frame.size == 0 or frame.ndim not in (2, 3):
            return None
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if frame.ndim == 3 else frame
        frame_height, frame_width = gray.shape
        search_x = round(frame_width * 0.52) if frame_width / frame_height > 1.2 else 0
        search = gray[:, search_x:]

        best_score = -1.0
        best_location: tuple[int, int] | None = None
        best_width = 0
        for scale in np.linspace(0.55, 1.6, 22):
            width = max(12, round(self._anchor.shape[1] * float(scale)))
            height = max(12, round(self._anchor.shape[0] * float(scale)))
            if width >= search.shape[1] or height >= search.shape[0]:
                continue
            template = cv2.resize(self._anchor, (width, height), interpolation=cv2.INTER_AREA)
            result = cv2.matchTemplate(search, template, cv2.TM_CCOEFF_NORMED)
            _, score, _, location = cv2.minMaxLoc(result)
            if score > best_score:
                best_score = float(score)
                best_location = (location[0] + search_x, location[1])
                best_width = width

        if best_location is None or best_score < 0.58:
            return None

        panel_x = best_location[0] - round(best_width * 0.19)
        panel_y = best_location[1] - round(best_width * 0.19)
        panel_width = round(best_width * 9.30)
        panel_height = round(best_width * 15.20)
        x = max(0, panel_x)
        y = max(0, panel_y)
        right = min(frame_width, panel_x + panel_width)
        bottom = min(frame_height, panel_y + panel_height)
        if right <= x or bottom <= y:
            return None

        rect = Rect(x, y, right - x, bottom - y)
        scale = best_width / self._anchor.shape[1]
        return PanelDetection(rect, scale, best_score)

    def extract_regions(self, frame: np.ndarray, detection: PanelDetection) -> PanelRegions:
        rect = detection.rect

        def crop(x1: float, y1: float, x2: float, y2: float) -> np.ndarray:
            left = rect.x + round(rect.width * x1)
            top = rect.y + round(rect.height * y1)
            right = rect.x + round(rect.width * x2)
            bottom = rect.y + round(rect.height * y2)
            return frame[top:bottom, left:right].copy()

        return PanelRegions(
            title=crop(0.18, 0.325, 0.84, 0.395),
            level=crop(0.02, 0.395, 0.19, 0.475),
            progress=crop(0.16, 0.395, 0.86, 0.475),
        )
