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


def _register_hotkey(hwnd: object, hotkey_id: int, modifiers: int, key: int) -> bool:
    return bool(ctypes.windll.user32.RegisterHotKey(hwnd, hotkey_id, modifiers, key))


def _unregister_hotkey(hwnd: object, hotkey_id: int) -> bool:
    return bool(ctypes.windll.user32.UnregisterHotKey(hwnd, hotkey_id))


class GlobalF1Hotkey(QAbstractNativeEventFilter):
    def __init__(
        self,
        application: QCoreApplication,
        callback: Callable[[], None],
        *,
        register_hotkey: Callable[[object, int, int, int], bool] = _register_hotkey,
        unregister_hotkey: Callable[[object, int], bool] = _unregister_hotkey,
    ) -> None:
        super().__init__()
        self._application = application
        self._callback = callback
        self._unregister_hotkey = unregister_hotkey
        self._closed = False
        self.release_succeeded: bool | None = None
        application.installNativeEventFilter(self)
        self.registered = bool(
            register_hotkey(None, _HOTKEY_ID, _MOD_NOREPEAT, _VK_F1)
        )

    def nativeEventFilter(self, event_type: bytes, message: int) -> tuple[bool, int]:
        native_message = wintypes.MSG.from_address(int(message))
        if native_message.message == _WM_HOTKEY and native_message.wParam == _HOTKEY_ID:
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
