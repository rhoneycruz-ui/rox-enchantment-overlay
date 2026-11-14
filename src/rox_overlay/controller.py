"""Timed recognition loop that emits stable, UI-ready cost snapshots."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from PySide6.QtCore import QObject, QTimer, Signal, Slot

from rox_overlay.capture.base import FrameSource, WindowDiscovery, WindowInfo
from rox_overlay.domain import CITIES, DEFAULT_CITY, CostEstimate, estimate_cost
from rox_overlay.recognition.models import Rect
from rox_overlay.recognition.pipeline import RecognitionPipeline
from rox_overlay.recognition.stability import ReadingStabilizer

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class OverlaySnapshot:
    estimate: CostEstimate
    panel_rect: Rect
    confidence: float
    city_detected: bool = False


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
        self._target_level: int | None = None
        self._city = DEFAULT_CITY
        self._auto_city = True
        self._last_status: str | None = None
        self._consecutive_errors = 0
        self._window: WindowInfo | None = None
        self._paused = False
        self._was_visible = False
        self._last_snapshot_key: tuple[CostEstimate, Rect, bool] | None = None
        self.interval_ms = round(1000 / fps)
        self._timer = QTimer(self)
        self._timer.setInterval(self.interval_ms)
        self._timer.timeout.connect(self.tick_once)

    @property
    def current_window(self) -> WindowInfo | None:
        return self._window

    def _emit_status(self, status: str) -> None:
        if status != self._last_status:
            self._last_status = status
            self.status_changed.emit(status)

    def set_window(self, window: WindowInfo | None) -> None:
        self._window = window
        self._stabilizer = ReadingStabilizer()
        self._last_snapshot_key = None

    @Slot(object)
    def start(self, window: WindowInfo) -> None:
        self.set_window(window)
        self._paused = False
        self._timer.start()
        self._emit_status("executando")

    @Slot()
    def pause(self) -> None:
        self._paused = True
        self._stabilizer = ReadingStabilizer()
        self._publish_visibility(False)
        self._emit_status("pausado")

    @Slot()
    def resume(self) -> None:
        self._paused = False
        self._emit_status("executando")

    @Slot()
    def stop(self) -> None:
        self._timer.stop()
        self._publish_visibility(False)
        self.set_window(None)
        self._emit_status("parado")

    @Slot(int)
    def set_unit_price(self, price: int) -> None:
        if isinstance(price, bool) or not isinstance(price, int) or price < 0:
            logger.warning("preço unitário inválido ignorado: %r", price)
            return
        self._unit_price = price

    @Slot(int)
    def set_target_level(self, level: int) -> None:
        """0 means "next level"; 2..20 accumulates the cost up to that level."""
        if isinstance(level, bool) or not isinstance(level, int) or (level != 0 and not 2 <= level <= 20):
            logger.warning("nível-meta inválido ignorado: %r", level)
            return
        self._target_level = level or None
        self._last_snapshot_key = None

    @Slot(str)
    def set_city(self, city: str) -> None:
        if city not in CITIES:
            logger.warning("cidade desconhecida ignorada: %r", city)
            return
        self._city = city
        self._last_snapshot_key = None

    @Slot(bool)
    def set_auto_city(self, enabled: bool) -> None:
        self._auto_city = bool(enabled)
        self._last_snapshot_key = None

    @Slot()
    def tick_once(self) -> None:
        if self._paused or self._window is None:
            return
        try:
            self._tick()
        except Exception:
            # One bad frame (OCR timeout, capture hiccup...) must not leave a
            # stale overlay on screen or silently kill the loop.
            self._consecutive_errors += 1
            if self._consecutive_errors == 1 or self._consecutive_errors % 50 == 0:
                logger.exception("falha ao analisar o quadro (%d seguidas)", self._consecutive_errors)
            self._emit_status("erro_leitura")
            self._handle_invalid()
        else:
            self._consecutive_errors = 0

    def _tick(self) -> None:
        assert self._window is not None
        if self._discovery is not None:
            current = self._discovery.reacquire(self._window)
            if current is None:
                self._emit_status("janela_indisponivel")
                self._handle_invalid()
                return
            self._window = current
            is_foreground = getattr(self._discovery, "is_foreground", None)
            if callable(is_foreground) and not is_foreground(current):
                # The capture still sees a covered game, so without this the
                # overlay would float over whatever window the user switched to.
                self._emit_status("jogo_em_segundo_plano")
                self._publish_visibility(False)
                return
        frame = self._capture.capture(self._window)
        if frame is None:
            self._emit_status("janela_indisponivel")
            self._handle_invalid()
            return
        reading = self._pipeline.recognize(frame)
        if reading is None:
            self._emit_status("procurando_painel")
            self._handle_invalid(panel_absent=bool(getattr(self._pipeline, "panel_absent", False)))
            return
        stable = self._stabilizer.push(reading)
        if stable.visible and stable.reading is not None:
            detected = stable.reading.city if self._auto_city else None
            city = detected or self._city
            estimate = estimate_cost(
                stable.reading.item_type,
                stable.reading.level,
                stable.reading.progress,
                self._unit_price,
                self._target_level,
                city,
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
            snapshot_key = (estimate, screen_panel, detected is not None)
            if snapshot_key != self._last_snapshot_key:
                self.snapshot_ready.emit(
                    OverlaySnapshot(estimate, screen_panel, stable.reading.confidence, detected is not None)
                )
                self._last_snapshot_key = snapshot_key
            self._emit_status("encanto_detectado")

    def _handle_invalid(self, *, panel_absent: bool = False) -> None:
        stable = self._stabilizer.mark_invalid(panel_absent=panel_absent)
        if not stable.visible:
            self._publish_visibility(False)

    def _publish_visibility(self, visible: bool) -> None:
        if self._was_visible and not visible:
            self.overlay_hidden.emit()
            self._last_snapshot_key = None
        self._was_visible = visible
