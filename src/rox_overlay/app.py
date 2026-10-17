"""Application composition and executable entry point."""

from __future__ import annotations

import sys
import os
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QMetaObject, QThread, Qt
from PySide6.QtWidgets import QApplication

from rox_overlay.autoclick import AutoClickController
from rox_overlay.capture.base import FrameSource, WindowDiscovery
from rox_overlay.capture.fallback import CascadingFrameSource, MssCaptureSource
from rox_overlay.capture.windows import Win32WindowDiscovery, WindowsCaptureSource
from rox_overlay.config import ConfigStore
from rox_overlay.controller import RecognitionController
from rox_overlay.hotkey import GlobalF1Hotkey
from rox_overlay.recognition.panel import PanelDetector
from rox_overlay.recognition.pipeline import RecognitionPipeline
from rox_overlay.recognition.tesseract import TesseractOcrEngine
from rox_overlay.ui.overlay import OverlayWindow
from rox_overlay.ui.settings import SettingsWindow
from rox_overlay.ui.tray import TrayController


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
    hotkey: GlobalF1Hotkey
    tray: TrayController
    config_store: ConfigStore
    worker: QThread | None = None
    capture: FrameSource | None = None
    is_shutdown: bool = False

    def shutdown(self) -> None:
        if self.is_shutdown:
            return
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
        close = getattr(self.capture, "close", None)
        if callable(close):
            close()
        self.overlay.hide()
        self.tray.hide()
        self.is_shutdown = True


def build_application(
    *,
    app: QApplication | None = None,
    discovery: WindowDiscovery | None = None,
    capture: FrameSource | None = None,
    pipeline: RecognitionPipeline | None = None,
    config_store: ConfigStore | None = None,
    hotkey_factory: Callable[[QApplication, Callable[[], None]], GlobalF1Hotkey] = GlobalF1Hotkey,
    start_worker: bool = True,
) -> ApplicationRuntime:
    qt_app = app or QApplication.instance() or QApplication(sys.argv)
    qt_app.setApplicationName("ROX Enchantment Overlay")
    qt_app.setQuitOnLastWindowClosed(False)
    store = config_store or ConfigStore()
    config = store.load()
    window_discovery = discovery or Win32WindowDiscovery()
    frame_source = capture or CascadingFrameSource(WindowsCaptureSource(), MssCaptureSource())

    if pipeline is None:
        root = _resource_root()
        ocr = TesseractOcrEngine(
            root / "vendor" / "tesseract" / "tesseract.exe",
            root / "vendor" / "tesseract" / "tessdata",
        )
        pipeline = RecognitionPipeline(PanelDetector(), ocr)

    controller = RecognitionController(
        frame_source,
        pipeline,
        unit_price=config.unit_price,
        discovery=window_discovery,
    )
    overlay = OverlayWindow()
    overlay.set_opacity(config.opacity_percent)
    settings = SettingsWindow(window_discovery, config)
    autoclick = AutoClickController()
    hotkey = hotkey_factory(qt_app, autoclick.toggle)
    settings.set_hotkey_available(hotkey.registered)
    tray = TrayController(settings)
    worker = QThread() if start_worker else None
    if worker is not None:
        controller.moveToThread(worker)
        worker.start()

    settings.window_selected.connect(controller.start)
    settings.unit_price_changed.connect(controller.set_unit_price)
    settings.opacity_changed.connect(overlay.set_opacity)
    settings.pause_requested.connect(controller.pause)
    settings.resume_requested.connect(controller.resume)
    settings.autoclick_toggle_requested.connect(autoclick.toggle)
    autoclick.state_changed.connect(settings.set_autoclick_state)
    controller.snapshot_ready.connect(overlay.show_snapshot)
    controller.overlay_hidden.connect(overlay.hide_overlay)
    controller.status_changed.connect(settings.set_status)

    def persist() -> None:
        store.save(settings.current_config())

    settings.unit_price_changed.connect(lambda _value: persist())
    settings.opacity_changed.connect(lambda _value: persist())
    settings.window_selected.connect(lambda _window: persist())

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
    )
    tray.exit_requested.connect(qt_app.quit)
    qt_app.aboutToQuit.connect(runtime.shutdown)
    return runtime


def main(argv: list[str] | None = None) -> int:
    arguments = sys.argv[1:] if argv is None else argv
    self_test = "--self-test" in arguments
    if self_test:
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
    runtime = build_application(start_worker=not self_test)
    if self_test:
        runtime.shutdown()
        return 0
    runtime.settings.show()
    runtime.tray.show()
    return runtime.app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
