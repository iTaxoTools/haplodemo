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

from itertools import product

from itaxotools.common.utility import override

from .types import Direction


class BoundaryEdgeHandle(QtWidgets.QGraphicsRectItem):

    def __init__(self, parent, horizontal, vertical, size):
        super().__init__(parent)

        self.horizontal = horizontal
        self.vertical = vertical
        self.size = size

        self.locked_pos = QtCore.QPointF()
        self.locked_rect = self.rect()
        self.item_block = False

        self.setFlag(QtWidgets.QGraphicsItem.ItemIsMovable, True)
        self.setAcceptHoverEvents(True)
        self.setBrush(QtCore.Qt.green)
        self.setPen(QtCore.Qt.NoPen)

        self.adjustCursor()
        self.adjustRect()

    def adjustCursor(self):
        match self.horizontal, self.vertical:
            case Direction.Center, _:
                cursor = QtCore.Qt.SizeVerCursor
            case _, Direction.Center:
                cursor = QtCore.Qt.SizeHorCursor
            case Direction.Left, Direction.Top:
                cursor = QtCore.Qt.SizeFDiagCursor
            case Direction.Left, Direction.Bottom:
                cursor = QtCore.Qt.SizeBDiagCursor
            case Direction.Right, Direction.Top:
                cursor = QtCore.Qt.SizeBDiagCursor
            case Direction.Right, Direction.Bottom:
                cursor = QtCore.Qt.SizeFDiagCursor
            case _, _:
                cursor = QtCore.Qt.SizeAllCursor
        self.setCursor(cursor)

    def adjustRect(self):
        parent = self.parentItem()
        width = self.size
        height = self.size
        x = 0
        y = 0

        match self.horizontal:
            case Direction.Right:
                x = parent.rect().right()
            case Direction.Left:
                x = parent.rect().left() - self.size
            case Direction.Center:
                width = parent.rect().width()
                x = parent.rect().left()

        match self.vertical:
            case Direction.Top:
                y = parent.rect().top() - self.size
            case Direction.Bottom:
                y = parent.rect().bottom()
            case Direction.Center:
                height = parent.rect().height()
                y = parent.rect().top()

        rect = QtCore.QRect(x, y, width, height)
        self.prepareGeometryChange()
        self.setRect(rect)

    @override
    def mousePressEvent(self, event):
        if self.scene().getItemAtPos(event.scenePos()):
            self.item_block = True
            return
        self.item_block = False

        super().mousePressEvent(event)
        self.locked_rect = self.rect()
        self.locked_pos = event.scenePos()

    @override
    def mouseMoveEvent(self, event):
        if self.item_block:
            return

        pos = event.scenePos()
        diff_x = pos.x() - self.locked_pos.x()
        diff_y = pos.y() - self.locked_pos.y()

        if self.vertical == Direction.Center:
            diff_y = 0
        elif self.horizontal == Direction.Center:
            diff_x = 0

        rect = self.locked_rect.translated(diff_x, diff_y)
        parent = self.parentItem()

        if self.horizontal == Direction.Right:
            limit = parent.rect().left() + parent.minimum_size
            if rect.left() < limit:
                rect.moveLeft(limit)
            parent.setEdge(QtCore.QRectF.setRight, rect.left())

        if self.horizontal == Direction.Left:
            limit = parent.rect().right() - parent.minimum_size
            if rect.right() > limit:
                rect.moveRight(limit)
            parent.setEdge(QtCore.QRectF.setLeft, rect.right())

        if self.vertical == Direction.Top:
            limit = parent.rect().bottom() - parent.minimum_size
            if rect.bottom() > limit:
                rect.moveBottom(limit)
            parent.setEdge(QtCore.QRectF.setTop, rect.bottom())

        if self.vertical == Direction.Bottom:
            limit = parent.rect().top() + parent.minimum_size
            if rect.top() < limit:
                rect.moveTop(limit)
            parent.setEdge(QtCore.QRectF.setBottom, rect.top())

    @override
    def paint(self, painter, option, widget=None):
        """Do not paint"""


class BoundaryOutline(QtWidgets.QGraphicsRectItem):
    def __init__(self, parent):
        super().__init__(parent)
        self.setPen(QtGui.QPen(QtCore.Qt.black, 1, QtCore.Qt.PenStyle.DashLine))
        self.adjustRect()

    def adjustRect(self):
        m = self.parentItem().margin
        rect = self.parentItem().rect()
        rect.adjust(-m, -m, m, m)
        self.prepareGeometryChange()
        self.setRect(rect)


class BoundaryRect(QtWidgets.QGraphicsRectItem):
    def __init__(self, x, y, w, h):
        super().__init__(x, y, w, h)
        self.minimum_size = 32
        self.margin = 8

        self.setBrush(QtCore.Qt.white)
        self.setZValue(-99)

        handles = list(product(
            [Direction.Left, Direction.Center, Direction.Right],
            [Direction.Top, Direction.Center, Direction.Bottom]))
        handles.remove((Direction.Center, Direction.Center))

        self.handles = [
            BoundaryEdgeHandle(self, horizontal, vertical, self.margin)
            for horizontal, vertical in handles]
        self.outline = BoundaryOutline(self)

    def setEdge(self, method, value):
        rect = QtCore.QRectF(self.rect())
        method(rect, value)

        self.prepareGeometryChange()
        self.setRect(rect)

        self.outline.adjustRect()
        for handle in self.handles:
            handle.adjustRect()