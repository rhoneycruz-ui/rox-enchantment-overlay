"""Timed recognition loop that emits stable, UI-ready cost snapshots."""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import QObject, QTimer, Signal, Slot

from rox_overlay.capture.base import FrameSource, WindowDiscovery, WindowInfo
from rox_overlay.domain import CostEstimate, estimate_cost
from rox_overlay.recognition.models import Rect
from rox_overlay.recognition.pipeline import RecognitionPipeline
from rox_overlay.recognition.stability import ReadingStabilizer


@dataclass(frozen=True)
class OverlaySnapshot:
    estimate: CostEstimate
    panel_rect: Rect
    confidence: float


class RecognitionController(QObject):
    snapshot_ready = Signal(object)
    overlay_hidden = Signal()
    status_changed = Signal(str)

    def __init__(
        self,
        capture: FrameSource,
        pipeline: RecognitionPipeline,
        *,
        unit_price: int = 0,
        fps: int = 5,
        discovery: WindowDiscovery | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._capture = capture
        self._pipeline = pipeline
        self._discovery = discovery
        self._stabilizer = ReadingStabilizer()
        self._unit_price = unit_price
        self._window: WindowInfo | None = None
        self._paused = False
        self._was_visible = False
        self._last_snapshot_key: tuple[CostEstimate, Rect] | None = None
        self.interval_ms = round(1000 / fps)
        self._timer = QTimer(self)
        self._timer.setInterval(self.interval_ms)
        self._timer.timeout.connect(self.tick_once)

    def set_window(self, window: WindowInfo | None) -> None:
        self._window = window
        self._stabilizer = ReadingStabilizer()
        self._last_snapshot_key = None

    @Slot(object)
    def start(self, window: WindowInfo) -> None:
        self.set_window(window)
        self._paused = False
        self._timer.start()
        self.status_changed.emit("executando")

    @Slot()
    def pause(self) -> None:
        self._paused = True
        self._stabilizer = ReadingStabilizer()
        self._publish_visibility(False)
        self.status_changed.emit("pausado")

    @Slot()
    def resume(self) -> None:
        self._paused = False
        self.status_changed.emit("executando")

    @Slot()
    def stop(self) -> None:
        self._timer.stop()
        self._publish_visibility(False)
        self.set_window(None)
        self.status_changed.emit("parado")

    @Slot(int)
    def set_unit_price(self, price: int) -> None:
        if isinstance(price, bool) or not isinstance(price, int) or price < 0:
            raise ValueError("unit price must be a non-negative integer")
        self._unit_price = price

    @Slot()
    def tick_once(self) -> None:
        if self._paused or self._window is None:
            return
        if self._discovery is not None:
            current = self._discovery.reacquire(self._window)
            if current is None:
                self.status_changed.emit("janela_indisponivel")
                self._handle_invalid()
                return
            self._window = current
        frame = self._capture.capture(self._window)
        if frame is None:
            self.status_changed.emit("janela_indisponivel")
            self._handle_invalid()
            return
        reading = self._pipeline.recognize(frame)
        if reading is None:
            self.status_changed.emit("procurando_painel")
            self._handle_invalid()
            return
        stable = self._stabilizer.push(reading)
        if stable.visible and stable.reading is not None:
            estimate = estimate_cost(
                stable.reading.item_type,
                stable.reading.level,
                stable.reading.progress,
                self._unit_price,
            )
            self._was_visible = True
            origin = self._window.client_rect
            panel = stable.reading.panel_rect
            scale = max(1.0, self._window.dpi_scale)
            physical_x = origin.x + panel.x
            physical_y = origin.y + panel.y
            screen_panel = Rect(
                self._window.monitor_x + round((physical_x - self._window.monitor_x) / scale),
                self._window.monitor_y + round((physical_y - self._window.monitor_y) / scale),
                round(panel.width / scale),
                round(panel.height / scale),
            )
            snapshot_key = (estimate, screen_panel)
            if snapshot_key != self._last_snapshot_key:
                self.snapshot_ready.emit(
                    OverlaySnapshot(estimate, screen_panel, stable.reading.confidence)
                )
                self._last_snapshot_key = snapshot_key
            self.status_changed.emit("encanto_detectado")

    def _handle_invalid(self) -> None:
        stable = self._stabilizer.mark_invalid()
        if not stable.visible:
            self._publish_visibility(False)

    def _publish_visibility(self, visible: bool) -> None:
        if self._was_visible and not visible:
            self.overlay_hidden.emit()
            self._last_snapshot_key = None
        self._was_visible = visible
