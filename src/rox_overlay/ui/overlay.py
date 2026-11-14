"""Compact, click-through enchantment overlay."""

from __future__ import annotations

import ctypes
from pathlib import Path

from PySide6.QtCore import QPoint, QRect, QSize, Qt
from PySide6.QtGui import QColor, QFont, QFontDatabase, QGuiApplication, QPainter, QPaintEvent, QPen, QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QVBoxLayout,
    QWidget,
)

from rox_overlay.controller import OverlaySnapshot
from rox_overlay.domain import ItemType
from rox_overlay.recognition.models import Rect
from rox_overlay.ui.widgets import child

_ITEM_NAMES = {
    ItemType.WEAPON: "ARMA",
    ItemType.ARMOR: "ARMADURA",
    ItemType.ACCESSORY: "ACESSÓRIO",
}


_CAPTION_CSS = "font-size: 9px; color: #9BA8C8;"
LOW_CONFIDENCE = 0.6


_FONT_FAMILY: str | None = None


def load_interface_font() -> str:
    global _FONT_FAMILY
    if _FONT_FAMILY is not None:
        return _FONT_FAMILY
    font_path = Path(__file__).parents[1] / "assets" / "fonts" / "Inter.ttf"
    font_id = QFontDatabase.addApplicationFont(str(font_path))
    families = QFontDatabase.applicationFontFamilies(font_id) if font_id >= 0 else []
    _FONT_FAMILY = families[0] if families else "Arial"
    return _FONT_FAMILY


def _inside(candidate: Rect, work_area: Rect) -> bool:
    return (
        candidate.x >= work_area.x
        and candidate.y >= work_area.y
        and candidate.x + candidate.width <= work_area.x + work_area.width
        and candidate.y + candidate.height <= work_area.y + work_area.height
    )


def _clamp(candidate: Rect, work_area: Rect) -> Rect:
    x = min(max(candidate.x, work_area.x), work_area.x + work_area.width - candidate.width)
    y = min(max(candidate.y, work_area.y), work_area.y + work_area.height - candidate.height)
    return Rect(x, y, candidate.width, candidate.height)


def choose_overlay_rect(
    panel_rect: Rect,
    overlay_size: QSize,
    work_area: Rect,
    offset: QPoint,
) -> Rect:
    width, height, gap = overlay_size.width(), overlay_size.height(), 12
    candidates = [
        Rect(panel_rect.x - width - gap + offset.x(), panel_rect.y + offset.y(), width, height),
        Rect(panel_rect.x + panel_rect.width + gap + offset.x(), panel_rect.y + offset.y(), width, height),
        Rect(panel_rect.x + offset.x(), panel_rect.y - height - gap + offset.y(), width, height),
        Rect(panel_rect.x + offset.x(), panel_rect.y + panel_rect.height + gap + offset.y(), width, height),
    ]
    fallback = _clamp(candidates[0], work_area)
    return next((candidate for candidate in candidates if _inside(candidate, work_area)), fallback)


def _format_integer(value: int) -> str:
    return f"{value:,}".replace(",", ".")


