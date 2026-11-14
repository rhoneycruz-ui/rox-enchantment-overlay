"""Separate settings window for the noninteractive overlay."""

from __future__ import annotations

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QSpinBox,
    QStyle,
    QVBoxLayout,
    QWidget,
)

from rox_overlay import __version__
from rox_overlay.capture.base import WindowDiscovery, WindowInfo
from rox_overlay.config import HOTKEY_CHOICES, MAX_OVERLAY_OFFSET, AppConfig
from rox_overlay.domain import CITIES, DEFAULT_CITY
from rox_overlay.ui.overlay import load_interface_font
from rox_overlay.ui.switch import ToggleSwitch
from rox_overlay.ui.theme import SETTINGS_STYLESHEET
from rox_overlay.ui.widgets import child

_STATUS_TEXT = {
    "executando": "Monitorando",
    "encanto_detectado": "Encanto detectado",
    "procurando_painel": "Aguardando painel",
    "janela_indisponivel": "Janela indisponível",
    "jogo_em_segundo_plano": "Jogo em segundo plano",
    "erro_leitura": "Erro na leitura (veja o log)",
    "pausado": "Pausado",
    "parado": "Parado",
}

_AUTOCLICK_STOP_TEXT = {
    "level_up": "Parado: nível alcançado",
    "panel_closed": "Parado: menu fechado",
    "game_unfocused": "Parado: jogo perdeu o foco",
}

AUTO_START_RETRY_MS = 5000


