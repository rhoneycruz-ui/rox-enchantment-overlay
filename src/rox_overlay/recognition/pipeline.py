"""Composition of panel, OCR and progress recognition for one frame."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

import cv2
import numpy as np

from rox_overlay.domain import ItemType

from .models import FieldReading, OcrEngine
from .panel import PanelDetector
from .progress import read_progress
from .stability import RecognizedState
from .stones import StoneMatcher
from .text import read_item_type, read_level


class RecognitionPipeline:
    _TITLE_CACHE_MAX_USES = 5

    def __init__(
        self,
        panel_detector: PanelDetector,
        ocr: OcrEngine,
        stone_matcher: StoneMatcher | None = None,
    ) -> None:
        self._panel_detector = panel_detector
        self._stones = stone_matcher
        self._ocr = ocr
        self._title_cache: tuple[np.ndarray, FieldReading[ItemType]] | None = None
        self._title_cache_uses = 0
        self._level_cache: tuple[np.ndarray, FieldReading[int]] | None = None
        self._executor: ThreadPoolExecutor | None = None
        self.panel_absent = False

    def _parallel_executor(self) -> ThreadPoolExecutor:
        # Reused across frames instead of creating two threads every tick.
        if self._executor is None:
            self._executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="rox-ocr")
        return self._executor

    def close(self) -> None:
        if self._executor is not None:
            self._executor.shutdown(wait=False, cancel_futures=True)
            self._executor = None

    @staticmethod
    def _fingerprint(image: np.ndarray) -> np.ndarray:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if image.ndim == 3 else image
        compact = cv2.resize(gray, (96, 24), interpolation=cv2.INTER_AREA)
        return compact >= float(compact.mean())

    @staticmethod
    def _matches(left: np.ndarray, right: np.ndarray) -> bool:
        return left.shape == right.shape and float(np.mean(left != right)) <= 0.03

    def recognize(self, frame: np.ndarray) -> RecognizedState | None:
        detection = self._panel_detector.detect(frame)
        self.panel_absent = detection is None
        if detection is None:
            return None
        regions = self._panel_detector.extract_regions(frame, detection)
        title_fingerprint = self._fingerprint(regions.title)
        level_fingerprint = self._fingerprint(regions.level)
        item_type = (
            self._title_cache[1]
            if self._title_cache is not None
            and self._matches(title_fingerprint, self._title_cache[0])
            and self._title_cache_uses < self._TITLE_CACHE_MAX_USES
            else None
        )
        used_cached_title = item_type is not None
        if used_cached_title:
            self._title_cache_uses += 1
        level = (
            self._level_cache[1]
            if self._level_cache is not None
            and self._matches(level_fingerprint, self._level_cache[0])
            else None
        )
        if item_type is None and level is None and getattr(self._ocr, "supports_parallel", False):
            executor = self._parallel_executor()
            item_future = executor.submit(read_item_type, regions.title, self._ocr)
            level_future = executor.submit(read_level, regions.level, self._ocr)
            item_type, level = item_future.result(), level_future.result()
        else:
            if item_type is None:
                item_type = read_item_type(regions.title, self._ocr)
            if level is None:
                level = read_level(regions.level, self._ocr)
        if item_type.value is not None:
            self._title_cache = (title_fingerprint, item_type)
            if not used_cached_title:
                self._title_cache_uses = 0
        if level.value is not None:
            self._level_cache = (level_fingerprint, level)
        progress = read_progress(regions.progress)
        if item_type.value is None or level.value is None or progress.value is None:
            return None
        confidence = min(
            detection.confidence,
            item_type.confidence,
            level.confidence,
            progress.confidence,
        )
        city = (
            self._stones.identify(regions.cost_icon, item_type.value, detection.rect.width).value
            if self._stones is not None
            else None
        )
        return RecognizedState(
            item_type=item_type.value,
            level=level.value,
            progress=progress.value,
            confidence=confidence,
            panel_rect=detection.rect,
            city=city,
        )

