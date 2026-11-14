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


def _running(controller: AutoClickController) -> None:
    controller.toggle()
    for _ in range(3):
        controller._countdown_tick()


def test_send_input_structure_matches_windows_abi() -> None:
    import ctypes

    from rox_overlay.autoclick import _Input

    assert ctypes.sizeof(_Input) == (40 if ctypes.sizeof(ctypes.c_void_p) == 8 else 28)


def test_waits_while_cursor_outside_and_stops_when_game_loses_focus() -> None:
    QApplication.instance() or QApplication([])
    clicks: list[str] = []
    guard = {"value": "outside"}
    states: list[str] = []
    controller = AutoClickController(click=lambda: clicks.append("left"), guard=lambda: guard["value"])
    controller.state_changed.connect(lambda state, _n: states.append(state))

    _running(controller)
    assert clicks == []
    assert controller.state == "waiting"

    guard["value"] = "ok"
    controller._click_tick()
    assert clicks == ["left"]

    guard["value"] = "unfocused"
    controller._click_tick()
    assert controller.state == "idle"
    assert states[-1] == "stopped:game_unfocused"
    assert clicks == ["left"]


def test_stops_on_level_up_and_when_panel_closes() -> None:
    QApplication.instance() or QApplication([])
    controller = AutoClickController(click=lambda: None, guard=lambda: "ok")
    states: list[str] = []
    controller.state_changed.connect(lambda state, _n: states.append(state))

    _running(controller)
    controller.observe_level("armor", 14)
    controller.observe_level("armor", 14)
    assert controller.state == "running"
    controller.observe_level("armor", 15)
    assert states[-1] == "stopped:level_up"

    _running(controller)
    controller.panel_closed()
    assert states[-1] == "stopped:panel_closed"


def test_level_up_stop_can_be_disabled() -> None:
    QApplication.instance() or QApplication([])
    controller = AutoClickController(click=lambda: None, guard=lambda: "ok")
    controller.set_stop_on_level_up(False)

    _running(controller)
    controller.observe_level("armor", 14)
    controller.observe_level("armor", 15)

    assert controller.state == "running"
    controller.stop()
