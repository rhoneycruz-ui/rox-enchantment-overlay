"""Native Windows autoclick controller."""

from __future__ import annotations

import ctypes
from collections.abc import Callable

from PySide6.QtCore import QObject, QTimer, Signal


_LEFT_DOWN = 0x0002
_LEFT_UP = 0x0004


def send_left_click() -> None:
    """Send one native left click at the current cursor position."""
    user32 = ctypes.windll.user32
    user32.mouse_event(_LEFT_DOWN, 0, 0, 0, 0)
    user32.mouse_event(_LEFT_UP, 0, 0, 0, 0)


class AutoClickController(QObject):
    state_changed = Signal(str, int)

    def __init__(
        self,
        click: Callable[[], None] = send_left_click,
        *,
        click_interval_ms: int = 250,
    ) -> None:
        super().__init__()
        self._click = click
        self._remaining = 0
        self.state = "idle"
        self._countdown_timer = QTimer(self)
        self._countdown_timer.setInterval(1000)
        self._countdown_timer.timeout.connect(self._countdown_tick)
        self._click_timer = QTimer(self)
        self._click_timer.setInterval(click_interval_ms)
        self._click_timer.timeout.connect(self._click_tick)

    def toggle(self) -> None:
        if self.state == "idle":
            self._remaining = 3
            self.state = "countdown"
            self.state_changed.emit(self.state, self._remaining)
            self._countdown_timer.start()
        else:
            self.stop()

    def stop(self) -> None:
        self._countdown_timer.stop()
        self._click_timer.stop()
        self._remaining = 0
        if self.state != "idle":
            self.state = "idle"
            self.state_changed.emit(self.state, 0)

    def _countdown_tick(self) -> None:
        if self.state != "countdown":
            return
        self._remaining -= 1
        if self._remaining > 0:
            self.state_changed.emit(self.state, self._remaining)
            return
        self._countdown_timer.stop()
        self.state = "running"
        self.state_changed.emit(self.state, 0)
        self._click_tick()
        self._click_timer.start()

    def _click_tick(self) -> None:
        if self.state == "running":
            self._click()
