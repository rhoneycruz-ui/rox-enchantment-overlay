"""Resolution-independent enchantment panel detection."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

from .models import Rect

# Fractions of the panel rect (x1, y1, x2, y2) holding the cost stone icon.
COST_ICON_BOX = (0.05, 0.84, 0.27, 0.99)
# Panel width at which the stone templates were captured.
REFERENCE_PANEL_WIDTH = 400


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
    # Stone icon in the "Custo" box; identifies the enchanting city.
    cost_icon: np.ndarray | None = None


class PanelDetector:
    def __init__(self, anchor_template: np.ndarray | None = None) -> None:
        if anchor_template is None:
            path = Path(__file__).parents[1] / "assets" / "search-anchor.png"
            anchor_template = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
        if anchor_template is None or anchor_template.size == 0:
            raise ValueError("search anchor template is unavailable")
        self._anchor = anchor_template
        self._templates: dict[tuple[int, int], np.ndarray] = {}
        self._last: tuple[float, tuple[int, int], tuple[int, ...], float] | None = None

    # Real panels score >= 0.95 at every tested scale; round HUD buttons of the
    # closed game screen reach ~0.74, which kept a stale overlay on screen.
    _MIN_SCORE = 0.85
    _FULL_SCALES = tuple(float(scale) for scale in np.linspace(0.55, 1.6, 22))

    def _best_match(
        self,
        gray: np.ndarray,
        left: int,
        top: int,
        right: int,
        bottom: int,
        scales: tuple[float, ...],
    ) -> tuple[float, tuple[int, int] | None, int, float]:
        search = gray[top:bottom, left:right]
        best_score = -1.0
        best_location: tuple[int, int] | None = None
        best_width = 0
        best_scale = 0.0
        for scale in scales:
            width = max(12, round(self._anchor.shape[1] * scale))
            height = max(12, round(self._anchor.shape[0] * scale))
            if width >= search.shape[1] or height >= search.shape[0]:
                continue
            template = self._template_for(width, height)
            result = cv2.matchTemplate(search, template, cv2.TM_CCOEFF_NORMED)
            _, score, _, location = cv2.minMaxLoc(result)
            if score > best_score:
                best_score = float(score)
                best_location = (location[0] + left, location[1] + top)
                best_width = width
                best_scale = scale
        return best_score, best_location, best_width, best_scale

    def _template_for(self, width: int, height: int) -> np.ndarray:
        key = (width, height)
        template = self._templates.get(key)
        if template is None:
            template = cv2.resize(self._anchor, key, interpolation=cv2.INTER_AREA)
            self._templates[key] = template
        return template

    def detect(self, frame: np.ndarray) -> PanelDetection | None:
        if frame.size == 0 or frame.ndim not in (2, 3):
            return None
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if frame.ndim == 3 else frame
        frame_height, frame_width = gray.shape

        match: tuple[float, tuple[int, int] | None, int, float] | None = None
        if self._last is not None and self._last[2] == gray.shape:
            # Fast path: the panel rarely moves, so look near the last hit at the
            # last scale before paying for the full 22-scale, half-screen search.
            last_scale, (last_x, last_y), _, last_score = self._last
            margin = max(24, round(self._anchor.shape[1] * last_scale * 1.5))
            local = self._best_match(
                gray,
                max(0, last_x - margin),
                max(0, last_y - margin),
                min(frame_width, last_x + margin + round(self._anchor.shape[1] * last_scale * 1.1)),
                min(frame_height, last_y + margin + round(self._anchor.shape[0] * last_scale * 1.1)),
                (last_scale * 0.97, last_scale, last_scale * 1.03),
            )
            # Only trust the shortcut when it is about as good as the last full hit.
            if local[1] is not None and local[0] >= max(self._MIN_SCORE, last_score - 0.08):
                match = local
        if match is None:
            search_x = round(frame_width * 0.52) if frame_width / frame_height > 1.2 else 0
            match = self._best_match(gray, search_x, 0, frame_width, frame_height, self._FULL_SCALES)

        best_score, best_location, best_width, best_scale = match
        if best_location is None or best_score < self._MIN_SCORE:
            self._last = None
            return None
        self._last = (best_scale, best_location, gray.shape, best_score)

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
            title=crop(0.22, 0.34, 0.79, 0.38),
            level=crop(0.01, 0.40, 0.17, 0.47),
            progress=crop(0.16, 0.395, 0.86, 0.475),
            cost_icon=crop(*COST_ICON_BOX),
        )
