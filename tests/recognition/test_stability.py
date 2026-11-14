from __future__ import annotations

import pytest

from rox_overlay.domain import ItemType
from rox_overlay.recognition.models import Rect
from rox_overlay.recognition.stability import ReadingStabilizer, RecognizedState

PANEL = Rect(920, 40, 400, 650)


def reading(
    progress: float,
    *,
    item_type: ItemType = ItemType.ARMOR,
    level: int = 14,
) -> RecognizedState:
    return RecognizedState(item_type, level, progress, 0.9, PANEL)


def test_publishes_after_three_compatible_readings() -> None:
    stabilizer = ReadingStabilizer()

    assert stabilizer.push(reading(0.20)).visible is False
    assert stabilizer.push(reading(0.21)).visible is False
    state = stabilizer.push(reading(0.19))

    assert state.visible is True
    assert state.reading is not None
    assert state.reading.progress == pytest.approx(0.20)


def test_uses_median_of_seven_recent_compatible_readings() -> None:
    stabilizer = ReadingStabilizer()

    for progress in [0.20, 0.21, 0.19, 0.95, 0.22, 0.18, 0.20]:
        state = stabilizer.push(reading(progress))

    assert state.reading is not None
    assert state.reading.progress == pytest.approx(0.20)


def test_one_incompatible_frame_does_not_replace_published_state() -> None:
    stabilizer = ReadingStabilizer()
    for progress in [0.20, 0.21, 0.19]:
        stable = stabilizer.push(reading(progress))

    outlier = stabilizer.push(reading(0.8, item_type=ItemType.WEAPON))

    assert outlier == stable


def test_hides_on_fifth_invalid_frame_and_reappears_after_three_valid_frames() -> None:
    stabilizer = ReadingStabilizer()
    for progress in [0.20, 0.21, 0.19]:
        stabilizer.push(reading(progress))

    for _ in range(4):
        assert stabilizer.mark_invalid().visible is True
    hidden = stabilizer.mark_invalid()
    assert hidden.visible is False
    assert hidden.reading is None

    assert stabilizer.push(reading(0.30)).visible is False
    assert stabilizer.push(reading(0.31)).visible is False
    visible = stabilizer.push(reading(0.29))
    assert visible.visible is True
    assert visible.reading is not None
    assert visible.reading.progress == pytest.approx(0.30)


def test_hides_after_five_incompatible_readings_even_when_they_alternate() -> None:
    stabilizer = ReadingStabilizer()
    for progress in [0.20, 0.21, 0.19]:
        stabilizer.push(reading(progress))

    alternatives = [ItemType.WEAPON, ItemType.ACCESSORY] * 3
    for item_type in alternatives[:4]:
        assert stabilizer.push(reading(0.5, item_type=item_type)).visible is True
    hidden = stabilizer.push(reading(0.5, item_type=alternatives[4]))

    assert hidden.visible is False
    assert hidden.reading is None


def test_closed_menu_hides_after_two_absent_frames() -> None:
    stabilizer = ReadingStabilizer()
    for _ in range(3):
        stabilizer.push(reading(0.2))

    assert stabilizer.mark_invalid(panel_absent=True).visible is True
    assert stabilizer.mark_invalid(panel_absent=True).visible is False


def test_unreadable_but_present_panel_still_waits_five_frames() -> None:
    stabilizer = ReadingStabilizer()
    for _ in range(3):
        stabilizer.push(reading(0.2))

    for _ in range(4):
        assert stabilizer.mark_invalid().visible is True
    assert stabilizer.mark_invalid().visible is False


def test_absent_frames_must_be_consecutive() -> None:
    stabilizer = ReadingStabilizer()
    for _ in range(3):
        stabilizer.push(reading(0.2))

    stabilizer.mark_invalid(panel_absent=True)
    stabilizer.push(reading(0.2))
    assert stabilizer.mark_invalid(panel_absent=True).visible is True


def test_city_is_the_most_common_in_recent_readings() -> None:
    from dataclasses import replace

    stabilizer = ReadingStabilizer()
    for city in ("Morroc", None, "Morroc", "Payon"):
        state = stabilizer.push(replace(reading(0.2), city=city))

    assert state.reading is not None
    assert state.reading.city == "Morroc"
