from __future__ import annotations

import ctypes
from ctypes import wintypes

from rox_overlay.hotkey import GlobalF1Hotkey


class FakeApplication:
    def __init__(self) -> None:
        self.installed: list[object] = []
        self.removed: list[object] = []

    def installNativeEventFilter(self, event_filter: object) -> None:
        self.installed.append(event_filter)

    def removeNativeEventFilter(self, event_filter: object) -> None:
        self.removed.append(event_filter)


def test_global_f1_hotkey_registers_toggles_and_unregisters() -> None:
    app = FakeApplication()
    registrations: list[tuple[object, int, int, int]] = []
    unregistrations: list[tuple[object, int]] = []
    toggles: list[bool] = []

    hotkey = GlobalF1Hotkey(
        app,  # type: ignore[arg-type]
        lambda: toggles.append(True),
        register_hotkey=lambda hwnd, hotkey_id, modifiers, key: (
            registrations.append((hwnd, hotkey_id, modifiers, key)) or True
        ),
        unregister_hotkey=lambda hwnd, hotkey_id: (
            unregistrations.append((hwnd, hotkey_id)) or True
        ),
    )
    message = wintypes.MSG()
    message.message = 0x0312
    message.wParam = 0x524F

    assert hotkey.registered

    handled = hotkey.nativeEventFilter(
        b"windows_dispatcher_MSG",
        ctypes.addressof(message),
    )
    hotkey.close()

    assert not hotkey.registered
    assert registrations == [(None, 0x524F, 0x4000, 0x70)]
    assert app.installed == [hotkey]
    assert handled == (True, 0)
    assert toggles == [True]
    assert unregistrations == [(None, 0x524F)]
    assert app.removed == [hotkey]


def test_unavailable_f1_hotkey_does_not_unregister() -> None:
    app = FakeApplication()
    unregistrations: list[tuple[object, int]] = []
    hotkey = GlobalF1Hotkey(
        app,  # type: ignore[arg-type]
        lambda: None,
        register_hotkey=lambda _hwnd, _id, _modifiers, _key: False,
        unregister_hotkey=lambda hwnd, hotkey_id: (
            unregistrations.append((hwnd, hotkey_id)) or True
        ),
    )

    hotkey.close()

    assert not hotkey.registered
    assert unregistrations == []
    assert app.removed == [hotkey]


def test_unregister_failure_remains_observable() -> None:
    app = FakeApplication()
    hotkey = GlobalF1Hotkey(
        app,  # type: ignore[arg-type]
        lambda: None,
        register_hotkey=lambda _hwnd, _id, _modifiers, _key: True,
        unregister_hotkey=lambda _hwnd, _id: False,
    )

    hotkey.close()

    assert hotkey.release_succeeded is False
    assert hotkey.registered
    assert app.removed == [hotkey]
