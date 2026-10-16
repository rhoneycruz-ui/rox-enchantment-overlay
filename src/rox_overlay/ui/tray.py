"""System tray controls for the background application."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtGui import QAction, QColor, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import QMenu, QSystemTrayIcon, QWidget


def _tray_icon() -> QIcon:
    pixmap = QPixmap(64, 64)
    pixmap.fill(QColor(0, 0, 0, 0))
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setBrush(QColor("#4DDBE8"))
    painter.setPen(QColor("#0A1830"))
    painter.drawEllipse(5, 5, 54, 54)
    painter.setPen(QColor("#071121"))
    painter.drawText(pixmap.rect(), 0x84, "R")
    painter.end()
    return QIcon(pixmap)


class TrayController(QSystemTrayIcon):
    exit_requested = Signal()

    def __init__(self, settings: QWidget) -> None:
        super().__init__(_tray_icon(), settings)
        self.setToolTip("ROX Enchantment Overlay")
        menu = QMenu()
        show_action = QAction("Abrir configurações", menu)
        show_action.triggered.connect(settings.show)
        menu.addAction(show_action)
        menu.addSeparator()
        exit_action = QAction("Sair", menu)
        exit_action.triggered.connect(self.exit_requested)
        menu.addAction(exit_action)
        self.setContextMenu(menu)
        self.activated.connect(lambda reason: settings.show() if reason == self.ActivationReason.Trigger else None)

