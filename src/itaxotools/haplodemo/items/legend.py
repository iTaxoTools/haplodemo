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


class LegendBubble(QtWidgets.QGraphicsEllipseItem):
    def __init__(self, x, y, r, color, parent=None):
        super().__init__(-r, -r, r * 2, r * 2, parent)
        self.setBrush(color)
        self.setPos(x, y)


class LegendLabel(QtWidgets.QGraphicsSimpleTextItem):
    def __init__(self, x, y, text, parent=None):
        super().__init__(text, parent)
        self.setPos(x, y)

        font = QtGui.QFont()
        font.setPixelSize(16)
        font.setFamily('Arial')
        font.setHintingPreference(QtGui.QFont.PreferNoHinting)
        self.setFont(font)


class LegendItem(QtWidgets.QGraphicsItem):
    def __init__(self, x, y, radius, color, key, parent=None):
        super().__init__(parent)
        self.setPos(x, y)
        self.key = key

        self.bubble = LegendBubble(0, 0, radius, color, parent=self)
        self.label = LegendLabel(radius * 2, -radius, key, parent=self)

    @override
    def boundingRect(self):
        return QtCore.QRect(0, 0, 0, 0)

    @override
    def paint(self, painter, options, widget=None):
        pass

    def update_color(self, color_map):
        color = QtGui.QColor(color_map[self.key])
        self.bubble.setBrush(color)

    def set_label_font(self, font):
        self.label.setFont(font)


class Legend(QtWidgets.QGraphicsRectItem):

    def __init__(self, divisions, parent=None):
        super().__init__(parent)

        self._highlight_color = QtCore.Qt.magenta

        self.divisions = divisions
        self.longest = 64
        self.padding = 8
        self.margin = 16
        self.radius = 8

        for index, division in enumerate(divisions):
            LegendItem(
                20, 30 * (index + 1),
                self.radius, QtGui.QColor(division.color),
                division.key, parent=self)

        self.setFlag(QtWidgets.QGraphicsItem.ItemIsMovable, True)
        self.setAcceptHoverEvents(True)
        self.setBrush(QtCore.Qt.white)
        self.setZValue(50)
        self.adjustRect()

    @override
    def hoverEnterEvent(self, event):
        super().hoverEnterEvent(event)
        self.setPen(QtGui.QPen(self._highlight_color, 4))
        self.update()

    @override
    def hoverLeaveEvent(self, event):
        super().hoverLeaveEvent(event)
        self.setPen(QtGui.QPen(QtCore.Qt.black, 1))
        self.update()

    def adjustRect(self):
        width = 2 * self.margin + self.longest
        width += 3 * self.radius
        height = 2 * self.margin
        height += len(self.divisions) * 2 * self.radius
        height += (len(self.divisions) - 1) * self.padding

        self.setRect(0, 0, width, height)

    def update_colors(self, color_map):
        for item in self.childItems():
            item.update_color(color_map)

    def set_highlight_color(self, color):
        self._highlight_color = color

    def set_label_font(self, font):
        metric = QtGui.QFontMetrics(font)
        height = metric.height()

        self.radius = height / 2
        self.padding = height / 2
        self.margin = height

        self.longest = max(
            metric.horizontalAdvance(division.key)
            for division in self.divisions)

        self.adjustRect()
        self.populate()

        for item in self.childItems():
            item.set_label_font(font)

    def populate(self):
        for item in self.childItems():
            self.scene().removeItem(item)

        for index, division in enumerate(self.divisions):
            LegendItem(
                self.margin + self.radius,
                self.margin + self.radius + index * (self.radius * 2 + self.padding),
                self.radius, QtGui.QColor(division.color),
                division.key, parent=self)
