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

from typing import TYPE_CHECKING

from itaxotools.common.utility import override

from ..utility import shapeFromPath
from .protocols import HighlightableItem, SoloMovableItem

if TYPE_CHECKING:
    from .nodes import Vertex


class BezierHandleLine(QtWidgets.QGraphicsLineItem):
    def __init__(self, parent, p1, p2):
        super().__init__(p1.x(), p1.y(), p2.x(), p2.y(), parent)
        self.setPen(QtGui.QPen(QtGui.QColor("#333"), 1))


class BezierHandle(HighlightableItem, SoloMovableItem, QtWidgets.QGraphicsEllipseItem):
    def __init__(self, parent, point, r):
        """This is drawn above all other items"""
        super().__init__(-r, -r, r * 2, r * 2)
        self.parent = parent
        self.curve = parent.parentItem()
        self.locked_pos = None

        self.set_highlight_color(self.curve.highlight_color())

        self._pen = QtGui.QPen(QtCore.Qt.gray, 1)
        self._pen_high = QtGui.QPen(self.highlight_color(), 4)

        self.setCursor(QtCore.Qt.ArrowCursor)
        self.setFlag(QtWidgets.QGraphicsItem.ItemIsMovable, True)
        self.setFlag(QtWidgets.QGraphicsItem.ItemSendsGeometryChanges, True)
        self.setPen(QtGui.QPen(QtCore.Qt.gray, 1))
        self.setBrush(QtCore.Qt.red)
        self.setPos(point.x(), point.y())
        self.setZValue(90)

    @override
    def itemChange(self, change, value):
        if change == QtWidgets.QGraphicsItem.ItemPositionHasChanged:
            start_point = self.curve.pos()
            pos = self.pos() - start_point
            self.parent.setPos(pos)
        return super().itemChange(change, value)

    @override
    def paint(self, painter, options, widget=None):
        painter.save()
        rect = self.rect()
        if self.is_highlighted():
            rect = self.rect().adjusted(-2, -2, 2, 2)
            painter.setPen(self._pen_high)
        else:
            painter.setPen(self._pen)
        painter.setBrush(self.brush())
        painter.drawEllipse(rect)
        painter.restore()

    @override
    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self.locked_pos = self.pos()
            self.curve.lock_control_points()
        super().mousePressEvent(event)

    @override
    def mouseReleaseEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            if self.locked_pos != self.pos():
                self.curve.post_bezier_edit()
        super().mouseReleaseEvent(event)


class BezierHandlePhantom(QtWidgets.QGraphicsEllipseItem):
    def __init__(self, parent, point, r=7):
        """This is drawn on parent's Z level"""
        super().__init__(-r, -r, r * 2, r * 2, parent)
        self.setFlag(QtWidgets.QGraphicsItem.ItemSendsGeometryChanges, True)
        self.setPos(point.x(), point.y())
        self.setBrush(QtCore.Qt.NoBrush)
        self.setPen(QtCore.Qt.NoPen)

        self.handle = BezierHandle(self, point, r)
        self.scene().addItem(self.handle)

    @override
    def itemChange(self, change, value):
        if change == QtWidgets.QGraphicsItem.ItemPositionHasChanged:
            self.parentItem().move_handle(self)
        return super().itemChange(change, value)