class OverlayWindow(QWidget):
    def __init__(self) -> None:
        flags = (
            Qt.WindowType.Tool
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.WindowDoesNotAcceptFocus
            | Qt.WindowType.WindowTransparentForInput
        )
        super().__init__(None, flags)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setFixedSize(300, 244)
        self.background_opacity = 82
        self._offset = QPoint()
        self._last_snapshot: OverlaySnapshot | None = None
        self.setFont(QFont(load_interface_font()))
        self._build_layout()

    def _label(self, text: str, object_name: str, css: str = "") -> QLabel:
        label = QLabel(text)
        label.setObjectName(object_name)
        label.setStyleSheet(css)
        return label

    def _build_layout(self) -> None:
        self.setStyleSheet(
            "QLabel { color: #F4F7FF; }"
            "QFrame#divider { background: rgba(121, 139, 184, 80); max-height: 1px; }"
        )
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 14, 18, 14)
        root.setSpacing(7)

        header = QHBoxLayout()
        item = self._label("—", "itemLabel", "font-size: 11px; font-weight: 700; color: #77E7FF;")
        badge = self._label("● AO VIVO  ·  PRONTERA", "cityLabel", "font-size: 9px; color: #78DDEB;")
        header.addWidget(item)
        header.addStretch()
        header.addWidget(badge)
        root.addLayout(header)

        root.addWidget(self._label("—", "levelLabel", "font-size: 25px; font-weight: 750;"))
        progress = QProgressBar()
        progress.setObjectName("progressBar")
        progress.setRange(0, 1000)
        progress.setTextVisible(False)
        progress.setFixedHeight(8)
        progress.setStyleSheet(
            "QProgressBar { border: 1px solid rgba(125, 151, 212, 90); border-radius: 4px;"
            " background: rgba(4, 11, 30, 150); }"
            "QProgressBar::chunk { border-radius: 3px; background: #4DDBE8; }"
        )
        root.addWidget(progress)

        divider = QFrame()
        divider.setObjectName("divider")
        divider.setFrameShape(QFrame.Shape.HLine)
        root.addWidget(divider)

        counts = QHBoxLayout()
        points_box = QVBoxLayout()
        points_box.addWidget(self._label("PONTOS RESTANTES", "pointsCaption", _CAPTION_CSS))
        points_box.addWidget(self._label("—", "pointsLabel", "font-size: 18px; font-weight: 700;"))
        taps_box = QVBoxLayout()
        taps_box.addWidget(self._label("TOQUES", "tapsCaption", _CAPTION_CSS))
        taps_box.addWidget(self._label("—", "tapsLabel", "font-size: 18px; font-weight: 700; color: #77E7FF;"))
        counts.addLayout(points_box)
        counts.addStretch()
        counts.addLayout(taps_box)
        root.addLayout(counts)

        metrics = QHBoxLayout()
        musp_box = QVBoxLayout()
        musp_box.addWidget(self._label("MUSPELLIUM", "muspCaption", _CAPTION_CSS))
        musp_box.addWidget(self._label("—", "muspelliumLabel", "font-size: 15px; font-weight: 650;"))
        cost_box = QVBoxLayout()
        cost_box.addWidget(self._label("CUSTO RESTANTE", "costCaption", _CAPTION_CSS))
        currency_row = QHBoxLayout()
        currency_row.setSpacing(4)
        currency_row.addWidget(self._label("—", "costLabel", "font-size: 15px; font-weight: 700; color: #F5C86A;"))
        currency_icon = QLabel()
        currency_icon.setObjectName("currencyIcon")
        currency_icon.setFixedSize(20, 20)
        icon_path = Path(__file__).parents[1] / "assets" / "crystal-currency.png"
        currency_icon.setPixmap(
            QPixmap(str(icon_path)).scaled(
                18,
                18,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )
        currency_row.addWidget(currency_icon)
        cost_box.addLayout(currency_row)
        metrics.addLayout(musp_box)
        metrics.addStretch()
        metrics.addLayout(cost_box)
        root.addLayout(metrics)

    def set_offset(self, x: int, y: int) -> None:
        self._offset = QPoint(int(x), int(y))
        if self.isVisible() and self._last_snapshot is not None:
            self.show_snapshot(self._last_snapshot)

    def set_opacity(self, percent: int) -> None:
        if isinstance(percent, bool) or not isinstance(percent, int) or not 25 <= percent <= 100:
            raise ValueError("opacity must be an integer between 25 and 100")  # caller bug, not user input
        self.background_opacity = percent
        self.update()

    def show_snapshot(self, snapshot: OverlaySnapshot, work_area: Rect | None = None) -> None:
        self._last_snapshot = snapshot
        estimate = snapshot.estimate
        approx = "≈ " if estimate.is_approximate else ""
        child(self, QLabel, "itemLabel").setText(_ITEM_NAMES[estimate.item_type])
        if estimate.next_level is None:
            level_text = f"{estimate.current_level} → MÁX"
        elif estimate.target_level is not None:
            level_text = f"{estimate.current_level} → {estimate.next_level}  (meta)"
        else:
            level_text = f"{estimate.current_level} → {estimate.next_level}"
        child(self, QLabel, "levelLabel").setText(level_text)
        child(self, QProgressBar, "progressBar").setValue(round(estimate.progress * 1000))
        child(self, QLabel, "pointsLabel").setText(approx + _format_integer(estimate.remaining_points))
        child(self, QLabel, "tapsLabel").setText(approx + _format_integer(estimate.remaining_taps))
        child(self, QLabel, "muspelliumLabel").setText(approx + _format_integer(estimate.remaining_stones))
        child(self, QLabel, "muspCaption").setText("MUSPELLIUM" if estimate.priced_in_crystals else "PEDRAS")
        child(self, QLabel, "muspelliumLabel").setToolTip(estimate.stone_name)
        child(self, QLabel, "costLabel").setText(approx + _format_integer(estimate.remaining_crystals))
        for name in ("costCaption", "costLabel", "currencyIcon"):
            child(self, QLabel, name).setVisible(estimate.priced_in_crystals)
        badge = child(self, QLabel, "cityLabel")
        if snapshot.confidence < LOW_CONFIDENCE:
            badge.setText("● LEITURA INCERTA")
            badge.setStyleSheet("font-size: 9px; color: #E3A04A;")
        else:
            source = "" if snapshot.city_detected else "  (manual)"
            badge.setText(f"● AO VIVO  ·  {estimate.city.upper()}{source}")
            badge.setStyleSheet("font-size: 9px; color: #78DDEB;")

        if work_area is None:
            center = QPoint(
                snapshot.panel_rect.x + snapshot.panel_rect.width // 2,
                snapshot.panel_rect.y + snapshot.panel_rect.height // 2,
            )
            screen = QGuiApplication.screenAt(center) or QGuiApplication.primaryScreen()
            available = screen.availableGeometry() if screen is not None else QRect(0, 0, 1920, 1080)
            work_area = Rect(available.x(), available.y(), available.width(), available.height())
        placement = choose_overlay_rect(snapshot.panel_rect, self.size(), work_area, self._offset)
        self.setGeometry(placement.x, placement.y, placement.width, placement.height)
        self.show()

    def hide_overlay(self) -> None:
        self._last_snapshot = None
        self.hide()

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        alpha = round(255 * self.background_opacity / 100)
        painter.setBrush(QColor(8, 14, 31, alpha))
        painter.setPen(QPen(QColor(87, 173, 230, min(230, alpha + 30)), 1.2))
        painter.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), 14, 14)
        painter.end()
        super().paintEvent(event)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        try:
            ctypes.windll.user32.SetWindowDisplayAffinity(int(self.winId()), 0x11)
        except (AttributeError, OSError):
            pass
