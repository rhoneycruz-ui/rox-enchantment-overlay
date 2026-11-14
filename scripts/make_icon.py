"""Regenerate the application icon (PNG + ICO) from vector shapes.

Run: python scripts/make_icon.py
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QGuiApplication, QImage, QLinearGradient, QPainter, QPen, QPolygonF

ASSETS = Path(__file__).parents[1] / "src" / "rox_overlay" / "assets"
logger = logging.getLogger("make_icon")


def render(size: int = 256) -> QImage:
    image = QImage(size, size, QImage.Format.Format_ARGB32)
    image.fill(Qt.GlobalColor.transparent)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    unit = size / 256
    painter.setPen(QPen(QColor("#4DDBE8"), 6 * unit))
    painter.setBrush(QColor("#080E1F"))
    painter.drawRoundedRect(QRectF(10 * unit, 10 * unit, 236 * unit, 236 * unit), 52 * unit, 52 * unit)
    crystal = QPolygonF([
        QPointF(128 * unit, 40 * unit),
        QPointF(190 * unit, 112 * unit),
        QPointF(128 * unit, 216 * unit),
        QPointF(66 * unit, 112 * unit),
    ])
    gradient = QLinearGradient(QPointF(128 * unit, 40 * unit), QPointF(128 * unit, 216 * unit))
    gradient.setColorAt(0.0, QColor("#B9F6FF"))
    gradient.setColorAt(1.0, QColor("#2396B5"))
    painter.setPen(QPen(QColor("#F4F7FF"), 4 * unit))
    painter.setBrush(gradient)
    painter.drawPolygon(crystal)
    painter.setPen(QPen(QColor(244, 247, 255, 150), 3 * unit))
    painter.drawLine(QPointF(66 * unit, 112 * unit), QPointF(190 * unit, 112 * unit))
    painter.drawLine(QPointF(128 * unit, 40 * unit), QPointF(128 * unit, 216 * unit))
    painter.end()
    return image


def main() -> int:
    logging.basicConfig(level=logging.INFO)
    app = QGuiApplication.instance() or QGuiApplication(sys.argv)
    image = render()
    ok_png = image.save(str(ASSETS / "app-icon.png"), "PNG")
    ok_ico = image.save(str(ASSETS / "app-icon.ico"), "ICO")
    logger.info("png=%s ico=%s", ok_png, ok_ico)
    del app
    return 0 if ok_png and ok_ico else 1


if __name__ == "__main__":
    raise SystemExit(main())
