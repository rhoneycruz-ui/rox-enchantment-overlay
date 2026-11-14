"""Native Windows autoclick controller with safety guards.

States emitted through ``state_changed(state, number)``:

* ``countdown`` (seconds left) – time to place the cursor on the button;
* ``running`` (clicks sent so far);
* ``waiting`` – temporarily not clicking (cursor outside the game, no game);
* ``stopped:<reason>`` – stopped by a guard (``level_up``, ``panel_closed``,
  ``game_unfocused``); the controller is idle afterwards;
* ``idle`` – stopped by the user.
"""

from __future__ import annotations

import ctypes
import logging
from collections.abc import Callable
from ctypes import wintypes

from PySide6.QtCore import QObject, QTimer, Signal, Slot

logger = logging.getLogger(__name__)

_INPUT_MOUSE = 0
_MOUSEEVENTF_LEFTDOWN = 0x0002
_MOUSEEVENTF_LEFTUP = 0x0004

GUARD_OK = "ok"
GUARD_UNFOCUSED = "unfocused"
GUARD_OUTSIDE = "outside"
GUARD_NO_GAME = "no_game"


class _MouseInput(ctypes.Structure):
    _fields_ = [
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_size_t),
    ]


class _InputUnion(ctypes.Union):
    # The union must be as large as its biggest member (KEYBDINPUT/HARDWAREINPUT
    # are smaller than MOUSEINPUT), so MOUSEINPUT alone gives the right size.
    _fields_ = [("mi", _MouseInput)]


class _Input(ctypes.Structure):
    _fields_ = [("type", wintypes.DWORD), ("union", _InputUnion)]


def send_left_click() -> None:
    """Send one left click (down + up) at the current cursor position via SendInput."""
    events = (_Input * 2)(
        _Input(_INPUT_MOUSE, _InputUnion(mi=_MouseInput(0, 0, 0, _MOUSEEVENTF_LEFTDOWN, 0, 0))),
        _Input(_INPUT_MOUSE, _InputUnion(mi=_MouseInput(0, 0, 0, _MOUSEEVENTF_LEFTUP, 0, 0))),
    )
    sent = ctypes.windll.user32.SendInput(2, events, ctypes.sizeof(_Input))
    if sent != 2:
        logger.warning("SendInput enviou %s de 2 eventos (bloqueado pelo Windows?)", sent)


class AutoClickController(QObject):
    state_changed = Signal(str, int)

    def __init__(
        self,
        click: Callable[[], None] = send_left_click,
        *,
        click_interval_ms: int = 250,
        guard: Callable[[], str] | None = None,
        countdown_seconds: int = 3,
    ) -> None:
        super().__init__()
        self._click = click
        self._guard = guard
        self._countdown_seconds = countdown_seconds
        self._remaining = 0
        self._clicks = 0
        self._baseline: tuple[object, int] | None = None
        self.stop_on_level_up = True
        self.state = "idle"
        self._countdown_timer = QTimer(self)
        self._countdown_timer.setInterval(1000)
        self._countdown_timer.timeout.connect(self._countdown_tick)
        self._click_timer = QTimer(self)
        self._click_timer.setInterval(click_interval_ms)
        self._click_timer.timeout.connect(self._click_tick)

    @property
    def active(self) -> bool:
        return self.state != "idle"

    def set_guard(self, guard: Callable[[], str] | None) -> None:
        self._guard = guard

    def set_stop_on_level_up(self, enabled: bool) -> None:
        self.stop_on_level_up = bool(enabled)

    def toggle(self) -> None:
        if self.state == "idle":
            self._remaining = self._countdown_seconds
            self._clicks = 0
            self._baseline = None
            self.state = "countdown"
            self.state_changed.emit(self.state, self._remaining)
            self._countdown_timer.start()
        else:
            self.stop()

    def stop(self, reason: str | None = None) -> None:
        self._countdown_timer.stop()
        self._click_timer.stop()
        self._remaining = 0
        self._baseline = None
        if self.state != "idle":
            self.state = "idle"
            if reason:
                logger.info("autoclique parado: %s (%d cliques)", reason, self._clicks)
                self.state_changed.emit(f"stopped:{reason}", self._clicks)
            else:
                self.state_changed.emit(self.state, 0)

    # ------------------------------------------------------------ guard hooks
    def observe_level(self, item_type: object, level: int) -> None:
        """Feed every stable reading; stops once the level goes up."""
        if not self.active:
            return
        key = (item_type, level)
        if self._baseline is None or self._baseline[0] != item_type:
            self._baseline = key
            return
        if self.stop_on_level_up and self.state in ("running", "waiting") and level > self._baseline[1]:
            self.stop("level_up")

    @Slot(object)
    def on_snapshot(self, snapshot: object) -> None:
        """Qt slot for ``RecognitionController.snapshot_ready`` (queued to this thread)."""
        estimate = getattr(snapshot, "estimate", None)
        if estimate is not None:
            self.observe_level(estimate.item_type, estimate.current_level)

    @Slot()
    def panel_closed(self) -> None:
        """The enchant menu is gone: clicking now would hit something else."""
        if self.state not in ("running", "waiting"):
            return
        status = self._guard() if self._guard is not None else GUARD_OK
        self.stop("game_unfocused" if status == GUARD_UNFOCUSED else "panel_closed")

    # --------------------------------------------------------------- timers
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
        if self.state != "idle":
            self._click_timer.start()

    def _click_tick(self) -> None:
        if self.state not in ("running", "waiting"):
            return
        status = self._guard() if self._guard is not None else GUARD_OK
        if status == GUARD_UNFOCUSED:
            self.stop("game_unfocused")
            return
        if status != GUARD_OK:
            if self.state != "waiting":
                self.state = "waiting"
                self.state_changed.emit(self.state, self._clicks)
            return
        if self.state != "running":
            self.state = "running"
        self._click()
        self._clicks += 1
        self.state_changed.emit(self.state, self._clicks)
