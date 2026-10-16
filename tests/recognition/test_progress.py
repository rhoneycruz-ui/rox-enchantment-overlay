from __future__ import annotations

import json
from pathlib import Path

import cv2
import numpy as np
import pytest

from rox_overlay.recognition.progress import read_progress


FIXTURE_DIR = Path(__file__).parents[1] / "fixtures" / "progress"


def _synthetic_bar(progress: float) -> np.ndarray:
    image = np.zeros((28, 260, 3), dtype=np.uint8)
    cv2.rectangle(image, (4, 5), (255, 23), (38, 44, 55), -1)
    inner_width = 246
    filled = round(inner_width * progress)
    if filled:
        cv2.rectangle(image, (7, 8), (7 + filled - 1, 20), (235, 205, 55), -1)
    cv2.rectangle(image, (4, 5), (255, 23), (215, 180, 120), 1)
    return image


def test_reads_progress_from_real_game_screenshots() -> None:
    manifest = json.loads((FIXTURE_DIR / "manifest.json").read_text(encoding="utf-8"))

    for case in manifest:
        image = cv2.imread(str(FIXTURE_DIR / case["file"]))
        x1, y1, x2, y2 = case["crop"]
        result = read_progress(image[y1:y2, x1:x2])

        assert result.value is not None, case["file"]
        assert case["min"] <= result.value <= case["max"], (case["file"], result)
        assert result.confidence >= 0.5


@pytest.mark.parametrize("progress", [0.0, 0.95])
def test_reads_empty_and_nearly_full_synthetic_bars(progress: float) -> None:
    result = read_progress(_synthetic_bar(progress))

    assert result.value == pytest.approx(progress, abs=0.035)


def test_rejects_image_without_track() -> None:
    result = read_progress(np.zeros((28, 260, 3), dtype=np.uint8))

    assert result.value is None
    assert result.confidence == 0


def test_rejects_detached_cyan_glow_as_fill() -> None:
    image = _synthetic_bar(0.0)
    cv2.circle(image, (170, 14), 7, (235, 205, 55), -1)

    result = read_progress(image)

    assert result.value == pytest.approx(0.0, abs=0.035)

