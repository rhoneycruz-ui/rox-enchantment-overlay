"""Separate settings window for the noninteractive overlay."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from rox_overlay.capture.base import WindowDiscovery, WindowInfo
from rox_overlay.config import AppConfig


_STATUS_TEXT = {
    "executando": "Monitorando",
    "encanto_detectado": "Encanto detectado",
    "procurando_painel": "Aguardando painel",
    "janela_indisponivel": "Janela indisponível",
    "pausado": "Pausado",
    "parado": "Parado",
}


class SettingsWindow(QWidget):
    window_selected = Signal(object)
    unit_price_changed = Signal(int)
    opacity_changed = Signal(int)
    pause_requested = Signal()
    resume_requested = Signal()
    autoclick_toggle_requested = Signal()

    def __init__(self, discovery: WindowDiscovery, config: AppConfig) -> None:
        super().__init__()
        self._discovery = discovery
        self._paused = False
        self.setWindowTitle("ROX Enchantment Overlay")
        self.setMinimumWidth(410)
        self._build(config)
        self.refresh_windows(config.window_title_hint)

    def _build(self, config: AppConfig) -> None:
        root = QVBoxLayout(self)
        title = QLabel("Encantamento de Prontera")
        title.setStyleSheet("font-size: 20px; font-weight: 700;")
        root.addWidget(title)
        license_label = QLabel("Licenciado por Rhoney")
        license_label.setObjectName("licenseLabel")
        license_label.setStyleSheet("font-size: 11px; color: #777;")
        root.addWidget(license_label)
        subtitle = QLabel("Selecione o jogo e informe o preço unitário do Muspellium.")
        subtitle.setWordWrap(True)
        root.addWidget(subtitle)

        form = QFormLayout()
        combo = QComboBox()
        combo.setObjectName("windowCombo")
        form.addRow("Janela do jogo", combo)
        price = QSpinBox()
        price.setObjectName("priceSpin")
        price.setRange(0, 2_000_000_000)
        price.setGroupSeparatorShown(True)
        price.setValue(config.unit_price)
        price.valueChanged.connect(self.unit_price_changed)
        form.addRow("Preço do Muspellium", price)
        opacity = QSlider(Qt.Orientation.Horizontal)
        opacity.setObjectName("opacitySlider")
        opacity.setRange(25, 100)
        opacity.setValue(config.opacity_percent)
        opacity.valueChanged.connect(self.opacity_changed)
        form.addRow("Opacidade do painel", opacity)
        root.addLayout(form)

        status_row = QHBoxLayout()
        status_row.addWidget(QLabel("Status:"))
        status = QLabel("Aguardando seleção")
        status.setObjectName("statusLabel")
        status.setStyleSheet("font-weight: 650; color: #2396B5;")
        status_row.addWidget(status)
        status_row.addStretch()
        root.addLayout(status_row)

        autoclick_row = QHBoxLayout()
        autoclick_row.addWidget(QLabel("Autoclique:"))
        autoclick_status = QLabel("Desligado")
        autoclick_status.setObjectName("autoclickStatusLabel")
        autoclick_status.setStyleSheet("font-weight: 650; color: #D98B32;")
        autoclick_row.addWidget(autoclick_status)
        autoclick_row.addStretch()
        autoclick = QPushButton("Iniciar autoclique")
        autoclick.setObjectName("autoclickButton")
        autoclick.clicked.connect(self.autoclick_toggle_requested)
        autoclick_row.addWidget(autoclick)
        root.addLayout(autoclick_row)

        hotkey_status = QLabel("Atalho global: F1")
        hotkey_status.setObjectName("hotkeyStatusLabel")
        hotkey_status.setStyleSheet("font-size: 11px; color: #2396B5;")
        root.addWidget(hotkey_status)

        warning = QLabel(
            "Pressione F1 e posicione o cursor sobre Refino durante a contagem. "
            "Confirme as regras do jogo antes de usar automação."
        )
        warning.setWordWrap(True)
        warning.setStyleSheet("font-size: 11px; color: #777;")
        root.addWidget(warning)

        buttons = QHBoxLayout()
        refresh = QPushButton("Redetectar")
        refresh.clicked.connect(self.refresh_windows)
        buttons.addWidget(refresh)
        select = QPushButton("Monitorar janela")
        select.setObjectName("monitorButton")
        select.clicked.connect(self.select_current_window)
        buttons.addWidget(select)
        pause = QPushButton("Pausar")
        pause.setObjectName("pauseButton")
        pause.clicked.connect(self.toggle_pause)
        buttons.addWidget(pause)
        root.addLayout(buttons)

    def refresh_windows(self, title_hint: str = "") -> None:
        combo = self.findChild(QComboBox, "windowCombo")
        combo.clear()
        chosen = 0
        for index, window in enumerate(self._discovery.list_windows()):
            combo.addItem(window.title, window)
            if title_hint and window.title.casefold() == title_hint.casefold():
                chosen = index
        if combo.count():
            combo.setCurrentIndex(chosen)

    def select_current_window(self) -> None:
        combo = self.findChild(QComboBox, "windowCombo")
        window = combo.currentData()
        if isinstance(window, WindowInfo):
            self.window_selected.emit(window)

    def toggle_pause(self) -> None:
        self._paused = not self._paused
        button = self.findChild(QPushButton, "pauseButton")
        button.setText("Retomar" if self._paused else "Pausar")
        (self.pause_requested if self._paused else self.resume_requested).emit()

    def set_status(self, status: str) -> None:
        self.findChild(QLabel, "statusLabel").setText(_STATUS_TEXT.get(status, status))

    def set_autoclick_state(self, state: str, remaining: int) -> None:
        button = self.findChild(QPushButton, "autoclickButton")
        status = self.findChild(QLabel, "autoclickStatusLabel")
        active = state != "idle"
        button.setText("Parar autoclique" if active else "Iniciar autoclique")
        if state == "countdown":
            status.setText(f"Começa em {remaining}s")
        elif state == "running":
            status.setText("Clicando (4/s)")
        else:
            status.setText("Desligado")

    def set_hotkey_available(self, available: bool) -> None:
        status = self.findChild(QLabel, "hotkeyStatusLabel")
        status.setText("Atalho global: F1" if available else "F1 indisponível — use o botão")

    def current_config(self) -> AppConfig:
        combo = self.findChild(QComboBox, "windowCombo")
        return AppConfig(
            unit_price=self.findChild(QSpinBox, "priceSpin").value(),
            opacity_percent=self.findChild(QSlider, "opacitySlider").value(),
            window_title_hint=combo.currentText(),
        )

