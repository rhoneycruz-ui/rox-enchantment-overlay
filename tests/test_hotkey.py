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


def test_rebind_switches_to_another_function_key() -> None:
    app = FakeApplication()
    registrations: list[int] = []
    unregistrations: list[int] = []
    hotkey = GlobalF1Hotkey(
        app,  # type: ignore[arg-type]
        lambda: None,
        register_hotkey=lambda _hwnd, _id, _modifiers, key: registrations.append(key) or True,
        unregister_hotkey=lambda _hwnd, hotkey_id: unregistrations.append(hotkey_id) or True,
    )

    assert hotkey.rebind("F8")
    assert registrations == [0x70, 0x77]
    assert unregistrations == [0x524F]
    assert hotkey.key == "F8"


def test_rejects_unknown_keys() -> None:
    import pytest

    from rox_overlay.hotkey import virtual_key_for

    assert virtual_key_for("F12") == 0x7B
    with pytest.raises(ValueError):
        virtual_key_for("F13")


def test_disabled_hotkey_is_not_registered_until_enabled() -> None:
    from PySide6.QtCore import QCoreApplication

    from rox_overlay.hotkey import GlobalHotkey

    app = QCoreApplication.instance() or QCoreApplication([])
    calls: list[str] = []
    hotkey = GlobalHotkey(
        app,
        lambda: None,
        key="F2",
        enabled=False,
        register_hotkey=lambda *args: calls.append("register") or True,
        unregister_hotkey=lambda *args: calls.append("unregister") or True,
    )
    assert hotkey.registered is False and calls == []
    assert hotkey.rebind("F3") is False and calls == []  # stays free while disabled

    assert hotkey.set_enabled(True) is True
    assert hotkey.set_enabled(False) is False
    assert calls == ["register", "unregister"]
    hotkey.close()
