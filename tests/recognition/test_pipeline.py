from __future__ import annotations

from collections import deque

import numpy as np

from rox_overlay.domain import ItemType
from rox_overlay.recognition.models import FieldReading, Rect
from rox_overlay.recognition.panel import PanelDetection, PanelRegions
from rox_overlay.recognition.pipeline import RecognitionPipeline


PANEL_RECT = Rect(900, 40, 400, 650)


class FakePanelDetector:
    def __init__(self, detection: PanelDetection | None) -> None:
        self.detection = detection

    def detect(self, frame: np.ndarray) -> PanelDetection | None:
        return self.detection

    def extract_regions(self, frame: np.ndarray, detection: PanelDetection) -> PanelRegions:
        crop = np.zeros((24, 180, 3), dtype=np.uint8)
        return PanelRegions(title=crop, level=crop[:, :50], progress=crop)


class FakeOcr:
    def __init__(self, *results: FieldReading[str]) -> None:
        self.results = deque(results)
        self.calls = 0

    def read_line(
        self,
        image: np.ndarray,
        *,
        languages: tuple[str, ...],
        digits_only: bool = False,
    ) -> FieldReading[str]:
        self.calls += 1
        return self.results.popleft()


def test_returns_none_without_panel() -> None:
    ocr = FakeOcr()
    pipeline = RecognitionPipeline(FakePanelDetector(None), ocr)  # type: ignore[arg-type]

    assert pipeline.recognize(np.zeros((100, 100, 3), dtype=np.uint8)) is None
    assert ocr.calls == 0


def test_returns_none_when_required_text_field_is_unknown(monkeypatch) -> None:
    detection = PanelDetection(PANEL_RECT, 1.0, 0.95)
    ocr = FakeOcr(FieldReading("Refino", 0.99, "Refino"), FieldReading("14", 0.9, "14"))
    monkeypatch.setattr(
        "rox_overlay.recognition.pipeline.read_progress",
        lambda image: FieldReading(0.4, 0.85),
    )
    pipeline = RecognitionPipeline(FakePanelDetector(detection), ocr)  # type: ignore[arg-type]

    assert pipeline.recognize(np.zeros((100, 100, 3), dtype=np.uint8)) is None


def test_composes_fields_and_uses_lowest_confidence(monkeypatch) -> None:
    detection = PanelDetection(PANEL_RECT, 1.0, 0.93)
    ocr = FakeOcr(
        FieldReading("Armor Level", 0.88, "Armor Level"),
        FieldReading("14", 0.91, "14"),
    )
    monkeypatch.setattr(
        "rox_overlay.recognition.pipeline.read_progress",
        lambda image: FieldReading(0.4, 0.79),
    )
    pipeline = RecognitionPipeline(FakePanelDetector(detection), ocr)  # type: ignore[arg-type]

    result = pipeline.recognize(np.zeros((100, 100, 3), dtype=np.uint8))

    assert result is not None
    assert result.item_type is ItemType.ARMOR
    assert result.level == 14
    assert result.progress == 0.4
    assert result.confidence == 0.79
    assert result.panel_rect == PANEL_RECT
