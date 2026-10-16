"""Native Win32 discovery and Windows Graphics Capture adapter."""

from __future__ import annotations

import ctypes
import threading
from ctypes import wintypes
from typing import Protocol

import numpy as np

from rox_overlay.recognition.models import Rect

from .base import WindowInfo


def normalize_window_title(title: str) -> str:
    return " ".join(title.casefold().split())


class WindowBackend(Protocol):
    def handles(self) -> list[int]: ...
    def is_visible(self, handle: int) -> bool: ...
    def title(self, handle: int) -> str: ...
    def client_rect(self, handle: int) -> Rect | None: ...


class _CtypesWindowBackend:
    def __init__(self) -> None:
        self._user32 = ctypes.windll.user32

    def handles(self) -> list[int]:
        handles: list[int] = []
        callback_type = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)

        @callback_type
        def callback(handle: int, _param: int) -> bool:
            handles.append(int(handle))
            return True

        self._user32.EnumWindows(callback, 0)
        return handles

    def is_visible(self, handle: int) -> bool:
        return bool(self._user32.IsWindowVisible(handle)) and not bool(self._user32.IsIconic(handle))

    def title(self, handle: int) -> str:
        length = self._user32.GetWindowTextLengthW(handle)
        buffer = ctypes.create_unicode_buffer(length + 1)
        self._user32.GetWindowTextW(handle, buffer, len(buffer))
        return buffer.value

    def client_rect(self, handle: int) -> Rect | None:
        rect = wintypes.RECT()
        origin = wintypes.POINT(0, 0)
        if not self._user32.GetClientRect(handle, ctypes.byref(rect)):
            return None
        if not self._user32.ClientToScreen(handle, ctypes.byref(origin)):
            return None
        width, height = rect.right - rect.left, rect.bottom - rect.top
        return Rect(origin.x, origin.y, width, height) if width > 0 and height > 0 else None


class Win32WindowDiscovery:
    def __init__(self, backend: WindowBackend | None = None) -> None:
        self._backend = backend or _CtypesWindowBackend()

    def list_windows(self) -> list[WindowInfo]:
        windows: list[WindowInfo] = []
        for handle in self._backend.handles():
            if not self._backend.is_visible(handle):
                continue
            title = self._backend.title(handle).strip()
            rect = self._backend.client_rect(handle)
            if title and rect is not None:
                windows.append(WindowInfo(handle, title, rect))
        return windows

    def reacquire(self, previous: WindowInfo) -> WindowInfo | None:
        windows = self.list_windows()
        same_handle = next((window for window in windows if window.handle == previous.handle), None)
        if same_handle is not None:
            return same_handle
        wanted = normalize_window_title(previous.title)
        return next((window for window in windows if normalize_window_title(window.title) == wanted), None)


class WindowsCaptureSource:
    """Keeps the newest frame from a Windows Graphics Capture session."""

    def __init__(self) -> None:
        self._title: str | None = None
        self._session = None
        self._control = None
        self._frame: np.ndarray | None = None
        self._lock = threading.Lock()

    def _start_session(self, title: str) -> None:
        self.close()
        from windows_capture import WindowsCapture

        session = WindowsCapture(
            cursor_capture=False,
            draw_border=False,
            minimum_update_interval=100,
            window_name=title,
        )

        @session.event
        def on_frame_arrived(frame, _control) -> None:
            with self._lock:
                self._frame = frame.convert_to_bgr().frame_buffer.copy()

        @session.event
        def on_closed() -> None:
            with self._lock:
                self._frame = None

        self._session = session
        self._control = session.start_free_threaded()
        self._title = title

    def capture(self, window: WindowInfo) -> np.ndarray | None:
        if self._title != window.title or self._control is None:
            try:
                self._start_session(window.title)
            except Exception:
                self.close()
                return None
        with self._lock:
            return None if self._frame is None else self._frame.copy()

    def close(self) -> None:
        control, self._control = self._control, None
        if control is not None:
            try:
                control.stop()
            except Exception:
                pass
        self._session = None
        self._title = None
        with self._lock:
            self._frame = None

