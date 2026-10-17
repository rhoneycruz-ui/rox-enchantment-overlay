from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from rox_overlay.autoclick import AutoClickController


def test_toggle_starts_three_second_countdown_and_stops_immediately() -> None:
    QApplication.instance() or QApplication([])
    controller = AutoClickController(click=lambda: None)
    states: list[tuple[str, int]] = []
    controller.state_changed.connect(lambda state, remaining: states.append((state, remaining)))

    controller.toggle()
    controller.toggle()

    assert states == [("countdown", 3), ("idle", 0)]
    assert controller.state == "idle"


def test_clicking_starts_after_countdown_and_stops_sending_clicks() -> None:
    QApplication.instance() or QApplication([])
    clicks: list[str] = []
    controller = AutoClickController(click=lambda: clicks.append("left"))

    controller.toggle()
    controller._countdown_tick()
    controller._countdown_tick()
    assert clicks == []

    controller._countdown_tick()
    assert controller.state == "running"
    assert clicks == ["left"]

    controller._click_tick()
    assert clicks == ["left", "left"]

    controller.toggle()
    controller._click_tick()
    assert controller.state == "idle"
    assert clicks == ["left", "left"]
