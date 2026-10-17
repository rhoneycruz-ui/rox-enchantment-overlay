from __future__ import annotations

import sys
import types

from rox_overlay.capture.base import WindowInfo
from rox_overlay.capture.windows import WindowsCaptureSource
from rox_overlay.recognition.models import Rect


class FakeControl:
    def stop(self) -> None:
        pass


class FakeWindowsCapture:
    instances: list["FakeWindowsCapture"] = []

    def __init__(self, **_kwargs) -> None:
        self.handlers = {}
        self.instances.append(self)

    def event(self, handler):
        self.handlers[handler.__name__] = handler
        return handler

    def start_free_threaded(self) -> FakeControl:
        return FakeControl()


def test_restarts_gpu_capture_after_source_window_closes(monkeypatch) -> None:
    FakeWindowsCapture.instances.clear()
    monkeypatch.setitem(
        sys.modules,
        "windows_capture",
        types.SimpleNamespace(WindowsCapture=FakeWindowsCapture),
    )
    source = WindowsCaptureSource()
    window = WindowInfo(1, "Ragnarok X", Rect(0, 0, 1280, 720))

    source.capture(window)
    assert len(FakeWindowsCapture.instances) == 1
    FakeWindowsCapture.instances[0].handlers["on_closed"]()
    source.capture(window)

    assert len(FakeWindowsCapture.instances) == 2
