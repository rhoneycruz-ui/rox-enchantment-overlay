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


def test_reuses_valid_ocr_when_title_and_level_pixels_are_unchanged(monkeypatch) -> None:
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
    frame = np.zeros((100, 100, 3), dtype=np.uint8)

    assert pipeline.recognize(frame) is not None
    assert pipeline.recognize(frame) is not None

    assert ocr.calls == 2


def test_revalidates_cached_title_after_five_uses(monkeypatch) -> None:
    detection = PanelDetection(PANEL_RECT, 1.0, 0.93)
    # Frame 1 reads title+level; the level is re-read every third frame (frames 4 and 7)
    # and the title after five cached uses (frame 7).
    ocr = FakeOcr(
        FieldReading("Armor Level", 0.88, "Armor Level"),
        FieldReading("14", 0.91, "14"),
        FieldReading("14", 0.91, "14"),
        FieldReading("Accessory Level", 0.88, "Accessory Level"),
        FieldReading("14", 0.91, "14"),
    )
    monkeypatch.setattr(
        "rox_overlay.recognition.pipeline.read_progress",
        lambda image: FieldReading(0.4, 0.79),
    )
    pipeline = RecognitionPipeline(FakePanelDetector(detection), ocr)  # type: ignore[arg-type]
    frame = np.zeros((100, 100, 3), dtype=np.uint8)

    results = [pipeline.recognize(frame) for _ in range(7)]

    assert results[-1] is not None
    assert results[-1].item_type is ItemType.ACCESSORY
    assert ocr.calls == 5


class SwitchingPanelDetector:
    """Same-looking level digits, but the title crop changes with the open menu."""

    def __init__(self) -> None:
        self.title_seed = 1

    def detect(self, frame: np.ndarray) -> PanelDetection | None:
        return PanelDetection(PANEL_RECT, 1.0, 0.95)

    def extract_regions(self, frame: np.ndarray, detection: PanelDetection) -> PanelRegions:
        title = np.random.default_rng(self.title_seed).integers(0, 255, (24, 180, 3), dtype=np.uint8)
        level = np.zeros((24, 50, 3), dtype=np.uint8)  # identical fingerprint for "15" and "16"
        return PanelRegions(title=title, level=level, progress=np.zeros((24, 180, 3), dtype=np.uint8))


def test_level_is_reread_when_another_menu_opens(monkeypatch) -> None:
    # Accessory at 16, then the weapon menu at 15: the old cache kept showing 16.
    monkeypatch.setattr(
        "rox_overlay.recognition.pipeline.read_progress", lambda image: FieldReading(0.4, 0.9)
    )
    detector = SwitchingPanelDetector()
    ocr = FakeOcr(
        FieldReading("Accessory Level", 0.9, "Accessory Level"),
        FieldReading("16", 0.9, "16"),
        FieldReading("Weapon Level", 0.9, "Weapon Level"),
        FieldReading("15", 0.9, "15"),
    )
    pipeline = RecognitionPipeline(detector, ocr)  # type: ignore[arg-type]
    frame = np.zeros((100, 100, 3), dtype=np.uint8)

    first = pipeline.recognize(frame)
    detector.title_seed = 2
    second = pipeline.recognize(frame)

    assert first is not None and first.level == 16
    assert second is not None and second.item_type is ItemType.WEAPON and second.level == 15


def test_level_is_reread_after_a_level_up(monkeypatch) -> None:
    # Same menu: the bar fills up, the level rises and the bar drops back to the start.
    progress = iter([0.95, 0.02])
    monkeypatch.setattr(
        "rox_overlay.recognition.pipeline.read_progress", lambda image: FieldReading(next(progress), 0.9)
    )
    ocr = FakeOcr(
        FieldReading("Accessory Level", 0.9, "Accessory Level"),
        FieldReading("15", 0.9, "15"),
        FieldReading("16", 0.9, "16"),
    )
    pipeline = RecognitionPipeline(SwitchingPanelDetector(), ocr)  # type: ignore[arg-type]
    frame = np.zeros((100, 100, 3), dtype=np.uint8)

    assert pipeline.recognize(frame).level == 15  # type: ignore[union-attr]
    after = pipeline.recognize(frame)

    assert after is not None and after.level == 16
