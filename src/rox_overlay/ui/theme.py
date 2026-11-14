"""Shared "Technical Glow" palette: the settings window matches the overlay."""

from __future__ import annotations

NAVY = "#070C1C"
PANEL = "#0E1730"
FIELD = "#121E3D"
BORDER = "#24365E"
TEXT = "#F4F7FF"
MUTED = "#8E9BBD"
CYAN = "#4DDBE8"
CYAN_SOFT = "#77E7FF"
VIOLET = "#8C7CFF"
GOLD = "#F5C86A"
AMBER = "#E3A04A"

SETTINGS_STYLESHEET = f"""
QWidget {{ background: {NAVY}; color: {TEXT}; font-size: 12px; }}
QLabel {{ background: transparent; }}
QLabel#titleLabel {{ font-size: 22px; font-weight: 750; color: {TEXT}; }}
QLabel#subtitleLabel {{ color: {MUTED}; font-size: 12px; }}
QLabel#licenseLabel, QLabel#versionLabel {{ font-size: 10px; color: {MUTED}; }}
QLabel#hintLabel {{ font-size: 11px; color: {MUTED}; }}
QLabel#hintLabel:disabled {{ color: #4A5470; }}
QLabel#priceNoteLabel {{ font-size: 11px; color: {MUTED}; }}
QLabel#cardTitle {{ font-size: 11px; font-weight: 750; letter-spacing: 2px; color: {TEXT}; }}
QLabel#fieldCaption {{ font-size: 11px; color: {MUTED}; margin-top: 2px; }}
QLabel#opacityValueLabel {{ font-weight: 650; color: {CYAN_SOFT}; }}
QLabel#statusLabel {{ font-weight: 650; color: {CYAN}; }}
QLabel#statusDot {{ color: {CYAN}; font-size: 10px; }}
QLabel#autoclickStatusLabel {{ font-size: 15px; font-weight: 700; color: {AMBER}; }}
QLabel#autoclickStatusLabel:disabled {{ color: #5A6482; }}
QLabel#hotkeyStatusLabel {{ font-size: 11px; color: {CYAN}; }}
QLabel#hotkeyStatusLabel:disabled {{ color: #5A6482; }}

QFrame#card {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #13204A, stop:1 #0C1530);
    border: 1px solid {BORDER}; border-top: 1px solid #3A5490; border-radius: 16px;
}}
QFrame#card QWidget {{ background: transparent; }}
QFrame#cardDivider {{ background: #22335A; border: none; }}
QFrame#statusPill {{
    background: rgba(77, 219, 232, 22); border: 1px solid rgba(77, 219, 232, 90); border-radius: 15px;
}}

QComboBox, QSpinBox {{
    background: {FIELD}; border: 1px solid {BORDER}; border-radius: 9px;
    padding: 6px 10px; min-height: 22px; selection-background-color: {CYAN}; selection-color: {NAVY};
}}
QFrame#card QComboBox, QFrame#card QSpinBox {{ background: {FIELD}; }}
QComboBox:hover, QSpinBox:hover {{ border-color: #3A5490; }}
QComboBox:focus, QSpinBox:focus {{ border-color: {CYAN}; }}
QComboBox:disabled, QSpinBox:disabled {{ color: #5A6482; border-color: #1B2747; }}
QComboBox QAbstractItemView {{
    background: {FIELD}; border: 1px solid {BORDER}; selection-background-color: #1F3366; outline: none;
}}

QPushButton {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #1D2C55, stop:1 #15214A);
    border: 1px solid #2E4272; border-top: 1px solid #45609E; border-radius: 10px;
    padding: 8px 16px; font-weight: 650; min-height: 20px;
}}
QFrame#card QPushButton {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #1D2C55, stop:1 #15214A);
}}
QPushButton:hover {{ border-color: {CYAN}; }}
QPushButton:pressed {{ background: #13204A; }}
QPushButton:disabled {{ color: #4E5872; border-color: #1B2747; background: #101A36; }}
QPushButton#monitorButton, QFrame#card QPushButton#monitorButton {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {CYAN}, stop:1 {VIOLET});
    color: #06101F; border: 1px solid rgba(255, 255, 255, 90); font-weight: 750;
}}
QPushButton#monitorButton:hover {{ border-color: #FFFFFF; }}
QPushButton#autoclickButton:enabled {{ border-color: rgba(140, 124, 255, 160); }}

QSlider::groove:horizontal {{ height: 6px; border-radius: 3px; background: {FIELD}; }}
QSlider::sub-page:horizontal {{
    border-radius: 3px; background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {CYAN}, stop:1 {VIOLET});
}}
QSlider::handle:horizontal {{
    width: 16px; margin: -6px 0; border-radius: 8px; background: {TEXT}; border: 2px solid {CYAN};
}}
QToolTip {{ background: {PANEL}; color: {TEXT}; border: 1px solid {BORDER}; padding: 4px; }}
"""
