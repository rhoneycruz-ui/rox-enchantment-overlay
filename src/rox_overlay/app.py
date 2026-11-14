"""Application composition and executable entry point."""

from __future__ import annotations

import logging
import os
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from PySide6.QtCore import QMetaObject, Qt, QThread, QTimer
from PySide6.QtWidgets import QApplication, QMessageBox

from rox_overlay import __version__
from rox_overlay.autoclick import GUARD_NO_GAME, GUARD_OK, GUARD_OUTSIDE, GUARD_UNFOCUSED, AutoClickController
from rox_overlay.capture.base import FrameSource, WindowDiscovery
from rox_overlay.capture.fallback import CascadingFrameSource, MssCaptureSource
from rox_overlay.capture.windows import Win32WindowDiscovery, WindowsCaptureSource
from rox_overlay.config import ConfigStore
from rox_overlay.controller import RecognitionController
from rox_overlay.diagnostics import configure_logging
from rox_overlay.hotkey import GlobalHotkey
from rox_overlay.recognition.panel import PanelDetector
from rox_overlay.recognition.pipeline import RecognitionPipeline
from rox_overlay.recognition.stones import StoneMatcher
from rox_overlay.recognition.tesseract import TesseractOcrEngine
from rox_overlay.ui.overlay import OverlayWindow
from rox_overlay.ui.settings import SettingsWindow
from rox_overlay.ui.tray import TrayController, app_icon

logger = logging.getLogger(__name__)

SAVE_DEBOUNCE_MS = 600


def _resource_root() -> Path:
    frozen_root = getattr(sys, "_MEIPASS", None)
    return Path(frozen_root) if frozen_root else Path(__file__).parents[2]


@dataclass
class ApplicationRuntime:
    app: QApplication
    controller: RecognitionController
    overlay: OverlayWindow
    settings: SettingsWindow
    autoclick: AutoClickController
    hotkey: GlobalHotkey
    tray: TrayController
    config_store: ConfigStore
    worker: QThread | None = None
    capture: FrameSource | None = None
    pipeline: RecognitionPipeline | None = None
    save_timer: QTimer | None = None
    persist_on_shutdown: bool = True
    is_shutdown: bool = False

    def flush_config(self) -> None:
        if self.save_timer is not None:
            self.save_timer.stop()
        try:
            self.config_store.save(self.settings.current_config())
        except OSError:
            logger.exception("não foi possível salvar a configuração")

    def shutdown(self) -> None:
        if self.is_shutdown:
            return
        if self.persist_on_shutdown:
            self.flush_config()
        elif self.save_timer is not None:
            self.save_timer.stop()
        self.hotkey.close()
        self.autoclick.stop()
        if self.worker is not None and self.worker.isRunning():
            QMetaObject.invokeMethod(
                self.controller,
                "stop",
                Qt.ConnectionType.BlockingQueuedConnection,
            )
            self.worker.quit()
            self.worker.wait(3000)
        else:
            self.controller.stop()
        for resource in (self.capture, self.pipeline):
            close = getattr(resource, "close", None)
            if callable(close):
                close()
        self.overlay.hide()
        self.tray.hide()
        self.is_shutdown = True
        logger.info("aplicativo encerrado")


def make_click_guard(
    controller: RecognitionController, discovery: WindowDiscovery
) -> Callable[[], str]:
    """Autoclick only fires into the monitored game, focused, with the cursor inside it."""

    def guard() -> str:
        window = controller.current_window
        if window is None:
            return GUARD_NO_GAME
        is_foreground = getattr(discovery, "is_foreground", None)
        if callable(is_foreground) and not is_foreground(window):
            return GUARD_UNFOCUSED
        cursor_inside = getattr(discovery, "cursor_inside", None)
        if callable(cursor_inside) and not cursor_inside(window):
            return GUARD_OUTSIDE
        return GUARD_OK

    return guard


