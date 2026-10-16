"""Capture contracts shared by native and fallback implementations."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

import numpy as np

from rox_overlay.recognition.models import Rect


@dataclass(frozen=True)
class WindowInfo:
    handle: int
    title: str
    client_rect: Rect


@runtime_checkable
class WindowDiscovery(Protocol):
    def list_windows(self) -> list[WindowInfo]: ...

    def reacquire(self, previous: WindowInfo) -> WindowInfo | None: ...


@runtime_checkable
class FrameSource(Protocol):
    def capture(self, window: WindowInfo) -> np.ndarray | None: ...

