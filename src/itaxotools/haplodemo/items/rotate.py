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


class PivotHandle(QtWidgets.QGraphicsEllipseItem):
    def __init__(self, r=10):
        super().__init__(-r, -r, r * 2, r * 2)
        self.setFlag(QtWidgets.QGraphicsItem.ItemIsMovable, True)
        self.setAcceptHoverEvents(True)
        self.setZValue(90)

        self._highlight_color = QtCore.Qt.magenta
        self._pen = QtGui.QPen(QtCore.Qt.black, 1)
        self._pen_high = QtGui.QPen(self._highlight_color, 2)

        self.state_hovered = False
        self.scale = 1.0
        self.radius = 10
        self.adjust_scale()

    @override
    def boundingRect(self):
        rect = super().boundingRect()
        width = rect.width()
        height = rect.height()
        rect.setWidth(width * 2)
        rect.setHeight(height * 2)
        rect.translate(-width, -height)
        return super().boundingRect()

    @override
    def paint(self, painter, option, widget=None):
        if self.state_hovered:
            painter.setPen(self._pen_high)
            self.paint_pivot(painter)

        painter.setPen(self._pen)
        self.paint_pivot(painter)

    def paint_pivot(self, painter):
        rect = self.rect()
        center = rect.center()
        extra = rect.width() / 2

        painter.drawEllipse(rect)
        painter.drawLine(
            center.x(), rect.top() - extra,
            center.x(), rect.bottom() + extra)
        painter.drawLine(
            rect.left() - extra, center.y(),
            rect.right() + extra, center.y())

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
        self._highlight_color = value
        self.update_pens()
        self.update()

    def adjust_scale(self, scale=1.0):
        self.scale = scale
        self.update_radius()
        self.update_pens()

    def update_radius(self):
        r = self.radius / self.scale
        rect = QtCore.QRectF(-r, -r, r * 2, r * 2)
        self.setRect(rect)

    def update_pens(self):
        self._pen = QtGui.QPen(QtCore.Qt.black, 1 / self.scale)
        self._pen_high = QtGui.QPen(self._highlight_color, 4 / self.scale)
        self._pen_high.setCapStyle(QtCore.Qt.RoundCap)
