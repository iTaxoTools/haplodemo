# -----------------------------------------------------------------------------
# Haplodemo - Visualize, edit and export haplotype networks
# Copyright (C) 2023  Patmanidis Stefanos
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
# -----------------------------------------------------------------------------

from PySide6 import QtCore, QtGui, QtWidgets

from itaxotools.common.utility import Guard

from .models import PartitionListModel
from .palettes import Palette


class GLineEdit(QtWidgets.QLineEdit):
    textEditedSafe = QtCore.Signal(str)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.textEdited.connect(self._handleEdit)
        self._guard = Guard()

    def _handleEdit(self, text):
        with self._guard:
            self.textEditedSafe.emit(text)

    def setText(self, text):
        if self._guard:
            return
        super().setText(text)


class RadioButtonGroup(QtCore.QObject):
    valueChanged = QtCore.Signal(object)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.members = dict()
        self.value = None

    def add(self, widget, value):
        self.members[widget] = value
        widget.toggled.connect(self.handleToggle)

    def handleToggle(self, checked):
        if not checked:
            return
        self.value = self.members[self.sender()]
        self.valueChanged.emit(self.value)

    def setValue(self, newValue):
        self.value = newValue
        for widget, value in self.members.items():
            widget.setChecked(value == newValue)


class ToggleButton(QtWidgets.QPushButton):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setCheckable(True)
        self.checkmark = QtGui.QPolygon(
            [QtCore.QPoint(-3, 0), QtCore.QPoint(-2, 3), QtCore.QPoint(5, -5)]
        )

    def paintEvent(self, event):
        super().paintEvent(event)
        if not self.isChecked():
            return

        m = QtGui.QFontMetrics(self.font())
        w = self.width() - m.boundingRect(self.text()).width()
        w = w / 2 - 14
        h = self.height() / 2 + 1

        painter = QtGui.QPainter(self)
        painter.translate(w, h)
        painter.setPen(QtGui.QPen(QtGui.QColor("#333"), 1.5))
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        painter.drawPolyline(self.checkmark)
        painter.end()

    def sizeHint(self):
        return super().sizeHint() + QtCore.QSize(48, 0)


class PartitionSelector(QtWidgets.QComboBox):
    modelIndexChanged = QtCore.Signal(QtCore.QModelIndex)

    def __init__(self, model: PartitionListModel):
        super().__init__()
        self.setModel(model)
        self.currentIndexChanged.connect(self.handleIndexChanged)

    def handleIndexChanged(self, row: int):
        index = self.model().index(row, 0)
        self.modelIndexChanged.emit(index)

    def setModelIndex(self, index: QtCore.QModelIndex):
        self.setCurrentIndex(index.row())


class PaletteSelector(QtWidgets.QComboBox):
    currentValueChanged = QtCore.Signal(Palette)

    def __init__(self):
        super().__init__()
        self._palettes = []
        for palette in Palette:
            self._palettes.append(palette)
            self.addItem(palette.label)
        self.currentIndexChanged.connect(self.handleIndexChanged)

    def handleIndexChanged(self, index):
        self.currentValueChanged.emit(self._palettes[index]())

    def setValue(self, value):
        index = self._palettes.index(value.type)
        self.setCurrentIndex(index)


class PenWidthSlider(QtWidgets.QSlider):
    def __init__(self):
        super().__init__(QtCore.Qt.Horizontal)
        self.setTickPosition(QtWidgets.QSlider.TicksAbove)
        self.setTickInterval(10)
        self.setSingleStep(1)
        self.setPageStep(10)
        self.setMinimum(0)
        self.setMaximum(40)


class PenWidthField(GLineEdit):
    valueChanged = QtCore.Signal(float)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setTextMargins(2, 0, 2, 0)
        self.setFixedWidth(60)

        self.textEditedSafe.connect(self.handleValueChanged)

        validator = QtGui.QDoubleValidator()
        validator.setNotation(QtGui.QDoubleValidator.StandardNotation)
        validator.setDecimals(2)
        validator.setBottom(0)
        self.setValidator(validator)

    def setValue(self, value):
        text = self.text_from_value(value)
        self.setText(text)

    def handleValueChanged(self, text):
        value = self.value_from_text(text)
        self.valueChanged.emit(value)

    @staticmethod
    def text_from_value(value: float) -> str:
        try:
            locale = QtCore.QLocale.system()
            return locale.toString(float(value), "f", 2)
        except Exception:
            return ""

    @staticmethod
    def value_from_text(text: str) -> float:
        try:
            locale = QtCore.QLocale.system()
            value, ok = locale.toFloat(text)
            if not ok:
                return 0.0
            return value
        except Exception:
            return 0.0


class ClickableLineEdit(QtWidgets.QLineEdit):
    clicked = QtCore.Signal(bool)

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        self.clicked.emit(True)


class ClickableSpinBox(QtWidgets.QSpinBox):
    clicked = QtCore.Signal(bool)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setLineEdit(ClickableLineEdit(self))
        self.lineEdit().clicked.connect(self.clicked.emit)

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        self.clicked.emit(True)

    def set_text_black(self, black: bool):
        color = "Palette(Text)" if black else "Palette(Dark)"
        self.lineEdit().setStyleSheet(f"QLineEdit {{ color: {color}; }}")


class ClickableDoubleSpinBox(QtWidgets.QDoubleSpinBox):
    clicked = QtCore.Signal(bool)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setLineEdit(ClickableLineEdit(self))
        self.lineEdit().clicked.connect(self.clicked.emit)

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        self.clicked.emit(True)

    def set_text_black(self, black: bool):
        color = "Palette(Text)" if black else "Palette(Dark)"
        self.lineEdit().setStyleSheet(f"QLineEdit {{ color: {color}; }}")
