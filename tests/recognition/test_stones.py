"""City identification from the stone icon in the cost box."""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
import pytest

from rox_overlay.domain import CITIES, ItemType
from rox_overlay.recognition.panel import PanelDetector
from rox_overlay.recognition.stones import StoneMatcher, city_slug

ROOT = Path(__file__).parents[2]
FIXTURES = ROOT / "tests" / "fixtures"


def screenshot(city: str, item: ItemType) -> Path:
    if city == "Prontera":
        return FIXTURES / "panels" / f"{item.value}-panel.png"
    if city == "Payon":
        return FIXTURES / "screens" / f"{item.value}-15.png"
    return FIXTURES / "stones" / f"{city_slug(city)}-{item.value}.png"


CASES = [(city, item) for city in CITIES for item in ItemType]


@pytest.fixture(scope="module")
def matcher() -> StoneMatcher:
    return StoneMatcher()


def icon_of(path: Path) -> tuple[np.ndarray, int]:
    frame = cv2.imread(str(path))
    detector = PanelDetector()
    detection = detector.detect(frame)
    assert detection is not None
    icon = detector.extract_regions(frame, detection).cost_icon
    assert icon is not None
    return icon, detection.rect.width


def test_every_city_and_item_has_a_template(matcher: StoneMatcher) -> None:
    for city, item in CASES:
        assert (ROOT / "src" / "rox_overlay" / "assets" / "stones" / f"{city_slug(city)}-{item.value}.png").exists()
    assert matcher.available


@pytest.mark.parametrize(("city", "item"), CASES)
def test_identifies_city_from_screenshot(matcher: StoneMatcher, city: str, item: ItemType) -> None:
    icon, width = icon_of(screenshot(city, item))
    reading = matcher.identify(icon, item, width)
    assert reading.value == city, reading.raw


@pytest.mark.parametrize(("city", "item"), CASES)
def test_survives_shift_brightness_and_rescale(matcher: StoneMatcher, city: str, item: ItemType) -> None:
    icon, width = icon_of(screenshot(city, item))
    shifted = np.roll(icon, (2, -2), axis=(0, 1))
    brighter = cv2.convertScaleAbs(shifted, alpha=1.08, beta=6)
    # Same icon seen on a 10% larger screen: the panel is wider, so it is scaled back.
    bigger = cv2.resize(brighter, None, fx=1.1, fy=1.1, interpolation=cv2.INTER_LINEAR)
    reading = matcher.identify(bigger, item, round(width * 1.1))
    assert reading.value == city, reading.raw


def test_unknown_icon_is_not_guessed(matcher: StoneMatcher) -> None:
    noise = np.random.default_rng(1).integers(0, 255, (98, 88, 3), dtype=np.uint8)
    assert matcher.identify(noise, ItemType.WEAPON, 400).value is None
    assert matcher.identify(None, ItemType.WEAPON, 400).value is None


def test_full_pipeline_reports_city_on_payon_screenshot() -> None:
    from rox_overlay.recognition.pipeline import RecognitionPipeline
    from rox_overlay.recognition.tesseract import TesseractOcrEngine

    tesseract = ROOT / "vendor" / "tesseract"
    pipeline = RecognitionPipeline(
        PanelDetector(), TesseractOcrEngine(tesseract / "tesseract.exe", tesseract / "tessdata"), StoneMatcher()
    )
    try:
        state = pipeline.recognize(cv2.imread(str(FIXTURES / "screens" / "weapon-15.png")))
    finally:
        pipeline.close()
    assert state is not None
    assert state.city == "Payon"