class BezierCurve(HighlightableItem, QtWidgets.QGraphicsPathItem):
    def __init__(self, node1: Vertex, node2: Vertex, parent=None):
        super().__init__(parent)
        self.setAcceptedMouseButtons(QtCore.Qt.LeftButton)
        self.setCursor(QtCore.Qt.ArrowCursor)
        self.update_z_value()

        self.node1 = node1
        self.node2 = node2

        self.p1 = node1.pos()
        self.p2 = node2.pos()
        self.c1 = self.p1
        self.c2 = self.p2

        self.locked_p1 = self.p1
        self.locked_p2 = self.p2
        self.locked_c1 = self.c1
        self.locked_c2 = self.c2

        self.l1 = None
        self.l2 = None
        self.h1 = None
        self.h2 = None

        self._pen_width = 2
        self._pen_high_increment = 4
        self._pen = QtGui.QPen(QtCore.Qt.red, 2, QtCore.Qt.DotLine)
        self._pen_high = QtGui.QPen(self.highlight_color(), 6)
        self._pen_shape = QtGui.QPen(QtCore.Qt.black, 12)

        self.setPen(self._pen_shape)
        self.update_path()

    @override
    def shape(self):
        path = self.path()
        path.cubicTo(self.c2, self.c1, self.p1)
        pen = self.pen()
        pen.setWidth(pen.width() + 8)
        return shapeFromPath(path, pen)

    @override
    def paint(self, painter, options, widget=None):
        painter.save()
        if self.is_highlighted():
            painter.setPen(self._pen_high)
            painter.drawPath(self.path())
        painter.setPen(self._pen)
        painter.drawPath(self.path())
        painter.restore()

    @override
    def mouseDoubleClickEvent(self, event):
        if self.h1:
            self.remove_controls()
        else:
            self.add_controls()

    @override
    def set_highlight_color(self, value):
        super().set_highlight_color(value)
        self.update_pens()
        if self.h1:
            self.h1.handle.set_highlight_color(value)
        if self.h2:
            self.h2.handle.set_highlight_color(value)

    def set_pen_width(self, value):
        self._pen_width = value
        self.update_pens()

    def update_pens(self):
        self._pen = QtGui.QPen(QtCore.Qt.red, self._pen_width, QtCore.Qt.DotLine)
        self._pen_high = QtGui.QPen(
            self.highlight_color(), self._pen_width + self._pen_high_increment
        )
        self._pen_shape = QtGui.QPen(
            QtCore.Qt.black, self._pen_width + self._pen_high_increment * 2
        )
        self.update()

    def get_control_point_for_node(self, node):
        if node == self.node1:
            return self.c1
        if node == self.node2:
            return self.c2
        raise ValueError("node not in bezier")

    def get_control_point_lock_for_node(self, node):
        if node == self.node1:
            return self.locked_c1
        if node == self.node2:
            return self.locked_c2
        raise ValueError("node not in bezier")

    def set_control_point_for_node(self, node, point):
        if node == self.node1:
            self.c1 = point
            return
        if node == self.node2:
            self.c2 = point
            return
        raise ValueError("node not in bezier")

    def update_z_value(self, hover=False):
        z = -11 if hover else -12
        self.setZValue(z)

    def set_hovered(self, value):
        super().set_hovered(value)
        self.update_z_value(value)

    def add_controls(self):
        self.l1 = BezierHandleLine(self, self.p1, self.c1)
        self.l2 = BezierHandleLine(self, self.p2, self.c2)
        self.h1 = BezierHandlePhantom(self, self.c1)
        self.h2 = BezierHandlePhantom(self, self.c2)

    def remove_controls(self):
        if self.scene():
            self.scene().removeItem(self.l1)
            self.scene().removeItem(self.l2)
            self.scene().removeItem(self.h1.handle)
            self.scene().removeItem(self.h2.handle)
            self.scene().removeItem(self.h1)
            self.scene().removeItem(self.h2)
        self.l1 = None
        self.l2 = None
        self.h1 = None
        self.h2 = None

    def move_handle(self, handle):
        if handle is self.h1:
            self.c1 = handle.pos()
        if handle is self.h2:
            self.c2 = handle.pos()
        self.update_path()

    def update_path(self):
        path = QtGui.QPainterPath()
        path.moveTo(self.p1)
        path.cubicTo(self.c1, self.c2, self.p2)
        self.setPath(path)
        self.update_handle_lines()
        self.update_handle_points()
        self.update()

    def update_handle_lines(self):
        if self.l1:
            line = QtCore.QLineF(self.p1, self.c1)
            self.l1.setLine(line)
        if self.l2:
            line = QtCore.QLineF(self.p2, self.c2)
            self.l2.setLine(line)

    def update_handle_points(self):
        if self.h1:
            self.h1.handle.setPos(self.c1)
        if self.h2:
            self.h2.handle.setPos(self.c2)

    def adjust_position(self):
        self.p1 = self.node1.pos()
        self.p2 = self.node2.pos()
        self.update_path()

    def bump(self, away: float = 1.0, at: float = 0.5):
        line = QtCore.QLineF(self.p1, self.p2)
        center = line.center()
        normal = line.normalVector()
        normal.setLength(line.length() * away)
        pn = normal.p2() - normal.p1()
        p3 = center + pn

        l1 = QtCore.QLineF(self.p1, p3)
        self.c1 = l1.pointAt(at)
        l2 = QtCore.QLineF(self.p2, p3)
        self.c2 = l2.pointAt(at)

        self.update_path()

    def lock_control_points(self):
        self.locked_p1 = self.p1
        self.locked_p2 = self.p2
        self.locked_c1 = self.c1
        self.locked_c2 = self.c2

    def post_bezier_edit(self):
        if not self.scene():
            return
        self.scene().handle_bezier_edit(self)
