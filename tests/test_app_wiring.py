from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import numpy as np
from PySide6.QtWidgets import QApplication
from PySide6.QtWidgets import QPushButton

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
