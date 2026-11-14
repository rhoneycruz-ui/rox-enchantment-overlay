"""Identify the enchanting city from the stone icon in the panel's cost box.

Each city consumes a different stone (Prontera: Muspellium; the others: one
enchantment stone per item type), so the icon tells which NPC is open. The
item type is already known from the title, so only that type's stones compete.
"""

from __future__ import annotations

import logging
from pathlib import Path

import cv2
import numpy as np

from rox_overlay.domain import CITIES, ItemType

from .models import FieldReading
from .panel import REFERENCE_PANEL_WIDTH

logger = logging.getLogger(__name__)

# Template = stone body only: it skips the "owned/needed" count printed over the
# bottom-right corner and leaves a few pixels around it to absorb small shifts.
TEMPLATE_BOX = (18, 12, 72, 58)  # x1, y1, x2, y2 inside the reference cost icon crop
MIN_SCORE = 0.90
MIN_MARGIN = 0.05


def city_slug(city: str) -> str:
    return city.lower().replace(" ", "-")


def default_template_dir() -> Path:
    return Path(__file__).parents[1] / "assets" / "stones"


def template_from_icon(icon: np.ndarray) -> np.ndarray:
    x1, y1, x2, y2 = TEMPLATE_BOX
    return icon[y1:y2, x1:x2].copy()


class StoneMatcher:
    def __init__(self, template_dir: Path | None = None) -> None:
        directory = template_dir or default_template_dir()
        self._templates: dict[ItemType, dict[str, np.ndarray]] = {item: {} for item in ItemType}
        for city in CITIES:
            for item in ItemType:
                path = directory / f"{city_slug(city)}-{item.value}.png"
                image = cv2.imread(str(path), cv2.IMREAD_COLOR)
                if image is None:
                    logger.warning("molde de pedra ausente: %s", path.name)
                    continue
                self._templates[item][city] = image

    @property
    def available(self) -> bool:
        return any(self._templates.values())

    def identify(self, icon: np.ndarray | None, item_type: ItemType, panel_width: int) -> FieldReading[str]:
        """Return the city whose stone matches clearly, or an empty reading."""
        candidates = self._templates.get(item_type, {})
        if icon is None or icon.size == 0 or len(candidates) == 0:
            return FieldReading(None, 0.0)
        if panel_width > 0 and panel_width != REFERENCE_PANEL_WIDTH:
            factor = REFERENCE_PANEL_WIDTH / panel_width
            icon = cv2.resize(icon, None, fx=factor, fy=factor, interpolation=cv2.INTER_AREA)
        scores: list[tuple[float, str]] = []
        for city, template in candidates.items():
            if icon.shape[0] < template.shape[0] or icon.shape[1] < template.shape[1]:
                continue
            score = float(cv2.matchTemplate(icon, template, cv2.TM_CCOEFF_NORMED).max())
            scores.append((score, city))
        if not scores:
            return FieldReading(None, 0.0)
        scores.sort(reverse=True)
        best_score, best_city = scores[0]
        second = scores[1][0] if len(scores) > 1 else -1.0
        raw = ", ".join(f"{city}={score:.2f}" for score, city in scores[:3])
        if best_score < MIN_SCORE or best_score - second < MIN_MARGIN:
            return FieldReading(None, best_score, raw)
        return FieldReading(best_city, best_score, raw)
