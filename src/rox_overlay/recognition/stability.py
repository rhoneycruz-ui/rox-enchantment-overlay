"""Temporal stabilization for noisy visual readings."""

from __future__ import annotations

from collections import deque
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


@dataclass(frozen=True)
class StableState:
    reading: RecognizedState | None
    visible: bool


class ReadingStabilizer:
    def __init__(self, *, window_size: int = 7, publish_after: int = 3, hide_after: int = 5) -> None:
        self._readings: deque[RecognizedState] = deque(maxlen=window_size)
        self._candidate_key: tuple[ItemType, int] | None = None
        self._candidate_count = 0
        self._publish_after = publish_after
        self._hide_after = hide_after
        self._invalid_count = 0
        self._published: RecognizedState | None = None

    def push(self, reading: RecognizedState) -> StableState:
        key = (reading.item_type, reading.level)
        published_key = (
            (self._published.item_type, self._published.level)
            if self._published is not None
            else None
        )
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
            self._published = replace(reading, progress=progress, confidence=confidence)
            self._invalid_count = 0
        elif self._invalid_count >= self._hide_after:
            self._published = None

        return StableState(self._published, self._published is not None)

    def mark_invalid(self) -> StableState:
        self._invalid_count += 1
        if self._invalid_count >= self._hide_after:
            self._published = None
            self._candidate_key = None
            self._candidate_count = 0
            self._readings.clear()
        return StableState(self._published, self._published is not None)
