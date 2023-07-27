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


class Scale(QtWidgets.QGraphicsItem):
    def __init__(self, settings, sizes, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.state_hovered = False
        self.highlight_color = QtCore.Qt.magenta
        self.font_height = 16
        self.padding = 8
        self.radius = 0
        self.radii = []
        self.sizes = []
        self.labels = []

        self.setSizes(sizes)

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
            painter.setPen(QtGui.QPen(self.highlight_color, 6))
            self.paint_radii(painter)

        painter.setPen(QtGui.QPen(QtCore.Qt.black, 2))
        self.paint_radii(painter)

    def paint_radii(self, painter):
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

    def set_highlight_color(self, value):
        self.highlight_color = value
        for label in self.labels:
            label.set_highlight_color(value)
        self.update()

    def set_label_font(self, font):
        metric = QtGui.QFontMetrics(font)
        self.font_height = metric.height()
        self.padding = metric.height() / 4
        self.placeLabels()

        for label in self.labels:
            label.set_font(font)

    def get_extended_rect(self):
        rect = self.boundingRect()
        for label in self.labels:
            label_rect = label.boundingRect()
            label_rect.translate(label.pos().toPoint())
            rect = rect.united(label_rect)
        return rect

    def setSizes(self, sizes: list[int]):
        args = self.settings.node_sizes.get_all_values()
        radii = [Node.radius_from_size(size, *args) for size in sizes]
        self.sizes = sizes
        self.radii = radii
        self.radius = max(radii)
        self.placeLabels()

    def placeLabels(self):
        for item in self.labels:
            self.scene().removeItem(item)
        self.labels = []

        for size, radius in zip(self.sizes, self.radii):
            label = Label(str(size), self)
            label.set_highlight_color(self.highlight_color)
            label.set_alignment('right')
            label.setPos(radius * 2, self.radius + self.padding + self.font_height / 2)
            label.recenter()
            self.labels.append(label)