def build_application(
    *,
    app: QApplication | None = None,
    discovery: WindowDiscovery | None = None,
    capture: FrameSource | None = None,
    pipeline: RecognitionPipeline | None = None,
    config_store: ConfigStore | None = None,
    hotkey_factory: Callable[..., GlobalHotkey] = GlobalHotkey,
    start_worker: bool = True,
) -> ApplicationRuntime:
    qt_app = cast(QApplication, app or QApplication.instance() or QApplication(sys.argv))
    qt_app.setApplicationName("ROX Enchantment Overlay")
    qt_app.setApplicationVersion(__version__)
    qt_app.setWindowIcon(app_icon())
    qt_app.setQuitOnLastWindowClosed(False)
    store = config_store or ConfigStore()
    config = store.load()
    window_discovery = discovery or Win32WindowDiscovery()
    title_count = getattr(window_discovery, "title_count", None)
    frame_source = capture or CascadingFrameSource(
        WindowsCaptureSource(title_count if callable(title_count) else None),
        MssCaptureSource(),
    )

    if pipeline is None:
        root = _resource_root()
        ocr = TesseractOcrEngine(
            root / "vendor" / "tesseract" / "tesseract.exe",
            root / "vendor" / "tesseract" / "tessdata",
        )
        pipeline = RecognitionPipeline(PanelDetector(), ocr, StoneMatcher())

    controller = RecognitionController(
        frame_source,
        pipeline,
        unit_price=config.unit_price,
        discovery=window_discovery,
    )
    controller.set_target_level(config.target_level)
    controller.set_city(config.city)
    controller.set_auto_city(config.auto_city)
    overlay = OverlayWindow()
    overlay.set_opacity(config.opacity_percent)
    overlay.set_offset(config.offset_x, config.offset_y)
    settings = SettingsWindow(window_discovery, config)
    autoclick = AutoClickController(guard=make_click_guard(controller, window_discovery))
    autoclick.set_stop_on_level_up(config.autoclick_stop_on_level_up)
    try:
        hotkey = hotkey_factory(qt_app, autoclick.toggle, key=config.hotkey, enabled=config.autoclick_enabled)
    except TypeError:  # factories without key/enabled support (tests, older adapters)
        hotkey = hotkey_factory(qt_app, autoclick.toggle)
    settings.set_hotkey_available(hotkey.registered)
    tray = TrayController(settings)
    worker = QThread() if start_worker else None
    if worker is not None:
        worker.setObjectName("rox-recognition")
        controller.moveToThread(worker)
        worker.start()

    settings.window_selected.connect(controller.start)
    settings.unit_price_changed.connect(controller.set_unit_price)
    settings.target_level_changed.connect(controller.set_target_level)
    settings.city_changed.connect(controller.set_city)
    settings.auto_city_changed.connect(controller.set_auto_city)
    settings.opacity_changed.connect(overlay.set_opacity)
    settings.overlay_offset_changed.connect(overlay.set_offset)
    settings.pause_requested.connect(controller.pause)
    settings.resume_requested.connect(controller.resume)
    settings.autoclick_toggle_requested.connect(autoclick.toggle)
    settings.autoclick_stop_on_level_up_changed.connect(autoclick.set_stop_on_level_up)
    autoclick.state_changed.connect(settings.set_autoclick_state)
    controller.snapshot_ready.connect(overlay.show_snapshot)
    controller.snapshot_ready.connect(autoclick.on_snapshot)
    controller.overlay_hidden.connect(overlay.hide_overlay)
    controller.overlay_hidden.connect(autoclick.panel_closed)
    controller.status_changed.connect(settings.set_status)

    def rebind_hotkey(key: str) -> None:
        rebind = getattr(hotkey, "rebind", None)
        available = bool(rebind(key)) if callable(rebind) else False
        settings.set_hotkey_available(available)
        logger.info("atalho do autoclique: %s (%s)", key, "ok" if available else "indisponível")

    settings.hotkey_changed.connect(rebind_hotkey)

    def set_autoclick_enabled(enabled: bool) -> None:
        if not enabled:
            autoclick.stop()
        set_enabled = getattr(hotkey, "set_enabled", None)
        available = bool(set_enabled(enabled)) if callable(set_enabled) else bool(hotkey.registered)
        settings.set_hotkey_available(available)
        logger.info("autoclique %s", "ativado" if enabled else "desativado")

    settings.autoclick_enabled_changed.connect(set_autoclick_enabled)

    # Save after the user stops typing/dragging instead of on every keystroke.
    save_timer = QTimer()
    save_timer.setSingleShot(True)
    save_timer.setInterval(SAVE_DEBOUNCE_MS)

    def persist() -> None:
        try:
            store.save(settings.current_config())
        except OSError:
            logger.exception("não foi possível salvar a configuração")

    save_timer.timeout.connect(persist)
    for signal in (
        settings.unit_price_changed,
        settings.opacity_changed,
        settings.window_selected,
        settings.target_level_changed,
        settings.city_changed,
        settings.auto_city_changed,
        settings.autoclick_enabled_changed,
        settings.overlay_offset_changed,
        settings.hotkey_changed,
        settings.autoclick_stop_on_level_up_changed,
        settings.auto_start_changed,
    ):
        signal.connect(save_timer.start)

    runtime = ApplicationRuntime(
        qt_app,
        controller,
        overlay,
        settings,
        autoclick,
        hotkey,
        tray,
        store,
        worker,
        frame_source,
        pipeline,
        save_timer,
    )
    tray.exit_requested.connect(qt_app.quit)
    qt_app.aboutToQuit.connect(runtime.shutdown)
    return runtime


