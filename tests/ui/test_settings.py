from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QComboBox, QLabel, QSlider, QSpinBox

from rox_overlay.capture.base import WindowInfo
from rox_overlay.config import AppConfig
from rox_overlay.recognition.models import Rect
from rox_overlay.ui.settings import SettingsWindow


class FakeDiscovery:
    def list_windows(self) -> list[WindowInfo]:
        return [WindowInfo(7, "Ragnarok X", Rect(0, 0, 1280, 720))]

    def reacquire(self, previous: WindowInfo) -> WindowInfo | None:
        return previous


@pytest.fixture(scope="module")
def app() -> QApplication:
    return QApplication.instance() or QApplication([])


def test_settings_populates_windows_and_controls(app: QApplication) -> None:
    window = SettingsWindow(FakeDiscovery(), AppConfig(123, 82))
    combo = window.findChild(QComboBox, "windowCombo")
    opacity = window.findChild(QSlider, "opacitySlider")
    price = window.findChild(QSpinBox, "priceSpin")

    assert combo.count() == 1
    assert combo.currentText() == "Ragnarok X"
    assert opacity.minimum() == 25 and opacity.maximum() == 100 and opacity.value() == 82
    assert price.value() == 123


def test_settings_emits_validated_changes_and_status(app: QApplication) -> None:
    window = SettingsWindow(FakeDiscovery(), AppConfig())
    prices: list[int] = []
    opacities: list[int] = []
    window.unit_price_changed.connect(prices.append)
    window.opacity_changed.connect(opacities.append)

    window.findChild(QSpinBox, "priceSpin").setValue(999)
    window.findChild(QSlider, "opacitySlider").setValue(35)
    window.set_status("procurando_painel")

    assert prices[-1] == 999
    assert opacities[-1] == 35
    assert window.findChild(QLabel, "statusLabel").text() == "Aguardando painel"

