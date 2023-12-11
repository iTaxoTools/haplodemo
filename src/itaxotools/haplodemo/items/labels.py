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

from .protocols import HighlightableItem, HoverableItem
from .types import Direction


class Label(HighlightableItem, QtWidgets.QGraphicsItem):
    def __init__(self, text, parent):
        super().__init__(parent)
        self._white_outline = False
        self._anchor = Direction.Center
        self._debug = False

        font = QtGui.QFont()
        font.setPixelSize(16)
        font.setFamily("Arial")
        font.setHintingPreference(QtGui.QFont.PreferNoHinting)
        self.font = font

        self.text = text
        self.rect = self.getTextRect()
        self.outline = self.getTextOutline()

        self.locked_rect = self.rect
        self.locked_pos = QtCore.QPointF(0, 0)

        self.setCursor(QtCore.Qt.ArrowCursor)
        self.setFlag(QtWidgets.QGraphicsItem.ItemIsMovable, False)
        self.setFlag(QtWidgets.QGraphicsItem.ItemSendsGeometryChanges, True)
        self.setAcceptedMouseButtons(QtCore.Qt.LeftButton)

    @override
    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self.locked_rect = self.rect
            self.locked_pos = event.scenePos()
        super().mousePressEvent(event)

    @override
    def mouseMoveEvent(self, event):
        epos = event.scenePos()
        diff = (epos - self.locked_pos).toPoint()
        rect = self.locked_rect.translated(diff)
        self.setRect(rect)

    @override
    def mouseReleaseEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            if self.locked_rect != self.rect:
                self.post_label_movement()
            self.locked_rect = self.rect
        super().mouseReleaseEvent(event)

    @override
    def mouseDoubleClickEvent(self, event):
        super().mouseDoubleClickEvent(event)
        self.recenter()

    @override
    def hoverEnterEvent(self, event):
        super().hoverEnterEvent(event)
        self.set_hovered(True)

    @override
    def hoverLeaveEvent(self, event):
        super().hoverLeaveEvent(event)
        hover = False
        parent = self.parentItem()
        if isinstance(parent, HoverableItem):
            hover = parent.is_hovered()
        self.set_hovered(hover)

    @override
    def boundingRect(self):
        try:
            return QtCore.QRect(self.rect)
        except Exception as e:
            print(self, vars(self))
            raise e

    @override
    def shape(self):
        path = QtGui.QPainterPath()
        path.addRect(self.rect)
        return path

    @override
    def paint(self, painter, options, widget=None):
        painter.save()

        pos = QtGui.QFontMetrics(self.font).boundingRect(self.text).center()
        pos -= self.rect.center()
        painter.translate(-pos)

        self.paint_outline(painter)
        self.paint_text(painter)

        painter.restore()

        if self._debug:
            painter.setPen(QtCore.Qt.green)
            painter.drawRect(self.boundingRect())
            painter.drawLine(-4, 0, 4, 0)
            painter.drawLine(0, -4, 0, 4)

    def paint_outline(self, painter):
        if (
            self.is_highlighted()
            or self.parentItem()
            and self.parentItem().isSelected()
        ):
            color = self.highlight_color()
        elif self._white_outline:
            color = QtCore.Qt.white
        else:
            return
        pen = QtGui.QPen(
            color, 4, QtCore.Qt.SolidLine, QtCore.Qt.RoundCap, QtCore.Qt.RoundJoin
        )
        painter.setPen(pen)
        painter.setBrush(QtGui.QBrush(color))
        painter.drawPath(self.outline)

    def paint_text(self, painter):
        pen = QtGui.QPen(QtGui.QColor("black"))
        painter.setPen(pen)
        painter.setBrush(QtCore.Qt.NoBrush)
        painter.setFont(self.font)
        painter.drawText(0, 0, self.text)

    def set_white_outline(self, value):
        self._white_outline = value
        self.update()

    def set_locked(self, value):
        self.setFlag(QtWidgets.QGraphicsItem.ItemIsMovable, not value)

    def set_font(self, font):
        if font is None:
            return
        font.setHintingPreference(QtGui.QFont.PreferNoHinting)
        self.font = font
        self.outline = self.getTextOutline()
        self.recenter()

    def set_anchor(self, value):
        self._anchor = value

    def setRect(self, rect):
        self.prepareGeometryChange()
        self.rect = rect

    def getTextRect(self):
        match self._anchor:
            case Direction.Center:
                return self.get_center_rect()
            case Direction.Left:
                return self.get_left_rect()
            case Direction.Right:
                return self.get_right_rect()

    def get_center_rect(self):
        rect = QtGui.QFontMetrics(self.font).tightBoundingRect(self.text)
        rect = rect.translated(-rect.center())
        rect = rect.adjusted(-3, -3, 3, 3)
        return rect

    def get_left_rect(self):
        rect = QtGui.QFontMetrics(self.font).tightBoundingRect(self.text)
        rect = rect.translated(0, -rect.center().y())
        rect = rect.adjusted(-3, -3, 3, 3)
        return rect

    def get_right_rect(self):
        rect = QtGui.QFontMetrics(self.font).tightBoundingRect(self.text)
        rect = rect.translated(-rect.width(), -rect.center().y())
        rect = rect.adjusted(-3, -3, 3, 3)
        return rect

    def getTextOutline(self):
        path = QtGui.QPainterPath()
        path.setFillRule(QtCore.Qt.WindingFill)
        path.addText(0, 0, self.font, self.text)
        return path

    def recenter(self):
        rect = self.getTextRect()
        self.setRect(rect)

    def setText(self, text):
        self.text = text
        self.outline = self.getTextOutline()
        rect = self.getTextRect()
        self.setRect(rect)

    def post_label_movement(self):
        if not self.scene():
            return
        self.scene().handle_label_movement(self)