class SettingsWindow(QWidget):
    window_selected = Signal(object)
    unit_price_changed = Signal(int)
    opacity_changed = Signal(int)
    pause_requested = Signal()
    resume_requested = Signal()
    autoclick_toggle_requested = Signal()
    target_level_changed = Signal(int)
    overlay_offset_changed = Signal(int, int)
    hotkey_changed = Signal(str)
    autoclick_stop_on_level_up_changed = Signal(bool)
    auto_start_changed = Signal(bool)
    city_changed = Signal(str)
    auto_city_changed = Signal(bool)
    autoclick_enabled_changed = Signal(bool)

    def __init__(self, discovery: WindowDiscovery, config: AppConfig) -> None:
        super().__init__()
        self._discovery = discovery
        self._paused = False
        self._monitoring = False
        self._title_hint = config.window_title_hint
        self.setWindowTitle(f"ROX Enchantment Overlay {__version__}")
        self.setMinimumSize(980, 470)
        self.setFont(QFont(load_interface_font()))
        self.setStyleSheet(SETTINGS_STYLESHEET)
        self._build(config)
        self.refresh_windows(config.window_title_hint)
        self._auto_start_timer = QTimer(self)
        self._auto_start_timer.setInterval(AUTO_START_RETRY_MS)
        self._auto_start_timer.timeout.connect(self._retry_auto_start)

    # ------------------------------------------------------------------ layout
    def _card(self, title: str, accent: str) -> tuple[QFrame, QVBoxLayout]:
        card = QFrame()
        card.setObjectName("card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 16, 18, 18)
        layout.setSpacing(10)
        heading = QLabel(f"<span style='color:{accent}'>●</span>&nbsp;&nbsp;{title}")
        heading.setObjectName("cardTitle")
        layout.addWidget(heading)
        return card, layout

    @staticmethod
    def _field(layout: QVBoxLayout, caption: str, widget: QWidget | QHBoxLayout) -> None:
        label = QLabel(caption)
        label.setObjectName("fieldCaption")
        layout.addWidget(label)
        if isinstance(widget, QHBoxLayout):
            layout.addLayout(widget)
        else:
            layout.addWidget(widget)

    @staticmethod
    def _divider(layout: QVBoxLayout) -> None:
        line = QFrame()
        line.setObjectName("cardDivider")
        line.setFixedHeight(1)
        layout.addWidget(line)

    def _build(self, config: AppConfig) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(22, 18, 22, 20)
        root.setSpacing(16)

        # --- Header: title on the left, live status on the right
        header = QHBoxLayout()
        heading = QVBoxLayout()
        heading.setSpacing(2)
        title = QLabel("Custo de Encantamento")
        title.setObjectName("titleLabel")
        heading.addWidget(title)
        subtitle = QLabel("Selecione o jogo e a cidade. Em Prontera, informe o preço do Muspellium em cristais.")
        subtitle.setObjectName("subtitleLabel")
        heading.addWidget(subtitle)
        header.addLayout(heading)
        header.addStretch()
        side = QVBoxLayout()
        side.setSpacing(4)
        status_pill = QFrame()
        status_pill.setObjectName("statusPill")
        pill = QHBoxLayout(status_pill)
        pill.setContentsMargins(14, 6, 16, 6)
        pill.setSpacing(8)
        dot = QLabel("●")
        dot.setObjectName("statusDot")
        pill.addWidget(dot)
        status = QLabel("Aguardando seleção")
        status.setObjectName("statusLabel")
        pill.addWidget(status)
        side.addWidget(status_pill, 0, Qt.AlignmentFlag.AlignRight)
        meta = QHBoxLayout()
        meta.addStretch()
        license_label = QLabel("Licenciado por Rhoney")
        license_label.setObjectName("licenseLabel")
        meta.addWidget(license_label)
        version = QLabel(f"v{__version__}")
        version.setObjectName("versionLabel")
        meta.addWidget(version)
        side.addLayout(meta)
        header.addLayout(side)
        root.addLayout(header)

        cards = QHBoxLayout()
        cards.setSpacing(14)
        # Attach first: cards get reparented to the window as they are added, so the
        # behaviour helpers called during the build can find their widgets.
        root.addLayout(cards, 1)

        # --- Card 1: game window + overlay appearance
        game, game_layout = self._card("JOGO", "#4DDBE8")
        window_row = QHBoxLayout()
        window_row.setSpacing(8)
        combo = QComboBox()
        combo.setObjectName("windowCombo")
        window_row.addWidget(combo, 1)
        refresh = QPushButton()
        refresh.setObjectName("refreshButton")
        refresh.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_BrowserReload))
        refresh.setToolTip("Redetectar janelas do jogo")
        refresh.setFixedWidth(40)
        refresh.clicked.connect(lambda: self.refresh_windows(self._current_title()))
        window_row.addWidget(refresh)
        self._field(game_layout, "Janela do jogo", window_row)
        buttons = QHBoxLayout()
        buttons.setSpacing(8)
        select = QPushButton("Monitorar")
        select.setObjectName("monitorButton")
        select.clicked.connect(self.select_current_window)
        buttons.addWidget(select, 2)
        pause = QPushButton("Pausar")
        pause.setObjectName("pauseButton")
        pause.setEnabled(False)
        pause.clicked.connect(self.toggle_pause)
        buttons.addWidget(pause, 1)
        game_layout.addLayout(buttons)
        auto_start = ToggleSwitch("Monitorar ao abrir o programa")
        auto_start.setObjectName("autoStartCheck")
        auto_start.setChecked(config.auto_start)
        auto_start.toggled.connect(self.auto_start_changed)
        game_layout.addWidget(auto_start)
        self._divider(game_layout)
        opacity_row = QHBoxLayout()
        opacity = QSlider(Qt.Orientation.Horizontal)
        opacity.setObjectName("opacitySlider")
        opacity.setRange(25, 100)
        opacity.setValue(config.opacity_percent)
        opacity_value = QLabel(f"{config.opacity_percent}%")
        opacity_value.setObjectName("opacityValueLabel")
        opacity_value.setFixedWidth(40)
        opacity.valueChanged.connect(lambda value: opacity_value.setText(f"{value}%"))
        opacity.valueChanged.connect(self.opacity_changed)
        opacity_row.addWidget(opacity, 1)
        opacity_row.addWidget(opacity_value)
        self._field(game_layout, "Opacidade do painel", opacity_row)
        offsets = QHBoxLayout()
        offsets.setSpacing(8)
        for name, value in (("offsetXSpin", config.offset_x), ("offsetYSpin", config.offset_y)):
            spin = QSpinBox()
            spin.setObjectName(name)
            spin.setRange(-MAX_OVERLAY_OFFSET, MAX_OVERLAY_OFFSET)
            spin.setPrefix("X  " if name == "offsetXSpin" else "Y  ")
            spin.setSuffix(" px")
            spin.setValue(value)
            spin.valueChanged.connect(self._emit_offset)
            offsets.addWidget(spin, 1)
        self._field(game_layout, "Deslocamento do painel", offsets)
        game_layout.addStretch()
        cards.addWidget(game, 1)

        # --- Card 2: cost
        cost, cost_layout = self._card("CÁLCULO", "#F5C86A")
        city = QComboBox()
        city.setObjectName("cityCombo")
        city.addItems(list(CITIES))
        city.setCurrentText(config.city)
        city.setToolTip("Mestre de encantamento usado: muda a pedra e os pontos por toque.")
        city.currentTextChanged.connect(self._on_city_changed)
        self._field(cost_layout, "Cidade", city)
        auto_city = ToggleSwitch("Detectar a cidade pela pedra")
        auto_city.setObjectName("autoCityCheck")
        auto_city.setToolTip("Reconhece a pedra no quadro Custo. Se não reconhecer, usa a cidade escolhida acima.")
        auto_city.setChecked(config.auto_city)
        auto_city.toggled.connect(self._on_auto_city_changed)
        cost_layout.addWidget(auto_city)
        self._divider(cost_layout)
        price = QSpinBox()
        price.setObjectName("priceSpin")
        price.setRange(0, 2_000_000_000)
        price.setGroupSeparatorShown(True)
        price.setSuffix(" cristais")
        price.setValue(config.unit_price)
        price.valueChanged.connect(self.unit_price_changed)
        self._field(cost_layout, "Preço do Muspellium", price)
        price_note = QLabel("")
        price_note.setObjectName("priceNoteLabel")
        price_note.setWordWrap(True)
        cost_layout.addWidget(price_note)
        target = QComboBox()
        target.setObjectName("targetCombo")
        target.addItem("Próximo nível", 0)
        for level in range(2, 21):
            target.addItem(f"Até o nível {level}", level)
        target.setCurrentIndex(max(0, target.findData(config.target_level)))
        target.currentIndexChanged.connect(lambda _index: self.target_level_changed.emit(int(target.currentData())))
        self._field(cost_layout, "Calcular custo", target)
        cost_layout.addStretch()
        cards.addWidget(cost, 1)
        self._apply_city_state(config.city)

        # --- Card 3: autoclick
        auto, auto_layout = self._card("AUTOCLIQUE", "#8C7CFF")
        enabled = ToggleSwitch("Ativar autoclique")
        enabled.setObjectName("autoclickEnabledCheck")
        enabled.setToolTip("Desligado, o botão e o atalho não fazem nada e a tecla fica livre para outros programas.")
        enabled.setChecked(config.autoclick_enabled)
        enabled.toggled.connect(self._on_autoclick_enabled)
        auto_layout.addWidget(enabled)
        self._divider(auto_layout)
        autoclick_status = QLabel("Desligado")
        autoclick_status.setObjectName("autoclickStatusLabel")
        auto_layout.addWidget(autoclick_status)
        autoclick = QPushButton("Iniciar autoclique")
        autoclick.setObjectName("autoclickButton")
        autoclick.clicked.connect(self.autoclick_toggle_requested)
        auto_layout.addWidget(autoclick)
        hotkey_row = QHBoxLayout()
        hotkey_combo = QComboBox()
        hotkey_combo.setObjectName("hotkeyCombo")
        hotkey_combo.addItems(list(HOTKEY_CHOICES))
        hotkey_combo.setCurrentText(config.hotkey)
        hotkey_combo.currentTextChanged.connect(self.hotkey_changed)
        hotkey_combo.setFixedWidth(80)
        hotkey_row.addWidget(hotkey_combo)
        hotkey_status = QLabel(f"Atalho global: {config.hotkey}")
        hotkey_status.setObjectName("hotkeyStatusLabel")
        hotkey_row.addWidget(hotkey_status, 1)
        self._field(auto_layout, "Tecla de atalho", hotkey_row)
        stop_on_level = ToggleSwitch("Parar quando o nível subir")
        stop_on_level.setObjectName("stopOnLevelCheck")
        stop_on_level.setChecked(config.autoclick_stop_on_level_up)
        stop_on_level.toggled.connect(self.autoclick_stop_on_level_up_changed)
        auto_layout.addWidget(stop_on_level)
        warning = QLabel(
            "Aperte o atalho e, durante a contagem, ponha o cursor no botão de encantar. "
            "Só clica com o jogo em foco; para se o menu fechar ou você trocar de janela. "
            "Automação pode violar as regras do jogo: use por sua conta e risco."
        )
        warning.setObjectName("hintLabel")
        warning.setWordWrap(True)
        auto_layout.addWidget(warning)
        auto_layout.addStretch()
        cards.addWidget(auto, 1)
        self._apply_autoclick_enabled(config.autoclick_enabled)

    # ------------------------------------------------------------- behaviour
    def _apply_autoclick_enabled(self, enabled: bool) -> None:
        for kind, name in (
            (QPushButton, "autoclickButton"),
            (QComboBox, "hotkeyCombo"),
            (QCheckBox, "stopOnLevelCheck"),
            (QLabel, "hotkeyStatusLabel"),
            (QLabel, "autoclickStatusLabel"),
            (QLabel, "hintLabel"),
        ):
            child(self, kind, name).setEnabled(enabled)
        child(self, QLabel, "autoclickStatusLabel").setText("Desligado" if enabled else "Desativado")

    def _on_autoclick_enabled(self, enabled: bool) -> None:
        self._apply_autoclick_enabled(enabled)
        self.autoclick_enabled_changed.emit(enabled)

    def _apply_city_state(self, city: str) -> None:
        auto = child(self, QCheckBox, "autoCityCheck").isChecked()
        priced = auto or city == DEFAULT_CITY
        child(self, QSpinBox, "priceSpin").setEnabled(priced)
        if auto:
            note = f"Se a pedra não for reconhecida, usa {city}. O preço só vale em Prontera."
        elif priced:
            note = ""
        else:
            note = f"Em {city} o custo é em pedras de encantamento; o overlay mostra quantas faltam."
        label = child(self, QLabel, "priceNoteLabel")
        label.setText(note)
        label.setVisible(bool(note))

    def _on_city_changed(self, city: str) -> None:
        self._apply_city_state(city)
        self.city_changed.emit(city)

    def _on_auto_city_changed(self, enabled: bool) -> None:
        self._apply_city_state(child(self, QComboBox, "cityCombo").currentText())
        self.auto_city_changed.emit(enabled)

    def _current_title(self) -> str:
        return child(self, QComboBox, "windowCombo").currentText()

    def _emit_offset(self, _value: int = 0) -> None:
        self.overlay_offset_changed.emit(*self.overlay_offset())

    def overlay_offset(self) -> tuple[int, int]:
        return (
            child(self, QSpinBox, "offsetXSpin").value(),
            child(self, QSpinBox, "offsetYSpin").value(),
        )

    def refresh_windows(self, title_hint: str = "") -> bool:
        """Repopulate the window list; returns True when ``title_hint`` was found."""
        combo = child(self, QComboBox, "windowCombo")
        combo.clear()
        chosen = 0
        found = False
        for index, window in enumerate(self._discovery.list_windows()):
            combo.addItem(window.title, window)
            if title_hint and not found and window.title.casefold() == title_hint.casefold():
                chosen = index
                found = True
        if combo.count():
            combo.setCurrentIndex(chosen)
        return found

    def try_auto_start(self) -> bool:
        """Start monitoring the remembered game window, retrying until it appears."""
        if self._monitoring or not self._title_hint:
            return False
        if self.refresh_windows(self._title_hint):
            self._auto_start_timer.stop()
            self.select_current_window()
            return True
        self._auto_start_timer.start()
        self.set_status_text("Aguardando o jogo abrir…")
        return False

    def _retry_auto_start(self) -> None:
        if self._monitoring:
            self._auto_start_timer.stop()
            return
        wanted = self._title_hint.casefold()
        # Peek without touching the combo so a user mid-selection is not disturbed.
        if any(window.title.casefold() == wanted for window in self._discovery.list_windows()):
            self.try_auto_start()

    def select_current_window(self) -> None:
        combo = child(self, QComboBox, "windowCombo")
        window = combo.currentData()
        if isinstance(window, WindowInfo):
            self._auto_start_timer.stop()
            self._monitoring = True
            self._title_hint = window.title
            self._set_paused(False)
            child(self, QPushButton, "pauseButton").setEnabled(True)
            self.window_selected.emit(window)

    def _set_paused(self, paused: bool) -> None:
        self._paused = paused
        child(self, QPushButton, "pauseButton").setText("Retomar" if paused else "Pausar")

    def toggle_pause(self) -> None:
        self._set_paused(not self._paused)
        (self.pause_requested if self._paused else self.resume_requested).emit()

    def set_status(self, status: str) -> None:
        # Keep the pause button in sync with what the controller actually does.
        if status == "pausado":
            self._set_paused(True)
        elif status != "parado":
            self._set_paused(False)
        self.set_status_text(_STATUS_TEXT.get(status, status))

    def set_status_text(self, text: str) -> None:
        child(self, QLabel, "statusLabel").setText(text)

    def set_autoclick_state(self, state: str, remaining: int) -> None:
        button = child(self, QPushButton, "autoclickButton")
        status = child(self, QLabel, "autoclickStatusLabel")
        active = state not in ("idle",) and not state.startswith("stopped:")
        button.setText("Parar autoclique" if active else "Iniciar autoclique")
        if state == "countdown":
            status.setText(f"Começa em {remaining}s")
        elif state == "running":
            status.setText(f"Clicando (4/s) · {remaining} cliques" if remaining else "Clicando (4/s)")
        elif state == "waiting":
            status.setText("Em espera: foco/cursor fora do jogo")
        elif state.startswith("stopped:"):
            status.setText(_AUTOCLICK_STOP_TEXT.get(state.removeprefix("stopped:"), "Desligado"))
        else:
            enabled = child(self, QCheckBox, "autoclickEnabledCheck").isChecked()
            status.setText("Desligado" if enabled else "Desativado")

    def set_hotkey_available(self, available: bool) -> None:
        key = child(self, QComboBox, "hotkeyCombo").currentText()
        status = child(self, QLabel, "hotkeyStatusLabel")
        if not child(self, QCheckBox, "autoclickEnabledCheck").isChecked():
            status.setText(f"Atalho {key} livre (autoclique desativado)")
            return
        status.setText(f"Atalho global: {key}" if available else f"{key} indisponível — use o botão")

    def current_config(self) -> AppConfig:
        offset_x, offset_y = self.overlay_offset()
        return AppConfig(
            unit_price=child(self, QSpinBox, "priceSpin").value(),
            opacity_percent=child(self, QSlider, "opacitySlider").value(),
            window_title_hint=self._title_hint or self._current_title(),
            offset_x=offset_x,
            offset_y=offset_y,
            hotkey=child(self, QComboBox, "hotkeyCombo").currentText(),
            target_level=int(child(self, QComboBox, "targetCombo").currentData()),
            auto_start=child(self, QCheckBox, "autoStartCheck").isChecked(),
            autoclick_stop_on_level_up=child(self, QCheckBox, "stopOnLevelCheck").isChecked(),
            city=child(self, QComboBox, "cityCombo").currentText(),
            auto_city=child(self, QCheckBox, "autoCityCheck").isChecked(),
            autoclick_enabled=child(self, QCheckBox, "autoclickEnabledCheck").isChecked(),
        )
