"""Visible-region capture fallback based on MSS."""

from __future__ import annotations

import cv2
import mss
import numpy as np

from .base import FrameSource, WindowInfo


class MssCaptureSource:
    def capture(self, window: WindowInfo) -> np.ndarray | None:
        rect = window.client_rect
        if rect.width <= 0 or rect.height <= 0:
            return None
        monitor = {"left": rect.x, "top": rect.y, "width": rect.width, "height": rect.height}
        try:
            with mss.mss() as capture:
                bgra = np.asarray(capture.grab(monitor))
        except (mss.ScreenShotError, OSError):
            return None
        return cv2.cvtColor(bgra, cv2.COLOR_BGRA2BGR)


class CascadingFrameSource:
    def __init__(self, primary: FrameSource, fallback: FrameSource) -> None:
        self._primary = primary
        self._fallback = fallback

    def capture(self, window: WindowInfo) -> np.ndarray | None:
        frame = self._primary.capture(window)
        return frame if frame is not None else self._fallback.capture(window)

