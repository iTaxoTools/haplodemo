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

from __future__ import annotations

from PySide6 import QtCore, QtGui, QtWidgets

from itaxotools.common.utility import override


class RectBox(QtWidgets.QGraphicsRectItem):
    def __init__(self, items: list[QtWidgets.QGraphicsItem] = None):
        super().__init__()
        self.items = items or list()
        self.padding = 24
        self.corner_radius = 24
        self.adjust_position()
        self.setZValue(-80)
        self.setBrush(QtGui.QColor("#777"))
        self.setOpacity(0.3)

    @override
    def paint(self, painter, option, widget):
        path = QtGui.QPainterPath()
        path.addRoundedRect(self.rect(), self.corner_radius, self.corner_radius)

        painter.setBrush(self.brush())
        painter.setPen(self.pen())
        painter.drawPath(path)

    def setColor(self, color: str):
        self.setBrush(QtGui.QColor(color))

    def adjust_position(self):
        if not self.items:
            return

        bounds = QtCore.QRectF()
        for item in self.items:
            rect = QtCore.QRectF(item.rect())
            rect.translate(item.pos())
            bounds = bounds.united(rect)
        bounds.adjust(-self.padding, -self.padding, self.padding, self.padding)

        self.setRect(bounds)
