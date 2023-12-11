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

from itaxotools.common.utility import override

from .labels import Label
from .protocols import HighlightableItem, SoloMovableItemWithHistory
from .types import Direction


class Scale(HighlightableItem, SoloMovableItemWithHistory, QtWidgets.QGraphicsItem):
    def __init__(self, settings, marks=[1, 10, 100], parent=None):
        super().__init__(parent)
        self.settings = settings

        self._pen = QtGui.QPen(QtCore.Qt.black, 2)
        self._pen_high = QtGui.QPen(self.highlight_color(), 4)
        self._pen_high_increment = 4
        self._pen_width = 2

        self.font = QtGui.QFont()
        self.font_height = 16
        self.padding = 8
        self.radius = 0
        self.radii = []
        self.marks = []
        self.labels = []

        self.set_marks(marks)

        self.setCursor(QtCore.Qt.ArrowCursor)
        self.setZValue(70)

    @override
    def boundingRect(self):
        return QtCore.QRect(0, -self.radius, self.radius * 2, self.radius)

    @override
    def shape(self):
        rect = QtCore.QRect(0, 0, self.radius * 2, self.radius * 2)
        path = QtGui.QPainterPath()
        path.arcMoveTo(rect, 0)
        path.arcTo(rect, 0, 180)
        path.translate(0, -self.radius)
        return path

    @override
    def paint(self, painter, options, widget=None):
        if self.is_highlighted():
            painter.setPen(self._pen_high)
            self.paint_marks(painter)

        painter.setPen(self._pen)
        self.paint_marks(painter)

    def paint_marks(self, painter):
        bottom_left = QtCore.QPoint(0, self.radius)

        for radius in self.radii:
            rect = QtCore.QRect(0, 0, radius * 2, radius * 2)
            rect.moveBottomLeft(bottom_left)
            rect.translate(0, radius)
            path = QtGui.QPainterPath()
            path.arcMoveTo(rect, 0)
            path.arcTo(rect, 0, 180)
            path.translate(0, -self.radius)
            painter.drawPath(path)

    def set_hovered(self, value):
        super().set_hovered(value)
        for label in self.labels:
            label.set_hovered(value)

    def set_label_font(self, font):
        self.font = font
        metric = QtGui.QFontMetrics(font)
        self.font_height = metric.height()
        self.padding = metric.height() / 4
        self.place_labels()

        for label in self.labels:
            label.set_font(font)

    @override
    def set_highlight_color(self, value):
        super().set_highlight_color(value)
        self.update_pens()
        for label in self.labels:
            label.set_highlight_color(value)

    def set_pen_width(self, value):
        self._pen_width = value
        self.update_pens()

    def update_pens(self):
        self._pen = QtGui.QPen(QtCore.Qt.black, self._pen_width)
        self._pen_high = QtGui.QPen(
            self.highlight_color(), self._pen_width + self._pen_high_increment
        )
        self._pen_high.setCapStyle(QtCore.Qt.RoundCap)

    def get_extended_rect(self):
        rect = self.boundingRect()
        for label in self.labels:
            label_rect = label.boundingRect()
            label_rect.translate(label.pos().toPoint())
            rect = rect.united(label_rect)
        return rect

    def get_bottom_margin(self):
        rect = self.get_extended_rect()
        diff = rect.height() + rect.y()
        if diff < 0:
            return 0
        return diff

    def set_marks(self, marks: list[int]):
        self.marks = marks
        self.update_radii()

    def update_radii(self):
        marks = self.marks or [1]
        radius_for_weight = self.settings.node_sizes.radius_for_weight
        radii = [radius_for_weight(size) for size in marks]
        self.radii = radii
        self.radius = max(radii)
        self.place_labels()
        self.update()

    def place_labels(self):
        for item in self.labels:
            self.scene().removeItem(item)
        self.labels = []

        for size, radius in zip(self.marks, self.radii):
            label = Label(str(size), self)
            label.set_highlight_color(self.highlight_color())
            label.set_anchor(Direction.Right)
            label.setPos(radius * 2, self.padding + self.font_height / 2)
            label.set_font(self.font)
            label.recenter()
            self.labels.append(label)

    def set_labels_locked(self, value):
        for label in self.labels:
            label.set_locked(value)
