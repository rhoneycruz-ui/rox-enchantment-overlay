from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QComboBox, QLabel, QPushButton, QSlider, QSpinBox

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


def test_settings_autoclick_button_emits_toggle_and_renders_state(app: QApplication) -> None:
    window = SettingsWindow(FakeDiscovery(), AppConfig())
    toggles: list[bool] = []
    window.autoclick_toggle_requested.connect(lambda: toggles.append(True))
    button = window.findChild(QPushButton, "autoclickButton")
    status = window.findChild(QLabel, "autoclickStatusLabel")

    button.click()
    window.set_autoclick_state("countdown", 3)
    assert toggles == [True]
    assert button.text() == "Parar autoclique"
    assert status.text() == "Começa em 3s"

    window.set_autoclick_state("running", 0)
    assert status.text() == "Clicando (4/s)"

    window.set_autoclick_state("idle", 0)
    assert button.text() == "Iniciar autoclique"
    assert status.text() == "Desligado"


def test_settings_shows_license_and_global_hotkey_state(app: QApplication) -> None:
    window = SettingsWindow(FakeDiscovery(), AppConfig())
    license_label = window.findChild(QLabel, "licenseLabel")
    hotkey_label = window.findChild(QLabel, "hotkeyStatusLabel")

    assert license_label.text() == "Licenciado por Rhoney"
    assert hotkey_label.text() == "Atalho global: F1"

    window.set_hotkey_available(False)

    assert hotkey_label.text() == "F1 indisponível — use o botão"

