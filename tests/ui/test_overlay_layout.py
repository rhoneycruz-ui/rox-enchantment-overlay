from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import cv2
import pytest
from PySide6.QtCore import QPoint, QSize, Qt
from PySide6.QtWidgets import QApplication, QLabel

from rox_overlay.controller import OverlaySnapshot
from rox_overlay.domain import ItemType, estimate_cost
from rox_overlay.recognition.models import Rect
from rox_overlay.ui.overlay import OverlayWindow, choose_overlay_rect


@pytest.fixture(scope="module")
def app() -> QApplication:
    return QApplication.instance() or QApplication([])


def test_positions_twelve_pixels_left_of_panel() -> None:
    result = choose_overlay_rect(Rect(900, 40, 370, 650), QSize(300, 220), Rect(0, 0, 1920, 1080), QPoint())
    assert result == Rect(588, 40, 300, 220)


def test_uses_right_side_when_panel_is_at_left_edge() -> None:
    result = choose_overlay_rect(Rect(5, 40, 370, 650), QSize(300, 220), Rect(0, 0, 1920, 1080), QPoint())
    assert result == Rect(387, 40, 300, 220)


def test_clamps_inside_secondary_monitor_work_area_with_offset() -> None:
    result = choose_overlay_rect(
        Rect(3300, 900, 350, 300),
        QSize(300, 220),
        Rect(1920, 0, 1920, 1040),
        QPoint(20, 30),
    )
    assert result.x >= 1920
    assert result.y >= 0
    assert result.x + result.width <= 3840
    assert result.y + result.height <= 1040


def test_overlay_has_native_noninteractive_flags_and_updates_text(app: QApplication) -> None:
    overlay = OverlayWindow()
    flags = overlay.windowFlags()
    assert flags & Qt.WindowType.FramelessWindowHint
    assert flags & Qt.WindowType.WindowStaysOnTopHint
    assert flags & Qt.WindowType.WindowDoesNotAcceptFocus
    assert overlay.testAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

    estimate = estimate_cost(ItemType.ARMOR, 14, 0.5, 123)
    overlay.show_snapshot(OverlaySnapshot(estimate, Rect(900, 40, 370, 650), 0.9), Rect(0, 0, 1920, 1080))

    assert overlay.findChild(QLabel, "itemLabel").text() == "ARMADURA"
    assert "14 → 15" in overlay.findChild(QLabel, "levelLabel").text()
    assert overlay.findChild(QLabel, "zenyLabel").text() == "7.011.000"
    currency_icon = overlay.findChild(QLabel, "currencyIcon")
    assert currency_icon.pixmap() is not None
    assert not currency_icon.pixmap().isNull()


def test_currency_icon_has_real_transparency() -> None:
    path = Path(__file__).parents[2] / "src" / "rox_overlay" / "assets" / "crystal-currency.png"
    image = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)

    assert image is not None
    assert image.shape[2] == 4
    alpha = image[:, :, 3]
    assert alpha.max() == 255
    assert (alpha == 0).mean() > 0.5


def test_opacity_changes_background_only(app: QApplication) -> None:
    overlay = OverlayWindow()
    overlay.set_opacity(35)
    assert overlay.background_opacity == 35
    assert overlay.windowOpacity() == 1.0

    with pytest.raises(ValueError):
        overlay.set_opacity(24)
