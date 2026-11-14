from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import numpy as np
from PySide6.QtWidgets import QApplication, QPushButton

from rox_overlay.app import build_application
from rox_overlay.capture.base import WindowInfo
from rox_overlay.config import ConfigStore
from rox_overlay.recognition.models import Rect


class FakeDiscovery:
    def list_windows(self) -> list[WindowInfo]:
        return []

    def reacquire(self, previous: WindowInfo) -> WindowInfo | None:
        return None


class FakeCapture:
    def capture(self, window: WindowInfo) -> np.ndarray | None:
        return None


class FakePipeline:
    def recognize(self, frame: np.ndarray):
        return None


class FakeHotkey:
    def __init__(self, _app: QApplication, callback) -> None:
        self.registered = True
        self.callback = callback
        self.closed = False

    def trigger(self) -> None:
        self.callback()

    def close(self) -> None:
        self.closed = True
        self.registered = False


def test_build_application_wires_components_and_shutdown() -> None:
    app = QApplication.instance() or QApplication([])
    path = Path("work/app-wiring-config.json")
    path.unlink(missing_ok=True)
    runtime = build_application(
        app=app,
        discovery=FakeDiscovery(),
        capture=FakeCapture(),
        pipeline=FakePipeline(),
        config_store=ConfigStore(path),
        hotkey_factory=FakeHotkey,
        start_worker=False,
    )

    assert runtime.settings is not None
    assert runtime.overlay is not None
    assert runtime.controller is not None
    assert runtime.autoclick.state == "idle"
    runtime.hotkey.trigger()
    assert runtime.autoclick.state == "countdown"
    runtime.hotkey.trigger()
    assert runtime.autoclick.state == "idle"
    runtime.settings.findChild(QPushButton, "autoclickButton").click()
    runtime.shutdown()
    assert runtime.is_shutdown
    assert runtime.autoclick.state == "idle"
    assert runtime.hotkey.closed


def test_settings_changes_reach_components_and_are_saved_debounced() -> None:
    from PySide6.QtWidgets import QComboBox, QSpinBox

    from rox_overlay.config import ConfigStore

    app = QApplication.instance() or QApplication([])
    path = Path("work/app-wiring-debounce.json")
    path.unlink(missing_ok=True)
    runtime = build_application(
        app=app,
        discovery=FakeDiscovery(),
        capture=FakeCapture(),
        pipeline=FakePipeline(),
        config_store=ConfigStore(path),
        hotkey_factory=FakeHotkey,
        start_worker=False,
    )

    runtime.settings.findChild(QSpinBox, "priceSpin").setValue(777)
    runtime.settings.findChild(QComboBox, "targetCombo").setCurrentIndex(3)  # "Até o nível 4"
    runtime.settings.findChild(QSpinBox, "offsetYSpin").setValue(15)
    assert not path.exists()  # nothing written per keystroke
    assert runtime.save_timer is not None and runtime.save_timer.isActive()

    runtime.shutdown()  # flushes pending changes
    saved = ConfigStore(path).load()
    assert saved.unit_price == 777
    assert saved.target_level == 4
    assert saved.offset_y == 15
    assert runtime.controller._target_level == 4


def test_click_guard_requires_monitored_focused_game_with_cursor_inside() -> None:
    from rox_overlay.app import make_click_guard

    class Controller:
        current_window = None

    class Discovery:
        focused = True
        inside = True

        def is_foreground(self, _window) -> bool:
            return self.focused

        def cursor_inside(self, _window) -> bool:
            return self.inside

    controller, discovery = Controller(), Discovery()
    guard = make_click_guard(controller, discovery)  # type: ignore[arg-type]
    assert guard() == "no_game"
    controller.current_window = WindowInfo(1, "Game", Rect(0, 0, 10, 10))
    assert guard() == "ok"
    discovery.inside = False
    assert guard() == "outside"
    discovery.focused = False
    assert guard() == "unfocused"


def test_single_instance_mutex_detects_second_instance() -> None:
    import ctypes
    import uuid

    from rox_overlay.app import acquire_single_instance

    name = rf"Local\ROXOverlayTest.{uuid.uuid4()}"
    first = acquire_single_instance(name)
    try:
        assert first
        assert acquire_single_instance(name) is None
    finally:
        ctypes.windll.kernel32.CloseHandle(ctypes.c_void_p(first))
    second = acquire_single_instance(name)
    assert second
    ctypes.windll.kernel32.CloseHandle(ctypes.c_void_p(second))


def test_self_test_shutdown_does_not_write_settings() -> None:
    app = QApplication.instance() or QApplication([])
    path = Path("work/self-test-config.json")
    path.unlink(missing_ok=True)
    runtime = build_application(
        app=app,
        discovery=FakeDiscovery(),
        capture=FakeCapture(),
        pipeline=FakePipeline(),
        config_store=ConfigStore(path),
        hotkey_factory=FakeHotkey,
        start_worker=False,
    )
    runtime.persist_on_shutdown = False
    runtime.shutdown()

    assert not path.exists()
