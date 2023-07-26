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
            case 'center', _:
                cursor = QtCore.Qt.SizeVerCursor
            case _, 'center':
                cursor = QtCore.Qt.SizeHorCursor
            case 'left', 'top':
                cursor = QtCore.Qt.SizeFDiagCursor
            case 'left', 'bottom':
                cursor = QtCore.Qt.SizeBDiagCursor
            case 'right', 'top':
                cursor = QtCore.Qt.SizeBDiagCursor
            case 'right', 'bottom':
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
            case 'right':
                x = parent.rect().right()
            case 'left':
                x = parent.rect().left() - self.size
            case 'center':
                width = parent.rect().width()
                x = parent.rect().left()

        match self.vertical:
            case 'top':
                y = parent.rect().top() - self.size
            case 'bottom':
                y = parent.rect().bottom()
            case 'center':
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

        if self.vertical == 'center':
            diff_y = 0
        elif self.horizontal == 'center':
            diff_x = 0

        rect = self.locked_rect.translated(diff_x, diff_y)
        parent = self.parentItem()

        if self.horizontal == 'right':
            limit = parent.rect().left() + parent.minimum_size
            if rect.left() < limit:
                rect.moveLeft(limit)
            parent.setEdge(QtCore.QRectF.setRight, rect.left())

        if self.horizontal == 'left':
            limit = parent.rect().right() - parent.minimum_size
            if rect.right() > limit:
                rect.moveRight(limit)
            parent.setEdge(QtCore.QRectF.setLeft, rect.right())

        if self.vertical == 'top':
            limit = parent.rect().bottom() - parent.minimum_size
            if rect.bottom() > limit:
                rect.moveBottom(limit)
            parent.setEdge(QtCore.QRectF.setTop, rect.bottom())

        if self.vertical == 'bottom':
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
            ['left', 'center', 'right'],
            ['top', 'center', 'bottom']))
        handles.remove(('center', 'center'))

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
