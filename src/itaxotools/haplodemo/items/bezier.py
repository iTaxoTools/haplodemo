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

from ..utility import shapeFromPath
from .nodes import Vertex


class BezierHandleLine(QtWidgets.QGraphicsLineItem):
    def __init__(self, parent, p1, p2):
        super().__init__(p1.x(), p1.y(), p2.x(), p2.y(), parent)
        self.setPen(QtGui.QPen(QtGui.QColor('#333'), 1))


class BezierHandle(QtWidgets.QGraphicsEllipseItem):
    def __init__(self, parent, point, r):
        """This is drawn above all other items"""
        super().__init__(-r, -r, r * 2, r * 2)
        self.parent = parent

        self.setFlag(QtWidgets.QGraphicsItem.ItemIsMovable, True)
        self.setFlag(QtWidgets.QGraphicsItem.ItemSendsGeometryChanges, True)
        self.setPen(QtGui.QPen(QtCore.Qt.gray, 1))
        self.setBrush(QtCore.Qt.red)
        self.setPos(point.x(), point.y())
        self.setZValue(90)

    @override
    def itemChange(self, change, value):
        if change == QtWidgets.QGraphicsItem.ItemPositionHasChanged:
            start_point = self.parent.parentItem().pos()
            pos = self.pos() - start_point
            self.parent.setPos(pos)
        return super().itemChange(change, value)


class BezierHandlePhantom(QtWidgets.QGraphicsEllipseItem):
    def __init__(self, parent, point, r=7):
        """This is drawn on parent's Z level"""
        super().__init__(-r, -r, r * 2, r * 2, parent)
        self.setFlag(QtWidgets.QGraphicsItem.ItemSendsGeometryChanges, True)
        self.setPos(point.x(), point.y())

        self.handle = BezierHandle(self, point, r)
        self.scene().addItem(self.handle)

    @override
    def itemChange(self, change, value):
        if change == QtWidgets.QGraphicsItem.ItemPositionHasChanged:
            self.parentItem().moveHandle(self)
        return super().itemChange(change, value)


class BezierCurve(QtWidgets.QGraphicsPathItem):
    def __init__(self, node1: Vertex, node2: Vertex, parent=None):
        super().__init__(parent)
        self.setZValue(-20)

        self.node1 = node1
        self.node2 = node2

        self.p1 = node1.pos()
        self.p2 = node2.pos()
        self.c1 = self.p1
        self.c2 = self.p2
        self.h1 = None
        self.h2 = None

        self.l1 = None
        self.l2 = None
        self.h1 = None
        self.h2 = None

        self._pen = QtGui.QPen(QtCore.Qt.red, 2, QtCore.Qt.DotLine)
        self._pen_shape = QtGui.QPen(QtCore.Qt.black, 12)

        self.setPen(self._pen_shape)
        self.updatePath()

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
        painter.setPen(self._pen)
        painter.drawPath(self.path())
        painter.restore()

    @override
    def mouseDoubleClickEvent(self, event):
        if self.h1:
            self.removeControls()
        else:
            self.addControls()

    def addControls(self):
        self.l1 = BezierHandleLine(self, self.p1, self.c1)
        self.l2 = BezierHandleLine(self, self.p2, self.c2)
        self.h1 = BezierHandlePhantom(self, self.c1)
        self.h2 = BezierHandlePhantom(self, self.c2)

    def removeControls(self):
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

    def moveHandle(self, handle):
        if handle is self.h1:
            self.c1 = handle.pos()
        if handle is self.h2:
            self.c2 = handle.pos()
        self.updatePath()

    def updatePath(self):
        path = QtGui.QPainterPath()
        path.moveTo(self.p1)
        path.cubicTo(self.c1, self.c2, self.p2)
        self.setPath(path)
        self.updateHandleLines()

    def updateHandleLines(self):
        if self.l1:
            line = QtCore.QLineF(self.p1, self.c1)
            self.l1.setLine(line)
        if self.l2:
            line = QtCore.QLineF(self.p2, self.c2)
            self.l2.setLine(line)

    def adjustPosition(self):
        self.p1 = self.node1.pos()
        self.p2 = self.node2.pos()
        self.updatePath()

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

        self.updatePath()
