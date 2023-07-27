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

from math import log

from itaxotools.common.utility import override

from ..utility import shapeFromPath
from .types import Direction, EdgeDecoration, EdgeStyle


class Label(QtWidgets.QGraphicsItem):
    def __init__(self, text, parent):
        super().__init__(parent)
        self.setFlag(QtWidgets.QGraphicsItem.ItemIsMovable, False)
        self.setFlag(QtWidgets.QGraphicsItem.ItemSendsGeometryChanges, True)
        self.setAcceptHoverEvents(True)

        self._highlight_color = QtCore.Qt.magenta
        self._white_outline = False
        self._anchor = Direction.Center

        font = QtGui.QFont()
        font.setPixelSize(16)
        font.setFamily('Arial')
        font.setHintingPreference(QtGui.QFont.PreferNoHinting)
        self.font = font

        self.text = text
        self.rect = self.getTextRect()
        self.outline = self.getTextOutline()

        self.state_hovered = False
        self.state_pressed = False

        self.locked_rect = self.rect
        self.locked_pos = QtCore.QPointF(0, 0)

    @override
    def mouseReleaseEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self.locked_rect = self.rect
        super().mouseReleaseEvent(event)

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
    def mouseDoubleClickEvent(self, event):
        self.recenter()

    @override
    def hoverEnterEvent(self, event):
        super().hoverEnterEvent(event)
        self.set_hovered(True)
        parent = self.parentItem()
        if parent:
            parent.set_hovered(True)

    @override
    def hoverLeaveEvent(self, event):
        super().hoverLeaveEvent(event)
        self.set_hovered(False)
        parent = self.parentItem()
        if parent:
            parent.set_hovered(False)

    @override
    def boundingRect(self):
        return QtCore.QRect(self.rect)

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

    def paint_outline(self, painter):
        if self.isHighlighted():
            color = self._highlight_color
        elif self._white_outline:
            color = QtCore.Qt.white
        else:
            return
        pen = QtGui.QPen(color, 4, QtCore.Qt.SolidLine, QtCore.Qt.RoundCap, QtCore.Qt.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(QtGui.QBrush(color))
        painter.drawPath(self.outline)

    def paint_text(self, painter):
        pen = QtGui.QPen(QtGui.QColor('black'))
        painter.setPen(pen)
        painter.setBrush(QtCore.Qt.NoBrush)
        painter.setFont(self.font)
        painter.drawText(0, 0, self.text)

    def set_white_outline(self, value):
        self._white_outline = value
        self.update()

    def set_locked(self, value):
        self.setFlag(QtWidgets.QGraphicsItem.ItemIsMovable, not value)

    def set_highlight_color(self, value):
        self._highlight_color = value

    def set_hovered(self, value):
        self.state_hovered = value
        self.update()

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

    def isHighlighted(self):
        if self.state_pressed:
            return True
        if self.state_hovered:
            return True
        return False

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


class Edge(QtWidgets.QGraphicsLineItem):
    def __init__(self, node1, node2, weight=1):
        super().__init__()
        self.setAcceptHoverEvents(True)
        self.setZValue(-10)
        self.weight = weight
        self.segments = weight
        self.node1 = node1
        self.node2 = node2

        self.style = EdgeStyle.Bubbles
        self.state_hovered = False
        self.locked_label_pos = None
        self.locked_label_rect_pos = None
        self._highlight_color = QtCore.Qt.magenta

        self.label = Label(str(weight), self)
        self.label.set_white_outline(True)
        self.set_style(EdgeStyle.Bubbles)
        self.lockLabelPosition()

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
    def pen(self):
        cap = QtCore.Qt.SquareCap
        style = QtCore.Qt.SolidLine
        if self.style.has_dots:
            cap = QtCore.Qt.FlatCap
            style = QtCore.Qt.DotLine
        return QtGui.QPen(QtCore.Qt.black, 2, style, cap)

    @override
    def paint(self, painter, options, widget=None):
        painter.save()

        if self.state_hovered:
            self.paintHoverLine(painter)

        pen = self.pen()

        painter.setPen(pen)
        painter.setBrush(pen.color())

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
        pen = QtGui.QPen(self._highlight_color, 6)
        painter.setPen(pen)
        painter.drawLine(self.line())
        painter.restore()

    def paintBubbles(self, painter):
        if self.segments <= 1:
            return

        line = self.line()

        if (self.segments - 1) * 6 > line.length():
            self.paintError(painter)
            return

        for dot in range(1, self.segments):
            point = line.pointAt(dot / self.segments)
            self.paintBubble(painter, point)

    def paintBubble(self, painter, point):
        if self.state_hovered:
            painter.save()
            painter.setPen(QtCore.Qt.NoPen)
            painter.setBrush(self._highlight_color)
            painter.drawEllipse(point, 6, 6)
            painter.restore()
        painter.drawEllipse(point, 2.5, 2.5)

    def paintBars(self, painter):
        if self.segments == 0:
            return

        bars = self.segments
        line = self.line()

        length = 12
        spacing = 6
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

        length = 12
        spacing = 6
        offset = (strikes - 1) * spacing / 2

        if offset * 2 > line.length():
            self.paintError(painter)
            return

        center = line.center()
        unit = line.unitVector()
        unit.translate(center - unit.p1())
        normal = unit.normalVector()
        strike = QtCore.QLineF(
            0, 0,
            2 * normal.dx() + unit.dx(),
            2 * normal.dy() + unit.dy())
        strike.setLength(length / 2)

        for count in range(strikes):
            point = unit.pointAt(count * spacing - offset)
            self.drawBar(painter, point, strike)

    def drawBar(self, painter, point, bar):
        bar = bar.translated(point)
        bar = QtCore.QLineF(bar.pointAt(-1), bar.pointAt(1))

        if self.state_hovered:
            painter.save()
            pen = QtGui.QPen(self._highlight_color, 6)
            painter.setPen(pen)
            painter.drawLine(bar)
            painter.restore()
        painter.drawLine(bar)

    def paintError(self, painter):
        painter.save()
        line = self.line()
        if self.state_hovered:
            pen = QtGui.QPen(self._highlight_color, 20, QtCore.Qt.SolidLine, QtCore.Qt.RoundCap)
            painter.setPen(pen)
            painter.drawLine(line)
        pen = QtGui.QPen(QtCore.Qt.black, 12, QtCore.Qt.SolidLine, QtCore.Qt.RoundCap)
        painter.setPen(pen)
        painter.drawLine(line)

        painter.restore()

    def set_style(self, style):
        self.style = style
        self.label.setVisible(self.style.has_text)
        self.resetLabelPosition(style.text_offset)
        self.update()

    def set_hovered(self, value):
        self.state_hovered = value
        self.label.set_hovered(value)
        if value:
            self.setZValue(-5)
        else:
            self.setZValue(-10)
        self.update()

    def set_highlight_color(self, value):
        self._highlight_color = value

    def set_label_font(self, value):
        self.label.set_font(value)

    def resetLabelPosition(self, offset: bool | None):
        if not offset:
            self.label.setPos(0, 0)
            self.label.recenter()
            return

        line = self.line()
        center = line.center()
        unit = line.unitVector()
        normal = line.normalVector().unitVector()
        point = QtCore.QLineF(0, 0, - offset * normal.dx() + offset * unit.dx(), - offset * normal.dy() + offset * unit.dy())
        point.translate(center)

        self.label.setPos(point.p2())
        self.label.recenter()

    def lockLabelPosition(self):
        angle = self.line().angle()
        transform = QtGui.QTransform().rotate(angle)

        pos = self.label.pos()
        pos = transform.map(pos)
        self.locked_label_pos = pos

        rpos = self.label.pos() + self.label.rect.center()
        rpos = transform.map(rpos)
        self.locked_label_rect_pos = rpos

    def adjustLabelPosition(self):
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

    def adjustPosition(self):
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

        line.setLength(length - rad1 - rad2)

        unit = line.unitVector()
        unit.setLength(rad1)
        unit.translate(-unit.x1(), -unit.y1())

        line.translate(unit.x2(), unit.y2())

        center = line.center()
        self.setPos(center)
        line.translate(-center)
        self.setLine(line)

        if self.label.isVisible():
            self.adjustLabelPosition()


class Vertex(QtWidgets.QGraphicsEllipseItem):
    def __init__(self, x, y, r=2.5):
        super().__init__(-r, -r, r * 2, r * 2)

        self.parent = None
        self.children = list()
        self.siblings = list()
        self.edges = dict()

        self.setZValue(10)
        self.setAcceptHoverEvents(True)
        self.setFlag(QtWidgets.QGraphicsItem.ItemIsMovable, True)
        self.setFlag(QtWidgets.QGraphicsItem.ItemSendsGeometryChanges, True)
        self.setPen(QtGui.QPen(QtCore.Qt.black, 2))
        self.setBrush(self.pen().color())
        self.setPos(x, y)

        self._rotational_setting = None
        self._recursive_setting = None
        self._highlight_color = QtCore.Qt.magenta

        self.weight = r
        self.radius = r

        self.locked_pos = None
        self.locked_event_pos = None
        self.locked_angle = None
        self.locked_center = None

        self.state_hovered = False
        self.state_pressed = False

    @override
    def paint(self, painter, options, widget=None):
        painter.save()
        painter.setPen(self.getBorderPen())
        painter.setBrush(self.brush())
        rect = self.rect()
        if self.isHighlighted():
            r = self.radius
            rect = rect.adjusted(-r, -r, r, r)
        painter.drawEllipse(rect)
        painter.restore()

    @override
    def boundingRect(self):
        # Hack to prevent drag n draw glitch
        return self.rect().adjusted(-50, -50, 50, 50)

    @override
    def shape(self):
        path = QtGui.QPainterPath()
        path.addEllipse(self.rect().adjusted(-3, -3, 3, 3))
        return path

    @override
    def itemChange(self, change, value):
        self.parentItem()
        if change == QtWidgets.QGraphicsItem.ItemPositionHasChanged:
            for edge in self.edges.values():
                edge.adjustPosition()
        return super().itemChange(change, value)

    @override
    def hoverEnterEvent(self, event):
        super().hoverEnterEvent(event)
        self.set_hovered(True)
        self.setZValue(15)

    @override
    def hoverLeaveEvent(self, event):
        super().hoverLeaveEvent(event)
        self.set_hovered(False)
        self.setZValue(10)

    @override
    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            center = self.parent.scenePos() if self.parent else None
            for edge in self.edges.values():
                edge.lockLabelPosition()
            self.lockPosition(event, center)
            if self.isMovementRecursive():
                self.mapNodeEdgeRecursive(
                    type(self).lockPosition, [event, center], {},
                    Edge.lockLabelPosition, [], {})

        super().mousePressEvent(event)
        self.set_pressed(True)

    @override
    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        self.set_pressed(False)

    @override
    def mouseMoveEvent(self, event):
        if self.isMovementRotational():
            return self.moveRotationally(event)
        return self.moveOrthogonally(event)

    def isHighlighted(self):
        if self.state_pressed:
            return True
        if self.state_hovered:
            return True
        return False

    def getBorderPen(self):
        if self.isHighlighted():
            return QtGui.QPen(self._highlight_color, 4)
        return self.pen()

    def addChild(self, item, edge):
        item.parent = self
        item.edges[self] = edge
        self.edges[item] = edge
        self.children.append(item)
        edge.adjustPosition()

    def addSibling(self, item, edge):
        item.edges[self] = edge
        self.edges[item] = edge
        self.siblings.append(item)
        item.siblings.append(self)
        edge.adjustPosition()

    def set_pressed(self, value):
        self.state_pressed = value
        self.update()

    def set_hovered(self, value):
        self.state_hovered = value
        if self.parent and any((
            self.isMovementRotational(),
            self.isMovementRecursive())
        ):
            edge = self.edges[self.parent]
            edge.set_hovered(value)
        self.update()

    def set_rotational_setting(self, value):
        self._rotational_setting = value

    def set_recursive_setting(self, value):
        self._recursive_setting = value

    def set_highlight_color(self, value):
        self._highlight_color = value

    def isMovementRotational(self):
        if not self._rotational_setting:
            return False
        return isinstance(self.parent, Vertex)

    def isMovementRecursive(self):
        return self._recursive_setting

    def _mapRecursive(
        self, siblings,
        visited_nodes, visited_edges,
        node_func, node_args, node_kwargs,
        edge_func, edge_args, edge_kwargs,
    ):
        if self in visited_nodes:
            return
        visited_nodes.add(self)

        if node_func:
            node_func(self, *node_args, **node_kwargs)

        nodes = self.children
        if siblings:
            nodes += self.siblings

        for node in nodes:
            node._mapRecursive(
                True, visited_nodes, visited_edges,
                node_func, node_args, node_kwargs,
                edge_func, edge_args, edge_kwargs)

            edge = self.edges[node]
            if edge_func and edge not in visited_edges:
                edge_func(edge, *edge_args, **edge_kwargs)
            visited_edges.add(edge)

    def mapNodeRecursive(self, func, *args, **kwargs):
        self._mapRecursive(False, set(), set(), func, args, kwargs, None, None, None)

    def mapNodeEdgeRecursive(
        self,
        node_func, node_args, node_kwargs,
        edge_func, edge_args, edge_kwargs,
    ):
        self._mapRecursive(
            False, set(), set(),
            node_func, node_args, node_kwargs,
            edge_func, edge_args, edge_kwargs)

    def lockPosition(self, event, center=None):
        self.locked_event_pos = event.scenePos()
        self.locked_pos = self.pos()

        if center is not None:
            line = QtCore.QLineF(center, event.scenePos())
            self.locked_angle = line.angle()
            self.locked_center = center

    def applyTranspose(self, diff):
        self.setPos(self.locked_pos + diff)

    def applyTransform(self, transform):
        pos = transform.map(self.locked_pos)
        self.setPos(pos)

    def moveOrthogonally(self, event):
        epos = event.scenePos()
        diff = epos - self.locked_event_pos
        if self.isMovementRecursive():
            return self.mapNodeRecursive(type(self).applyTranspose, diff)
        return self.applyTranspose(diff)

    def moveRotationally(self, event):
        epos = event.scenePos()
        line = QtCore.QLineF(self.locked_center, epos)
        angle = self.locked_angle - line.angle()
        center = self.locked_center

        transform = QtGui.QTransform()
        transform.translate(center.x(), center.y())
        transform.rotate(angle)
        transform.translate(-center.x(), -center.y())

        if self.isMovementRecursive():
            return self.mapNodeRecursive(type(self).applyTransform, transform)
        return self.applyTransform(transform)


class Node(Vertex):
    def __init__(self, x, y, r, name, weights):
        super().__init__(x, y, r)
        self.weights = weights
        self.pies = dict()
        self.name = name

        self.label = Label(name, self)
        self.adjust_radius()

    @override
    def hoverEnterEvent(self, event):
        super().hoverEnterEvent(event)
        self.label.state_hovered = True
        self.label.update()

    @override
    def hoverLeaveEvent(self, event):
        super().hoverLeaveEvent(event)
        self.label.state_hovered = False
        self.label.update()

    @override
    def mouseDoubleClickEvent(self, event):
        super().mouseDoubleClickEvent(event)
        self.label.mouseDoubleClickEvent(event)

    @override
    def paint(self, painter, options, widget=None):
        self.paint_node(painter)
        self.paint_pies(painter)

    def paint_node(self, painter):
        painter.save()
        if self.pies:
            painter.setPen(QtCore.Qt.NoPen)
        else:
            painter.setPen(self.getBorderPen())
        painter.setBrush(self.brush())
        painter.drawEllipse(self.rect())
        painter.restore()

    def paint_pies(self, painter):
        if not self.pies:
            return
        painter.save()

        painter.setPen(QtCore.Qt.NoPen)
        starting_angle = 16 * 90

        for color, span in self.pies.items():
            painter.setBrush(QtGui.QBrush(color))
            painter.drawPie(self.rect(), starting_angle, span)
            starting_angle += span

        painter.setBrush(QtCore.Qt.NoBrush)
        painter.setPen(self.getBorderPen())
        painter.drawEllipse(self.rect())
        painter.restore()

    def update_colors(self, color_map):
        total_weight = sum(weight for weight in self.weights.values())

        weight_items = iter(self.weights.items())
        first_key, _ = next(weight_items)
        first_color = color_map[first_key]
        self.setBrush(QtGui.QBrush(first_color))

        self.pies = dict()
        for key, weight in weight_items:
            color = color_map[key]
            span = int(5760 * weight / total_weight)
            self.pies[color] = span

    def set_highlight_color(self, value):
        self._highlight_color = value

    def set_label_font(self, value):
        self.label.set_font(value)

    def adjust_radius(self, a=10, b=2, c=0.4, d=1, e=0, f=0):
        r = self.radius_from_size(self.weight, a, b, c, d, e, f)
        self.radius = r

        self.prepareGeometryChange()
        self.setRect(-r, -r, 2 * r, 2 * r)

    @classmethod
    def radius_from_size(cls, x, a, b, c, d, e, f):
        if a and b and c:
            return a * log(c * x + d, b) + e * x + f
        return e * x + f
