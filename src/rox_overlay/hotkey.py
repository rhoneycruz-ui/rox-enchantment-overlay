"""Native Windows global hotkey support."""

from __future__ import annotations

import ctypes
from collections.abc import Callable
from ctypes import wintypes

from PySide6.QtCore import QAbstractNativeEventFilter, QCoreApplication

_HOTKEY_ID = 0x524F
_MOD_NOREPEAT = 0x4000
_VK_F1 = 0x70
_WM_HOTKEY = 0x0312


def virtual_key_for(name: str) -> int:
    """Map "F1".."F12" to its Windows virtual-key code."""
    if not name.startswith("F") or not name[1:].isdigit() or not 1 <= int(name[1:]) <= 12:
        raise ValueError(f"unsupported hotkey: {name!r}")
    return _VK_F1 + int(name[1:]) - 1


def _register_hotkey(hwnd: object, hotkey_id: int, modifiers: int, key: int) -> bool:
    return bool(ctypes.windll.user32.RegisterHotKey(hwnd, hotkey_id, modifiers, key))


def _unregister_hotkey(hwnd: object, hotkey_id: int) -> bool:
    return bool(ctypes.windll.user32.UnregisterHotKey(hwnd, hotkey_id))


class GlobalHotkey(QAbstractNativeEventFilter):
    def __init__(
        self,
        application: QCoreApplication,
        callback: Callable[[], None],
        *,
        key: str = "F1",
        enabled: bool = True,
        register_hotkey: Callable[[object, int, int, int], bool] = _register_hotkey,
        unregister_hotkey: Callable[[object, int], bool] = _unregister_hotkey,
    ) -> None:
        super().__init__()
        self._application = application
        self._callback = callback
        self._register_hotkey = register_hotkey
        self._unregister_hotkey = unregister_hotkey
        self._closed = False
        self.key = key
        self.release_succeeded: bool | None = None
        self.enabled = enabled
        application.installNativeEventFilter(self)
        self.registered = (
            bool(register_hotkey(None, _HOTKEY_ID, _MOD_NOREPEAT, virtual_key_for(key))) if enabled else False
        )

    def set_enabled(self, enabled: bool) -> bool:
        """Register (True) or release (False) the key; returns whether it is registered."""
        if self._closed:
            return False
        self.enabled = enabled
        if not enabled and self.registered:
            self.release_succeeded = bool(self._unregister_hotkey(None, _HOTKEY_ID))
            self.registered = not self.release_succeeded
        elif enabled and not self.registered:
            self.registered = bool(
                self._register_hotkey(None, _HOTKEY_ID, _MOD_NOREPEAT, virtual_key_for(self.key))
            )
        return self.registered

    def rebind(self, key: str) -> bool:
        """Switch to another F-key; returns whether the new key is registered."""
        vk = virtual_key_for(key)
        if self._closed:
            return False
        if self.registered:
            self.release_succeeded = bool(self._unregister_hotkey(None, _HOTKEY_ID))
            self.registered = not self.release_succeeded
        self.key = key
        if self.enabled and not self.registered:
            self.registered = bool(self._register_hotkey(None, _HOTKEY_ID, _MOD_NOREPEAT, vk))
        return self.registered

    def nativeEventFilter(self, event_type: object, message: int) -> tuple[bool, int]:
        native_message = wintypes.MSG.from_address(int(message))
        if native_message.message == _WM_HOTKEY and native_message.wParam == _HOTKEY_ID:
            if self.enabled:
                self._callback()
            return True, 0
        return False, 0

    def close(self) -> None:
        if self._closed:
            return
        if self.registered:
            self.release_succeeded = bool(self._unregister_hotkey(None, _HOTKEY_ID))
            if self.release_succeeded:
                self.registered = False
        self._application.removeNativeEventFilter(self)
        self._closed = True


GlobalF1Hotkey = GlobalHotkey
