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

from .nodes import Node


class Scale(QtWidgets.QGraphicsItem):
    def __init__(self, settings, sizes, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.sizes = sizes
        self.state_hovered = False
        self.highlight_color = QtCore.Qt.magenta
        self.radius = 0
        self.radii = []

        self.setSizes(sizes)

        self.setFlag(QtWidgets.QGraphicsItem.ItemIsMovable, True)
        self.setAcceptHoverEvents(True)
        self.setZValue(70)

    @override
    def boundingRect(self):
        return QtCore.QRect(0, 0, self.radius * 2, self.radius)

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
        bottom_left = self.boundingRect().bottomLeft()

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
        self.update()

    def set_highlight_color(self, value):
        self.highlight_color = value
        self.update()

    def setSizes(self, sizes: list[int]):
        args = self.settings.get_all_node_args()
        radii = [Node.radius_from_size(size, *args) for size in sizes]
        self.radii = radii
        self.radius = max(radii)