_MUTEX_NAME = r"Local\ROXEnchantmentOverlay.SingleInstance"
_ERROR_ALREADY_EXISTS = 183


def acquire_single_instance(name: str = _MUTEX_NAME) -> int | None:
    """Return a mutex handle if this is the only instance, or None if one is running.

    A named mutex is released by Windows even if the process crashes, so a
    stale lock can never block the next start.
    """
    import ctypes

    kernel32 = ctypes.windll.kernel32
    kernel32.CreateMutexW.restype = ctypes.c_void_p
    handle = kernel32.CreateMutexW(None, False, name)
    if not handle:
        logger.warning("não foi possível criar o mutex de instância única; seguindo sem ele")
        return 0
    if kernel32.GetLastError() == _ERROR_ALREADY_EXISTS:
        kernel32.CloseHandle(ctypes.c_void_p(handle))
        return None
    return int(handle)


def main(argv: list[str] | None = None) -> int:
    arguments = sys.argv[1:] if argv is None else argv
    self_test = "--self-test" in arguments
    if self_test:
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
        runtime = build_application(start_worker=False)
        runtime.persist_on_shutdown = False  # a smoke test must never touch user settings
        runtime.shutdown()
        return 0

    log_path = configure_logging()
    logger.info("ROX Enchantment Overlay %s iniciando (log: %s)", __version__, log_path)
    qt_app = cast(QApplication, QApplication.instance() or QApplication(sys.argv))
    instance = acquire_single_instance()
    if instance is None:
        logger.warning("outra instância já está aberta; encerrando")
        QMessageBox.information(
            None,
            "ROX Enchantment Overlay",
            "O programa já está aberto. Procure o ícone perto do relógio do Windows.",
        )
        return 1
    try:
        runtime = build_application(app=qt_app)
    except Exception:
        logger.exception("falha ao iniciar")
        QMessageBox.critical(
            None,
            "ROX Enchantment Overlay",
            f"Não foi possível iniciar. Detalhes no log:\n{log_path}",
        )
        return 1
    runtime.settings.show()
    runtime.tray.show()
    if runtime.settings.current_config().auto_start:
        runtime.settings.try_auto_start()
    return runtime.app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
