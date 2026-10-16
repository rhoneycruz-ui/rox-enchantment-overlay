"""Composition of panel, OCR and progress recognition for one frame."""

from __future__ import annotations

import numpy as np

from .models import OcrEngine
from .panel import PanelDetector
from .progress import read_progress
from .stability import RecognizedState
from .text import read_item_type, read_level


class RecognitionPipeline:
    def __init__(self, panel_detector: PanelDetector, ocr: OcrEngine) -> None:
        self._panel_detector = panel_detector
        self._ocr = ocr

    def recognize(self, frame: np.ndarray) -> RecognizedState | None:
        detection = self._panel_detector.detect(frame)
        if detection is None:
            return None
        regions = self._panel_detector.extract_regions(frame, detection)
        item_type = read_item_type(regions.title, self._ocr)
        level = read_level(regions.level, self._ocr)
        progress = read_progress(regions.progress)
        if item_type.value is None or level.value is None or progress.value is None:
            return None
        confidence = min(
            detection.confidence,
            item_type.confidence,
            level.confidence,
            progress.confidence,
        )
        return RecognizedState(
            item_type=item_type.value,
            level=level.value,
            progress=progress.value,
            confidence=confidence,
            panel_rect=detection.rect,
        )

