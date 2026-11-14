from __future__ import annotations

import json
from pathlib import Path

import cv2
import numpy as np

from rox_overlay.recognition.models import Rect
from rox_overlay.recognition.panel import PanelDetector

FIXTURE_DIR = Path(__file__).parents[1] / "fixtures" / "panels"


def _iou(left: Rect, right: Rect) -> float:
    x1 = max(left.x, right.x)
    y1 = max(left.y, right.y)
    x2 = min(left.x + left.width, right.x + right.width)
    y2 = min(left.y + left.height, right.y + right.height)
    intersection = max(0, x2 - x1) * max(0, y2 - y1)
    union = left.width * left.height + right.width * right.height - intersection
    return intersection / union


def test_detects_panel_in_real_screenshots() -> None:
    detector = PanelDetector()
    manifest = json.loads((FIXTURE_DIR / "manifest.json").read_text(encoding="utf-8"))

    for case in manifest:
        frame = cv2.imread(str(FIXTURE_DIR / case["file"]))
        detection = detector.detect(frame)
        expected = Rect(*case["rect"])

        assert detection is not None, case["file"]
        assert _iou(detection.rect, expected) >= 0.85, (case["file"], detection.rect)
        assert detection.confidence >= 0.6


def test_detects_resized_and_shifted_panel() -> None:
    detector = PanelDetector()
    panel = cv2.imread(str(FIXTURE_DIR / "armor-panel.png"))
    scaled = cv2.resize(panel, None, fx=0.75, fy=0.75, interpolation=cv2.INTER_AREA)
    frame = np.zeros((scaled.shape[0] + 80, scaled.shape[1] + 220, 3), dtype=np.uint8)
    frame[30 : 30 + scaled.shape[0], 180 : 180 + scaled.shape[1]] = scaled

    detection = detector.detect(frame)
    expected = Rect(186, 30, 301, 498)

    assert detection is not None
    assert _iou(detection.rect, expected) >= 0.85


def test_returns_none_when_panel_is_absent() -> None:
    detector = PanelDetector()
    frame = np.full((720, 1280, 3), (35, 55, 70), dtype=np.uint8)

    assert detector.detect(frame) is None


def test_extracts_non_empty_normalized_regions() -> None:
    detector = PanelDetector()
    frame = cv2.imread(str(FIXTURE_DIR / "game-full.png"))
    detection = detector.detect(frame)

    assert detection is not None
    regions = detector.extract_regions(frame, detection)
    assert regions.title.size > 0
    assert regions.level.size > 0
    assert regions.progress.size > 0
    assert regions.title.shape[1] > regions.level.shape[1]
    assert regions.progress.shape[1] > regions.level.shape[1]


def test_tracking_fast_path_matches_full_search_and_is_faster() -> None:
    import time

    frame = cv2.imread(str(FIXTURE_DIR / "game-full.png"))
    fresh = PanelDetector().detect(frame)
    tracker = PanelDetector()

    started = time.perf_counter()
    first = tracker.detect(frame)
    full_seconds = time.perf_counter() - started
    started = time.perf_counter()
    second = tracker.detect(frame)
    tracked_seconds = time.perf_counter() - started

    assert fresh is not None and first is not None and second is not None
    assert first.rect == fresh.rect
    assert _iou(second.rect, fresh.rect) >= 0.95
    assert tracked_seconds < full_seconds


def test_tracking_falls_back_when_panel_disappears() -> None:
    frame = cv2.imread(str(FIXTURE_DIR / "game-full.png"))
    tracker = PanelDetector()
    assert tracker.detect(frame) is not None

    assert tracker.detect(np.zeros_like(frame)) is None
    assert tracker.detect(frame) is not None


def test_closed_menu_hud_is_not_mistaken_for_the_panel() -> None:
    # In-game screen with the enchant menu closed: a round HUD button used to
    # score ~0.74 and keep the overlay up until OCR failed five times.
    frame = cv2.imread(str(Path(__file__).parents[1] / "fixtures" / "screens" / "closed-menu-alberta.png"))
    assert frame is not None
    assert PanelDetector().detect(frame) is None
