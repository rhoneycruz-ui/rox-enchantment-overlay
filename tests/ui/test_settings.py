from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QCheckBox, QComboBox, QLabel, QPushButton, QSlider, QSpinBox

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
    window = SettingsWindow(FakeDiscovery(), AppConfig(autoclick_enabled=True))
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
    window = SettingsWindow(FakeDiscovery(), AppConfig(autoclick_enabled=True))
    license_label = window.findChild(QLabel, "licenseLabel")
    hotkey_label = window.findChild(QLabel, "hotkeyStatusLabel")

    assert license_label.text() == "Licenciado por Rhoney"
    assert hotkey_label.text() == "Atalho global: F1"

    window.set_hotkey_available(False)

    assert hotkey_label.text() == "F1 indisponível — use o botão"



def test_pause_button_follows_controller_status(app: QApplication) -> None:
    window = SettingsWindow(FakeDiscovery(), AppConfig())
    button = window.findChild(QPushButton, "pauseButton")
    assert not button.isEnabled()

    window.select_current_window()
    assert button.isEnabled()
    window.toggle_pause()
    assert button.text() == "Retomar"

    # Choosing "Monitorar" again resumes the controller: the button must follow.
    window.select_current_window()
    assert button.text() == "Pausar"
    window.set_status("pausado")
    assert button.text() == "Retomar"
    window.set_status("encanto_detectado")
    assert button.text() == "Pausar"


def test_auto_start_selects_remembered_window(app: QApplication) -> None:
    window = SettingsWindow(FakeDiscovery(), AppConfig(window_title_hint="ragnarok x"))
    selected: list[WindowInfo] = []
    window.window_selected.connect(selected.append)

    assert window.try_auto_start()
    assert selected and selected[0].title == "Ragnarok X"
    assert not window.try_auto_start()  # already monitoring


def test_auto_start_waits_for_missing_game(app: QApplication) -> None:
    window = SettingsWindow(FakeDiscovery(), AppConfig(window_title_hint="Outro jogo"))

    assert not window.try_auto_start()
    assert window.findChild(QLabel, "statusLabel").text() == "Aguardando o jogo abrir…"
    assert window._auto_start_timer.isActive()
    window._auto_start_timer.stop()


def test_current_config_includes_new_preferences(app: QApplication) -> None:
    config_in = AppConfig(hotkey="F6", target_level=12, offset_x=-4, autoclick_enabled=True)
    window = SettingsWindow(FakeDiscovery(), config_in)
    config = window.current_config()

    assert config.hotkey == "F6"
    assert config.target_level == 12
    assert config.offset_x == -4
    window.set_hotkey_available(True)
    assert window.findChild(QLabel, "hotkeyStatusLabel").text() == "Atalho global: F6"
    window.set_autoclick_state("stopped:level_up", 40)
    assert window.findChild(QLabel, "autoclickStatusLabel").text() == "Parado: nível alcançado"
    assert window.findChild(QPushButton, "autoclickButton").text() == "Iniciar autoclique"


def test_city_combo_disables_price_outside_prontera(app: QApplication) -> None:
    window = SettingsWindow(FakeDiscovery(), AppConfig(city="Prontera", auto_city=False))
    cities: list[str] = []
    window.city_changed.connect(cities.append)
    combo = window.findChild(QComboBox, "cityCombo")
    price = window.findChild(QSpinBox, "priceSpin")

    assert combo.count() == 8 and combo.currentText() == "Prontera"
    assert price.isEnabled()

    combo.setCurrentText("Morroc")

    assert cities == ["Morroc"]
    assert not price.isEnabled()
    assert "pedras" in window.findChild(QLabel, "priceNoteLabel").text()
    assert window.current_config().city == "Morroc"


def test_auto_city_keeps_price_enabled_and_emits(app: QApplication) -> None:
    window = SettingsWindow(FakeDiscovery(), AppConfig(city="Morroc", auto_city=True))
    toggles: list[bool] = []
    window.auto_city_changed.connect(toggles.append)
    price = window.findChild(QSpinBox, "priceSpin")
    check = window.findChild(QCheckBox, "autoCityCheck")

    assert check.isChecked() and price.isEnabled()
    assert "reconhecida" in window.findChild(QLabel, "priceNoteLabel").text()

    check.setChecked(False)

    assert toggles == [False]
    assert not price.isEnabled()
    assert window.current_config().auto_city is False


def test_autoclick_can_be_fully_disabled(app: QApplication) -> None:
    window = SettingsWindow(FakeDiscovery(), AppConfig())
    toggles: list[bool] = []
    window.autoclick_enabled_changed.connect(toggles.append)
    check = window.findChild(QCheckBox, "autoclickEnabledCheck")
    button = window.findChild(QPushButton, "autoclickButton")

    assert not check.isChecked()  # off by default
    assert not button.isEnabled()
    assert window.findChild(QLabel, "autoclickStatusLabel").text() == "Desativado"

    check.setChecked(True)

    assert toggles == [True]
    assert button.isEnabled()
    assert window.current_config().autoclick_enabled is True


def test_toggles_are_switches_that_flip_on_click(app: QApplication) -> None:
    from PySide6.QtCore import QPoint
    from PySide6.QtTest import QTest

    from rox_overlay.ui.switch import ToggleSwitch

    window = SettingsWindow(FakeDiscovery(), AppConfig(auto_start=False))
    switch = window.findChild(QCheckBox, "autoStartCheck")
    assert isinstance(switch, ToggleSwitch)
    switch.resize(switch.sizeHint())
    QTest.mouseClick(switch, Qt.MouseButton.LeftButton, pos=QPoint(5, switch.height() // 2))
    assert switch.isChecked()
    assert window.current_config().auto_start is True
