from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from rox_overlay.domain import ItemType
from rox_overlay.recognition.models import Rect
from rox_overlay.recognition.stability import RecognizedState
from scripts.fixture_capture import write_diagnostic


OUTPUT = Path("work/diagnostic-test.png")
METADATA = OUTPUT.with_suffix(".json")


def setup_function() -> None:
    OUTPUT.unlink(missing_ok=True)
    METADATA.unlink(missing_ok=True)


def test_does_not_save_without_explicit_confirmation() -> None:
    frame = np.zeros((50, 80, 3), dtype=np.uint8)
    assert write_diagnostic(frame, None, OUTPUT, confirmed=False) is None
    assert not OUTPUT.exists()
    assert not METADATA.exists()


def test_saves_only_png_and_minimal_recognition_json_when_confirmed() -> None:
    frame = np.zeros((50, 80, 3), dtype=np.uint8)
    reading = RecognizedState(ItemType.ARMOR, 14, 0.42, 0.88, Rect(10, 5, 50, 40))

    paths = write_diagnostic(frame, reading, OUTPUT, confirmed=True)

    assert paths == (OUTPUT, METADATA)
    payload = json.loads(METADATA.read_text(encoding="utf-8"))
    assert payload == {
        "confidence": 0.88,
        "item_type": "armor",
        "level": 14,
        "panel_rect": {"height": 40, "width": 50, "x": 10, "y": 5},
        "progress": 0.42,
    }
