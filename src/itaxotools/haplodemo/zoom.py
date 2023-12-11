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


class ZoomEdit(QtWidgets.QLineEdit):
    scale = QtCore.Signal(float)

    def __init__(self, parent=None):
        super().__init__("100", parent)
        self.setStyleSheet("background: transparent; border: none;")
        self.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.setFixedWidth(50)
        self.setMaxLength(3)

        validator = QtGui.QRegularExpressionValidator(r"\d*")
        self.setValidator(validator)

    def focusOutEvent(self, event):
        self.setScale()
        super().focusOutEvent(event)

    def keyPressEvent(self, event):
        if event.key() in (QtCore.Qt.Key_Enter, QtCore.Qt.Key_Return):
            self.setScale()
        super().keyPressEvent(event)

    def getScale(self, value):
        if not value:
            value = 0.0
        value *= 100.0
        self.setText(f"{value:.0f}")

    def setScale(self):
        text = self.text()
        try:
            scale = float(text)
        except TypeError:
            scale = 0.0
        scale /= 100.0
        self.scale.emit(scale)


class ZoomButton(QtWidgets.QPushButton):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setStyleSheet(
            """
            ZoomButton {
                font: 14px;
                color: Palette(Shadow);
                background: transparent;
                border: none;
            }
            ZoomButton:hover {
                font: bold 18px;
                color: Palette(Text);
            }
            ZoomButton:pressed {
                font: bold 18px;
                color: Palette(Shadow);
            }

        """
        )


class ZoomControl(QtWidgets.QFrame):
    def __init__(self, view=None, parent=None):
        super().__init__(parent)
        self.setFixedWidth(160)
        self.setFixedHeight(24)

        label = QtWidgets.QLabel("Zoom: ")
        self.edit = ZoomEdit()
        percent = QtWidgets.QLabel("%")
        self.zoom_out = ZoomButton("-")
        self.zoom_in = ZoomButton("+")

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(4, 0, 4, 0)
        layout.setSpacing(0)
        layout.addWidget(label)
        layout.addSpacing(4)
        layout.addWidget(self.edit)
        layout.addWidget(percent)
        layout.addSpacing(8)
        layout.addWidget(self.zoom_out)
        layout.addSpacing(8)
        layout.addWidget(self.zoom_in)
        layout.addSpacing(8)
        layout.addStretch(1)
        self.setLayout(layout)

        self.setView(view)

    def setView(self, view):
        if not view:
            return

        view.scaled.connect(self.edit.getScale)
        self.edit.scale.connect(view.setScale)
        self.zoom_out.clicked.connect(view.zoomOut)
        self.zoom_in.clicked.connect(view.zoomIn)
