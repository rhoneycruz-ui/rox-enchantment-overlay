"""iOS-style toggle switch: label on the left, sliding pill on the right.

It is a ``QCheckBox`` underneath, so ``isChecked``/``toggled`` keep working
everywhere (settings code, tests, keyboard focus and Space to toggle).
"""

from __future__ import annotations

from PySide6.QtCore import Property, QEasingCurve, QPoint, QPointF, QPropertyAnimation, QRectF, QSize, Qt
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPaintEvent, QPen
from PySide6.QtWidgets import QCheckBox, QWidget

TRACK_W = 40
TRACK_H = 22
ON_START = QColor("#4DDBE8")
ON_END = QColor("#8C7CFF")
OFF = QColor("#1B2849")
OFF_BORDER = QColor("#2E4272")
TEXT = QColor("#E8EEFF")
TEXT_DISABLED = QColor("#56607A")


class ToggleSwitch(QCheckBox):
    def __init__(self, text: str = "", parent: QWidget | None = None) -> None:
        super().__init__(text, parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._position = 0.0
        self._animation = QPropertyAnimation(self, b"position", self)
        self._animation.setDuration(140)
        self._animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.toggled.connect(self._animate)

    # --- animated knob position (0 = off, 1 = on)
    def _get_position(self) -> float:
        return self._position

    def _set_position(self, value: float) -> None:
        self._position = value
        self.update()

    position = Property(float, _get_position, _set_position)

    def _animate(self, checked: bool) -> None:
        self._animation.stop()
        if not self.isVisible():
            self._set_position(1.0 if checked else 0.0)
            return
        self._animation.setStartValue(self._position)
        self._animation.setEndValue(1.0 if checked else 0.0)
        self._animation.start()

    def setChecked(self, checked: bool) -> None:  # noqa: N802 - Qt API
        super().setChecked(checked)
        if not self._animation.state() == QPropertyAnimation.State.Running:
            self._set_position(1.0 if checked else 0.0)

    # --- geometry
    def sizeHint(self) -> QSize:  # noqa: N802 - Qt API
        text_width = self.fontMetrics().horizontalAdvance(self.text())
        return QSize(text_width + TRACK_W + 18, max(TRACK_H + 6, self.fontMetrics().height() + 6))

    def hitButton(self, pos: QPoint) -> bool:  # noqa: N802 - Qt API
        return self.rect().contains(pos)

    # --- painting
    def paintEvent(self, event: QPaintEvent) -> None:  # noqa: N802 - Qt API
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        enabled = self.isEnabled()

        track = QRectF(self.width() - TRACK_W - 2, (self.height() - TRACK_H) / 2, TRACK_W, TRACK_H)
        text_rect = QRectF(0, 0, track.left() - 10, self.height())
        painter.setPen(TEXT if enabled else TEXT_DISABLED)
        painter.drawText(text_rect, int(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft), self.text())

        radius = TRACK_H / 2
        painter.setPen(QPen(OFF_BORDER, 1))
        painter.setBrush(OFF)
        painter.drawRoundedRect(track, radius, radius)
        if self._position > 0:
            fill = QLinearGradient(track.topLeft(), track.topRight())
            on_start, on_end = QColor(ON_START), QColor(ON_END)
            alpha = round(255 * self._position * (1.0 if enabled else 0.4))
            on_start.setAlpha(alpha)
            on_end.setAlpha(alpha)
            fill.setColorAt(0, on_start)
            fill.setColorAt(1, on_end)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(fill)
            painter.drawRoundedRect(track, radius, radius)

        knob_d = TRACK_H - 6
        x = track.left() + 3 + (TRACK_W - 6 - knob_d) * self._position
        knob = QRectF(x, track.top() + 3, knob_d, knob_d)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(0, 0, 0, 60))
        painter.drawEllipse(knob.translated(QPointF(0, 1)))
        painter.setBrush(QColor("#FFFFFF") if enabled else QColor("#8C95AD"))
        painter.drawEllipse(knob)
        if self.hasFocus():
            painter.setPen(QPen(QColor(77, 219, 232, 140), 1.5))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(track.adjusted(-2, -2, 2, 2), radius + 2, radius + 2)
        painter.end()
