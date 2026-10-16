from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import numpy as np
from PySide6.QtWidgets import QApplication

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
        start_worker=False,
    )

    assert runtime.settings is not None
    assert runtime.overlay is not None
    assert runtime.controller is not None
    runtime.shutdown()
    assert runtime.is_shutdown
