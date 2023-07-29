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

from .nodes import Label, Node
from .types import Direction


class Scale(QtWidgets.QGraphicsItem):
    def __init__(self, settings, marks=[1, 10, 100], parent=None):
        super().__init__(parent)
        self.settings = settings
        self.state_hovered = False

        self._highlight_color = QtCore.Qt.magenta
        self._pen = QtGui.QPen(QtCore.Qt.black, 2)
        self._pen_high = QtGui.QPen(self._highlight_color, 4)
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

        self.setFlag(QtWidgets.QGraphicsItem.ItemIsMovable, True)
        self.setAcceptHoverEvents(True)
        self.setZValue(70)

    @override
    def boundingRect(self):
        return QtCore.QRect(0, 0, self.radius * 2, self.radius)

    @override
    def shape(self):
        rect = QtCore.QRect(0, 0, self.radius * 2, self.radius * 2)
        path = QtGui.QPainterPath()
        path.arcMoveTo(rect, 0)
        path.arcTo(rect, 0, 180)
        return path

    @override
    def paint(self, painter, options, widget=None):
        if self.state_hovered:
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
            painter.drawPath(path)

    @override
    def hoverEnterEvent(self, event):
        super().hoverEnterEvent(event)
        self.set_hovered(True)

    @override
    def hoverLeaveEvent(self, event):
        super().hoverLeaveEvent(event)
        self.set_hovered(False)

    def set_hovered(self, value):
        self.state_hovered = value
        for label in self.labels:
            label.set_hovered(value)
        self.update()

    def set_label_font(self, font):
        self.font = font
        metric = QtGui.QFontMetrics(font)
        self.font_height = metric.height()
        self.padding = metric.height() / 4
        self.place_labels()

        for label in self.labels:
            label.set_font(font)

    def set_highlight_color(self, value):
        self._highlight_color = value
        self.update_pens()
        for label in self.labels:
            label.set_highlight_color(value)
        self.update()

    def set_pen_width(self, value):
        self._pen_width = value
        self.update_pens()

    def update_pens(self):
        self._pen = QtGui.QPen(QtCore.Qt.black, self._pen_width)
        self._pen_high = QtGui.QPen(self._highlight_color, self._pen_width + self._pen_high_increment)

    def get_extended_rect(self):
        rect = self.boundingRect()
        for label in self.labels:
            label_rect = label.boundingRect()
            label_rect.translate(label.pos().toPoint())
            rect = rect.united(label_rect)
        return rect

    def set_marks(self, marks: list[int]):
        self.marks = marks
        self.update_radii()

    def update_radii(self):
        values = self.settings.node_sizes.get_all_values()
        radii = [Node.radius_from_size(size, *values) for size in self.marks]
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
            label.set_highlight_color(self._highlight_color)
            label.set_anchor(Direction.Right)
            label.setPos(radius * 2, self.radius + self.padding + self.font_height / 2)
            label.set_font(self.font)
            label.recenter()
            self.labels.append(label)