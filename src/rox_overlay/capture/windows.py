"""Native Win32 discovery and Windows Graphics Capture adapter."""

from __future__ import annotations

import ctypes
import logging
import os
import threading
import time
from collections.abc import Callable
from ctypes import wintypes
from typing import Protocol

import numpy as np

from rox_overlay.recognition.models import Rect

from .base import WindowInfo

logger = logging.getLogger(__name__)


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

    def dpi_scale(self, handle: int) -> float:
        try:
            dpi = int(self._user32.GetDpiForWindow(handle))
        except (AttributeError, OSError):
            dpi = 96
        return max(1.0, dpi / 96.0) if dpi > 0 else 1.0

    def is_window(self, handle: int) -> bool:
        return bool(self._user32.IsWindow(handle))

    def foreground_handle(self) -> int:
        return int(self._user32.GetForegroundWindow() or 0)

    def process_id(self, handle: int) -> int:
        pid = wintypes.DWORD(0)
        self._user32.GetWindowThreadProcessId(handle, ctypes.byref(pid))
        return int(pid.value)

    def cursor_position(self) -> tuple[int, int] | None:
        point = wintypes.POINT()
        if not self._user32.GetCursorPos(ctypes.byref(point)):
            return None
        return int(point.x), int(point.y)

    def monitor_origin(self, handle: int) -> tuple[int, int]:
        class MonitorInfo(ctypes.Structure):
            _fields_ = [
                ("cbSize", wintypes.DWORD),
                ("rcMonitor", wintypes.RECT),
                ("rcWork", wintypes.RECT),
                ("dwFlags", wintypes.DWORD),
            ]

        monitor = self._user32.MonitorFromWindow(handle, 2)
        info = MonitorInfo()
        info.cbSize = ctypes.sizeof(info)
        if monitor and self._user32.GetMonitorInfoW(monitor, ctypes.byref(info)):
            return int(info.rcMonitor.left), int(info.rcMonitor.top)
        return 0, 0


class Win32WindowDiscovery:
    def __init__(self, backend: WindowBackend | None = None) -> None:
        self._backend = backend or _CtypesWindowBackend()
        self._own_pid = os.getpid()

    def _optional(self, name: str) -> Callable[..., object] | None:
        reader = getattr(self._backend, name, None)
        return reader if callable(reader) else None

    def _is_own_window(self, handle: int) -> bool:
        reader = self._optional("process_id")
        return reader is not None and reader(handle) == self._own_pid

    def describe(self, handle: int) -> WindowInfo | None:
        """Current geometry of one window, or None if it is gone, hidden or untitled."""
        is_window = self._optional("is_window")
        if is_window is not None and not is_window(handle):
            return None
        if not self._backend.is_visible(handle):
            return None
        title = self._backend.title(handle).strip()
        rect = self._backend.client_rect(handle)
        if not title or rect is None:
            return None
        dpi_reader = self._optional("dpi_scale")
        origin_reader = self._optional("monitor_origin")
        dpi_scale = float(dpi_reader(handle)) if dpi_reader is not None else 1.0  # type: ignore[arg-type]
        origin: tuple[int, int] = origin_reader(handle) if origin_reader is not None else (0, 0)  # type: ignore[assignment]
        monitor_x, monitor_y = origin
        return WindowInfo(handle, title, rect, dpi_scale, monitor_x, monitor_y)

    def list_windows(self) -> list[WindowInfo]:
        windows: list[WindowInfo] = []
        for handle in self._backend.handles():
            if self._is_own_window(handle):
                continue
            window = self.describe(handle)
            if window is not None:
                windows.append(window)
        return windows

    def reacquire(self, previous: WindowInfo) -> WindowInfo | None:
        if self._optional("is_window") is not None:
            # Fast path: the same window is still alive (no full enumeration per frame).
            same_handle = self.describe(previous.handle)
            if same_handle is not None:
                return same_handle
            windows = self.list_windows()
        else:
            windows = self.list_windows()
            match = next((window for window in windows if window.handle == previous.handle), None)
            if match is not None:
                return match
        wanted = normalize_window_title(previous.title)
        return next(
            (window for window in windows if normalize_window_title(window.title) == wanted),
            None,
        )

    def title_count(self, title: str) -> int:
        wanted = normalize_window_title(title)
        return sum(1 for window in self.list_windows() if normalize_window_title(window.title) == wanted)

    def is_foreground(self, window: WindowInfo) -> bool:
        """True when the game (or one of this app's own windows) has focus.

        Backends that cannot tell report True, preserving the old behaviour.
        """
        reader = self._optional("foreground_handle")
        if reader is None:
            return True
        foreground = int(reader())  # type: ignore[call-overload]
        if foreground == 0:
            return False
        return foreground == window.handle or self._is_own_window(foreground)

    def cursor_inside(self, window: WindowInfo) -> bool:
        reader = self._optional("cursor_position")
        if reader is None:
            return True
        position = reader()
        if not isinstance(position, tuple):
            return False
        x, y = int(position[0]), int(position[1])
        rect = window.client_rect
        return rect.x <= x < rect.x + rect.width and rect.y <= y < rect.y + rect.height


class WindowsCaptureSource:
    """Keeps the newest frame from a Windows Graphics Capture session."""

    def __init__(self, title_count: Callable[[str], int] | None = None) -> None:
        # Windows Graphics Capture (via windows-capture) can only target a window by
        # title. When two windows share the title (e.g. two game clients) it could
        # pick the wrong one, so we decline and let the rect-based fallback capture.
        self._title_count = title_count
        self._ambiguous_cache: tuple[str, float, bool] | None = None
        self._title: str | None = None
        self._session = None
        self._control = None
        self._frame: np.ndarray | None = None
        self._closed = True
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
                self._closed = True

        self._session = session
        with self._lock:
            self._closed = False
        self._control = session.start_free_threaded()
        self._title = title

    _AMBIGUITY_RECHECK_SECONDS = 2.0

    def _title_is_ambiguous(self, title: str) -> bool:
        if self._title_count is None:
            return False
        now = time.monotonic()
        cached = self._ambiguous_cache
        if cached is not None and cached[0] == title and now - cached[1] < self._AMBIGUITY_RECHECK_SECONDS:
            return cached[2]
        ambiguous = self._title_count(title) > 1
        self._ambiguous_cache = (title, now, ambiguous)
        return ambiguous

    def capture(self, window: WindowInfo) -> np.ndarray | None:
        if self._title_is_ambiguous(window.title):
            if self._control is not None:
                logger.info("título de janela duplicado; usando captura por região")
                self.close()
            return None
        with self._lock:
            closed = self._closed
        if self._title != window.title or self._control is None or closed:
            try:
                self._start_session(window.title)
            except Exception:
                logger.warning("falha ao iniciar a captura nativa da janela", exc_info=True)
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
                logger.debug("erro ao encerrar a captura nativa", exc_info=True)
        self._session = None
        self._title = None
        with self._lock:
            self._frame = None
            self._closed = True

