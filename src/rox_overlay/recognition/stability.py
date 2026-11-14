"""Temporal stabilization for noisy visual readings."""

from __future__ import annotations

from collections import Counter, deque
from dataclasses import dataclass, replace
from statistics import median

from rox_overlay.domain import ItemType

from .models import Rect


@dataclass(frozen=True)
class RecognizedState:
    item_type: ItemType
    level: int
    progress: float
    confidence: float
    panel_rect: Rect
    city: str | None = None  # detected from the cost stone; None = not identified


@dataclass(frozen=True)
class StableState:
    reading: RecognizedState | None
    visible: bool


class ReadingStabilizer:
    def __init__(
        self,
        *,
        window_size: int = 7,
        publish_after: int = 3,
        hide_after: int = 5,
        hide_after_absent: int = 2,
    ) -> None:
        self._readings: deque[RecognizedState] = deque(maxlen=window_size)
        self._candidate_key: tuple[ItemType, int] | None = None
        self._candidate_count = 0
        self._publish_after = publish_after
        self._hide_after = hide_after
        # The panel template vanishing is strong evidence the menu closed, so it
        # hides sooner than an unreadable-but-present panel (which may just blink).
        self._hide_after_absent = hide_after_absent
        self._absent_count = 0
        self._invalid_count = 0
        self._published: RecognizedState | None = None

    def push(self, reading: RecognizedState) -> StableState:
        key = (reading.item_type, reading.level)
        published_key = (
            (self._published.item_type, self._published.level)
            if self._published is not None
            else None
        )
        self._absent_count = 0
        if published_key is not None and key != published_key:
            self._invalid_count += 1
        else:
            self._invalid_count = 0
        if key != self._candidate_key:
            self._candidate_key = key
            self._candidate_count = 1
            self._readings.clear()
        else:
            self._candidate_count += 1
        self._readings.append(reading)

        if self._candidate_count >= self._publish_after:
            progress = float(median(item.progress for item in self._readings))
            confidence = float(median(item.confidence for item in self._readings))
            cities = Counter(item.city for item in self._readings if item.city is not None)
            city = cities.most_common(1)[0][0] if cities else None
            self._published = replace(reading, progress=progress, confidence=confidence, city=city)
            self._invalid_count = 0
        elif self._invalid_count >= self._hide_after:
            self._published = None

        return StableState(self._published, self._published is not None)

    def mark_invalid(self, *, panel_absent: bool = False) -> StableState:
        self._invalid_count += 1
        self._absent_count = self._absent_count + 1 if panel_absent else 0
        if self._invalid_count >= self._hide_after or self._absent_count >= self._hide_after_absent:
            self._published = None
            self._candidate_key = None
            self._candidate_count = 0
            self._readings.clear()
        return StableState(self._published, self._published is not None)
