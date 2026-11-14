"""End-to-end recognition on full in-game screenshots (level 15, three item types)."""

from __future__ import annotations

import math
from pathlib import Path

import cv2
import pytest

from rox_overlay.domain import CITIES, TABLES, ItemType, estimate_cost
from rox_overlay.recognition.panel import PanelDetector
from rox_overlay.recognition.pipeline import RecognitionPipeline
from rox_overlay.recognition.tesseract import TesseractOcrEngine

ROOT = Path(__file__).parents[2]
SCREENS = ROOT / "tests" / "fixtures" / "screens"
TESSERACT = ROOT / "vendor" / "tesseract" / "tesseract.exe"
TESSDATA = ROOT / "vendor" / "tesseract" / "tessdata"


@pytest.mark.parametrize(
    ("filename", "item_type", "progress"),
    [
        ("accessory-15.png", ItemType.ACCESSORY, 0.51),
        ("weapon-15.png", ItemType.WEAPON, 0.0),
        ("armor-15.png", ItemType.ARMOR, 0.045),
    ],
)
def test_recognizes_full_screenshots(filename: str, item_type: ItemType, progress: float) -> None:
    frame = cv2.imread(str(SCREENS / filename))
    assert frame is not None
    pipeline = RecognitionPipeline(PanelDetector(), TesseractOcrEngine(TESSERACT, TESSDATA))
    try:
        state = pipeline.recognize(frame)
    finally:
        pipeline.close()

    assert state is not None
    assert state.item_type is item_type
    assert state.level == 15
    assert state.progress == pytest.approx(progress, abs=0.02)


@pytest.mark.parametrize("level", range(1, 20))
def test_every_level_and_city_matches_methax_snapshot(level: int) -> None:
    import json

    snapshot = json.loads((ROOT / "tests" / "fixtures" / "methax_enchanting.json").read_text(encoding="utf-8"))
    for kind, expected in snapshot["levels"][str(level)].items():
        assert set(expected["cities"]) == set(CITIES)
        for city, site in expected["cities"].items():
            estimate = estimate_cost(ItemType(kind), level, 0.0, 88, city=city)
            assert estimate.remaining_points == expected["points"]
            assert estimate.stone_name == site["stone"]
            # The site shows fractional taps (1 decimal); the overlay rounds up to whole taps.
            per_tap = TABLES.cities[city][ItemType(kind)].stones_per_tap
            assert site["stones"] - 0.1 <= estimate.remaining_stones < site["stones"] + per_tap + 0.1, (city, kind)
            points_per_tap = TABLES.cities[city][ItemType(kind)].points_per_tap
            assert site["taps"] == pytest.approx(expected["points"] / points_per_tap, abs=0.051), (city, kind)
            assert estimate.remaining_taps == math.ceil(expected["points"] / points_per_tap)


def test_weapon_level_15_matches_methax_prontera() -> None:
    # rox.methax.com, Prontera, 15→16 from 0 exp: 5050 points, 151500 Muspellium
    # (1683.3 taps). The overlay rounds taps up, so it may be one tap (90) higher.
    estimate = estimate_cost(ItemType.WEAPON, 15, 0.0, 88)
    assert estimate.remaining_points == 5050
    assert 151500 <= estimate.remaining_stones <= 151500 + 90
    armor = estimate_cost(ItemType.ARMOR, 15, 0.0, 88)
    assert armor.remaining_stones * 88 == 13_332_000
