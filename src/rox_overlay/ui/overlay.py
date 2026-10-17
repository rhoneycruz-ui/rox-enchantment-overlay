"""Compact, click-through enchantment overlay."""

from __future__ import annotations

import ctypes
from pathlib import Path

from PySide6.QtCore import QPoint, QRect, QSize, Qt
from PySide6.QtGui import QColor, QFont, QFontDatabase, QGuiApplication, QPainter, QPaintEvent, QPen
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


_ITEM_NAMES = {
    ItemType.WEAPON: "ARMA",
    ItemType.ARMOR: "ARMADURA",
    ItemType.ACCESSORY: "ACESSÓRIO",
}


def _load_interface_font() -> str:
    font_path = Path(__file__).parents[1] / "assets" / "fonts" / "Inter.ttf"
    font_id = QFontDatabase.addApplicationFont(str(font_path))
    families = QFontDatabase.applicationFontFamilies(font_id) if font_id >= 0 else []
    return families[0] if families else "Arial"


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
    return next((candidate for candidate in candidates if _inside(candidate, work_area)), _clamp(candidates[0], work_area))


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
        self.setFixedSize(300, 226)
        self.background_opacity = 82
        self.setFont(QFont(_load_interface_font()))
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
            "QProgressBar { border: 1px solid rgba(125, 151, 212, 90); border-radius: 4px; background: rgba(4, 11, 30, 150); }"
            "QProgressBar::chunk { border-radius: 3px; background: #4DDBE8; }"
        )
        root.addWidget(progress)

        divider = QFrame()
        divider.setObjectName("divider")
        divider.setFrameShape(QFrame.Shape.HLine)
        root.addWidget(divider)

        root.addWidget(self._label("PONTOS RESTANTES", "pointsCaption", "font-size: 9px; color: #9BA8C8;"))
        root.addWidget(self._label("—", "pointsLabel", "font-size: 18px; font-weight: 700;"))

        metrics = QHBoxLayout()
        musp_box = QVBoxLayout()
        musp_box.addWidget(self._label("MUSPELLIUM", "muspCaption", "font-size: 9px; color: #9BA8C8;"))
        musp_box.addWidget(self._label("—", "muspelliumLabel", "font-size: 15px; font-weight: 650;"))
        zeny_box = QVBoxLayout()
        zeny_box.addWidget(self._label("CUSTO RESTANTE", "zenyCaption", "font-size: 9px; color: #9BA8C8;"))
        zeny_box.addWidget(self._label("—", "zenyLabel", "font-size: 15px; font-weight: 700; color: #F5C86A;"))
        metrics.addLayout(musp_box)
        metrics.addStretch()
        metrics.addLayout(zeny_box)
        root.addLayout(metrics)

    def set_opacity(self, percent: int) -> None:
        if isinstance(percent, bool) or not isinstance(percent, int) or not 25 <= percent <= 100:
            raise ValueError("opacity must be an integer between 25 and 100")
        self.background_opacity = percent
        self.update()

    def show_snapshot(self, snapshot: OverlaySnapshot, work_area: Rect | None = None) -> None:
        estimate = snapshot.estimate
        self.findChild(QLabel, "itemLabel").setText(_ITEM_NAMES[estimate.item_type])
        next_level = "MÁX" if estimate.next_level is None else str(estimate.next_level)
        self.findChild(QLabel, "levelLabel").setText(f"{estimate.current_level} → {next_level}")
        self.findChild(QProgressBar, "progressBar").setValue(round(estimate.progress * 1000))
        self.findChild(QLabel, "pointsLabel").setText(_format_integer(estimate.remaining_points))
        self.findChild(QLabel, "muspelliumLabel").setText(_format_integer(estimate.remaining_muspellium))
        self.findChild(QLabel, "zenyLabel").setText(f"{_format_integer(estimate.remaining_zeny)} Zeny")

        if work_area is None:
            center = QPoint(
                snapshot.panel_rect.x + snapshot.panel_rect.width // 2,
                snapshot.panel_rect.y + snapshot.panel_rect.height // 2,
            )
            screen = QGuiApplication.screenAt(center) or QGuiApplication.primaryScreen()
            available = screen.availableGeometry() if screen is not None else QRect(0, 0, 1920, 1080)
            work_area = Rect(available.x(), available.y(), available.width(), available.height())
        placement = choose_overlay_rect(snapshot.panel_rect, self.size(), work_area, QPoint())
        self.setGeometry(placement.x, placement.y, placement.width, placement.height)
        self.show()

    def hide_overlay(self) -> None:
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
