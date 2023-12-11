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

from ..utility import shapeFromPath
from .labels import Label
from .protocols import HighlightableItem
from .types import EdgeDecoration, EdgeStyle


class Edge(HighlightableItem, QtWidgets.QGraphicsLineItem):
    def __init__(
        self, node1: QtWidgets.QGraphicsItem, node2: QtWidgets.QGraphicsItem, weight=1
    ):
        super().__init__()
        self.setAcceptedMouseButtons(QtCore.Qt.LeftButton)
        self.setCursor(QtCore.Qt.ArrowCursor)
        self.weight = weight
        self.segments = weight
        self.node1 = node1
        self.node2 = node2

        self.style = EdgeStyle.Bubbles
        self.locked_style = self.style

        self.locked_label_pos = None
        self.locked_label_rect_pos = None

        self._pen = QtGui.QPen(QtCore.Qt.black, 2)
        self._pen_high = QtGui.QPen(self.highlight_color(), 4)
        self._pen_high_increment = 4
        self._pen_width = 2

        self.label = Label(str(weight), self)
        self.label.set_white_outline(True)
        self.set_style(EdgeStyle.Bubbles)
        self.lock_label_position()
        self.update_z_value()

    @override
    def shape(self):
        line = self.line()
        path = QtGui.QPainterPath()
        if line == QtCore.QLineF():
            return path
        path.moveTo(line.p1())
        path.lineTo(line.p2())
        pen = self.pen()
        pen.setWidth(pen.width() + 16)
        return shapeFromPath(path, pen)

    @override
    def mouseDoubleClickEvent(self, event):
        self.set_style(self.style.next)

    @override
    def hoverEnterEvent(self, event):
        super().hoverEnterEvent(event)
        self.set_hovered(True)

    @override
    def hoverLeaveEvent(self, event):
        super().hoverLeaveEvent(event)
        self.set_hovered(False)

    @override
    def boundingRect(self):
        # Expand to account for segment dots
        return super().boundingRect().adjusted(-5, -5, 5, 5)

    @override
    def paint(self, painter, options, widget=None):
        painter.save()

        if self.is_highlighted():
            self.paintHoverLine(painter)

        painter.setPen(self._pen)
        painter.setBrush(QtCore.Qt.black)

        painter.drawLine(self.line())

        if self.style.decoration == EdgeDecoration.Bubbles:
            self.paintBubbles(painter)
        elif self.style.decoration == EdgeDecoration.Bars:
            self.paintBars(painter)
        elif self.style.decoration == EdgeDecoration.DoubleStrike:
            self.paintDoubleStrike(painter)

        painter.restore()

    def paintHoverLine(self, painter):
        painter.save()
        painter.setPen(self._pen_high)
        painter.drawLine(self.line())
        painter.restore()

    def paintBubbles(self, painter):
        if self.segments <= 1:
            return

        line = self.line()

        radius = self._pen_width * 1.5 + 1
        radius_high = radius + self._pen_high_increment

        if (self.segments - 1) * radius_high > line.length():
            self.paintError(painter)
            return

        for dot in range(1, self.segments):
            point = line.pointAt(dot / self.segments)
            point = QtCore.QPointF(point)
            # Unless we use QPointF, bubble size isn't right
            self.paintBubble(painter, point, radius, radius_high)

    def paintBubble(self, painter, point, r=2.5, h=6):
        painter.setPen(QtCore.Qt.NoPen)
        if self.is_highlighted():
            painter.save()
            painter.setBrush(self.highlight_color())
            painter.drawEllipse(point, h, h)
            painter.restore()
        painter.setBrush(QtCore.Qt.black)
        painter.drawEllipse(point, r, r)

    def paintBars(self, painter):
        if self.segments == 0:
            return

        bars = self.segments
        line = self.line()

        length = 10 + self._pen_width
        spacing = 4 + self._pen_width
        offset = (bars - 1) * spacing / 2

        if offset * 2 > line.length():
            self.paintError(painter)
            return

        center = line.center()
        unit = line.unitVector()
        unit.translate(center - unit.p1())
        normal = unit.normalVector()
        bar = QtCore.QLineF(0, 0, normal.dx(), normal.dy())
        bar.setLength(length / 2)

        for count in range(bars):
            point = unit.pointAt(count * spacing - offset)
            self.drawBar(painter, point, bar)

    def paintDoubleStrike(self, painter):
        if self.segments <= 1:
            return

        strikes = 2
        line = self.line()

        length = 10 + self._pen_width
        spacing = 4 + self._pen_width
        offset = (strikes - 1) * spacing / 2

        if offset * 4 > line.length():
            self.paintError(painter)
            return

        center = line.center()
        unit = line.unitVector()
        unit.translate(center - unit.p1())
        normal = unit.normalVector()
        strike = QtCore.QLineF(
            0, 0, 2 * normal.dx() + unit.dx(), 2 * normal.dy() + unit.dy()
        )
        strike.setLength(length / 2)

        for count in range(strikes):
            point = unit.pointAt(count * spacing - offset)
            self.drawBar(painter, point, strike)

    def drawBar(self, painter, point, bar):
        bar = bar.translated(point)
        bar = QtCore.QLineF(bar.pointAt(-1), bar.pointAt(1))

        if self.is_highlighted():
            painter.save()
            pen = QtGui.QPen(self.highlight_color(), 6)
            painter.setPen(pen)
            painter.drawLine(bar)
            painter.restore()
        painter.drawLine(bar)

    def paintError(self, painter):
        radius = self._pen_width * 2 + 0.5
        radius_high = radius + self._pen_high_increment

        painter.save()
        line = self.line()
        if self.is_highlighted():
            pen = QtGui.QPen(
                self.highlight_color(),
                radius_high,
                QtCore.Qt.SolidLine,
                QtCore.Qt.RoundCap,
            )
            painter.setPen(pen)
            painter.drawLine(line)
        pen = QtGui.QPen(
            QtCore.Qt.black, radius, QtCore.Qt.SolidLine, QtCore.Qt.RoundCap
        )
        painter.setPen(pen)
        painter.drawLine(line)

        painter.restore()

    def update_z_value(self, hover=False):
        z = -21 if hover else -22
        self.setZValue(z)

    def set_style(self, style):
        self.style = style
        self.label.setVisible(self.style.has_text)
        self.reset_label_position(style.text_offset)
        self.update_pens()

    def set_hovered(self, value):
        self.label.set_hovered(value)
        self.update_z_value(value)
        super().set_hovered(value)

    def set_label_font(self, value):
        self.label.set_font(value)

    @override
    def set_highlight_color(self, value):
        super().set_highlight_color(value)
        self.label.set_highlight_color(value)
        self.update_pens()

    def set_pen_width(self, value):
        self._pen_width = value
        self.update_pens()

    def update_pens(self):
        cap = QtCore.Qt.SquareCap
        style = QtCore.Qt.SolidLine
        if self.style.has_dots:
            cap = QtCore.Qt.FlatCap
            style = QtCore.Qt.DotLine

        self._pen = QtGui.QPen(QtCore.Qt.black, self._pen_width, style, cap)
        self._pen_high = QtGui.QPen(
            self.highlight_color(), self._pen_width + self._pen_high_increment
        )
        self.update()

    def reset_label_position(self, offset: bool | None):
        if not offset:
            self.label.setPos(0, 0)
            self.label.recenter()
            return

        line = self.line()
        center = line.center()
        unit = line.unitVector()
        normal = line.normalVector().unitVector()
        point = QtCore.QLineF(
            0,
            0,
            -offset * normal.dx() + offset * unit.dx(),
            -offset * normal.dy() + offset * unit.dy(),
        )
        point.translate(center)

        self.label.setPos(point.p2())
        self.label.recenter()

    def lock_style(self):
        self.locked_style = self.style

    def lock_label_position(self):
        angle = self.line().angle()
        transform = QtGui.QTransform().rotate(angle)

        pos = self.label.pos()
        pos = transform.map(pos)
        self.locked_label_pos = pos

        rpos = self.label.pos() + self.label.rect.center()
        rpos = transform.map(rpos)
        self.locked_label_rect_pos = rpos

    def adjust_label_position(self):
        angle = self.line().angle()
        transform = QtGui.QTransform().rotate(-angle)

        pos = self.locked_label_pos
        pos = transform.map(pos)
        self.label.setPos(pos)

        rpos = self.locked_label_rect_pos
        rpos = transform.map(rpos)
        rect = self.label.rect
        rect.moveCenter((rpos - pos).toPoint())
        self.label.setRect(rect)

    def adjust_position(self):
        pos1 = self.node1.scenePos()
        pos2 = self.node2.scenePos()
        rad1 = self.node1.radius
        rad2 = self.node2.radius

        line = QtCore.QLineF(pos1, pos2)
        length = line.length()

        if length < (rad1 + rad2):
            self.hide()
            return
        self.show()

        line.setLength(length - rad1 - rad2 + 2)

        unit = line.unitVector()
        unit.setLength(rad1 - 1)
        unit.translate(-unit.x1(), -unit.y1())

        line.translate(unit.x2(), unit.y2())

        center = line.center()
        self.setPos(center)
        line.translate(-center)
        self.setLine(line)

        if self.label.isVisible():
            self.adjust_label_position()
