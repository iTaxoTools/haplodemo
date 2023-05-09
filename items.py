from PySide6 import QtWidgets
from PySide6 import QtGui
from PySide6 import QtCore

from enum import Enum

from itaxotools.common.utility import override

from utility import shapeFromPath


class EdgeStyle(Enum):
    Bubbles = 'Bubbles', True, False, False
    Plain = 'Plain', False, False, False
    Dots = 'Dots', False, True, False
    PlainWithText = 'Plain with text', False, False, True
    DotsWithText = 'Dots with text', False, True, True

    def __new__(cls, name, has_bubbles, has_dots, has_text):
        value = len(cls.__members__) + 1
        obj = object.__new__(cls)
        obj._value_ = value
        obj.label = name
        obj.has_bubbles = has_bubbles
        obj.has_dots = has_dots
        obj.has_text = has_text

        members = list(cls.__members__.values())
        if members:
            members[-1].next = obj
            obj.next = members[0]

        return obj

    def __repr__(self):
        cls_name = self.__class__.__name__
        return f'{cls_name}.{self._name_}'

    def __str__(self):
        return self.label


class BezierHandleLine(QtWidgets.QGraphicsLineItem):
    def __init__(self, parent, p1, p2):
        super().__init__(p1.x(), p1.y(), p2.x(), p2.y(), parent)
        self.setPen(QtGui.QPen(QtCore.Qt.gray, 1))


class BezierHandle(QtWidgets.QGraphicsEllipseItem):
    def __init__(self, parent, point, r=4):
        super().__init__(-r, -r, r * 2, r * 2, parent)
        self.setFlag(QtWidgets.QGraphicsItem.ItemIsMovable, True)
        self.setFlag(QtWidgets.QGraphicsItem.ItemSendsGeometryChanges, True)
        self.setPen(QtGui.QPen(QtCore.Qt.gray, 1))
        self.setBrush(QtCore.Qt.red)
        self.setPos(point.x(), point.y())

    def itemChange(self, change, value):
        if change == QtWidgets.QGraphicsItem.ItemPositionHasChanged:
            self.parentItem().moveHandle(self)
        return super().itemChange(change, value)


class BezierCurve(QtWidgets.QGraphicsPathItem):
    def __init__(self, p1, p2, parent=None):
        super().__init__(parent)
        self.p1 = p1
        self.p2 = p2
        self.c1 = p1
        self.c2 = p2
        self.h1 = None
        self.h2 = None

        self.l1 = None
        self.l2 = None
        self.h1 = None
        self.h2 = None

        self._pen = QtGui.QPen(QtCore.Qt.red, 2, QtCore.Qt.DotLine)
        self._pen_shape = QtGui.QPen(QtCore.Qt.black, 12)

        # Affects the clickable shape size
        self.setPen(self._pen_shape)
        self.updatePath()

    def paint(self, painter, options, widget=None):
        painter.save()
        painter.setPen(self._pen)
        painter.drawPath(self.path())
        painter.restore()

    def addControls(self):
        self.l1 = BezierHandleLine(self, self.p1, self.c1)
        self.l2 = BezierHandleLine(self, self.p2, self.c2)
        self.h1 = BezierHandle(self, self.c1)
        self.h2 = BezierHandle(self, self.c2)

    def removeControls(self):
        if self.scene():
            self.scene().removeItem(self.l1)
            self.scene().removeItem(self.l2)
            self.scene().removeItem(self.h1)
            self.scene().removeItem(self.h2)
        self.l1 = None
        self.l2 = None
        self.h1 = None
        self.h2 = None

    def moveHandle(self, handle):
        if handle is self.h1:
            self.c1 = handle.pos()
            line = QtCore.QLineF(self.p1, self.c1)
            self.l1.setLine(line)
        if handle is self.h2:
            self.c2 = handle.pos()
            line = QtCore.QLineF(self.p2, self.c2)
            self.l2.setLine(line)
        self.updatePath()

    def updatePath(self):
        path = QtGui.QPainterPath()
        path.moveTo(self.p1)
        path.cubicTo(self.c1, self.c2, self.p2)
        self.setPath(path)

    def mouseDoubleClickEvent(self, event):
        if self.h1:
            self.removeControls()
        else:
            self.addControls()


class Label(QtWidgets.QGraphicsItem):
    def __init__(self, text, parent):
        super().__init__(parent)
        self.setFlag(QtWidgets.QGraphicsItem.ItemIsMovable, False)
        self.setFlag(QtWidgets.QGraphicsItem.ItemSendsGeometryChanges, True)
        self.setAcceptHoverEvents(True)

        self._highlight_color = QtCore.Qt.magenta
        self._white_outline = False

        font = QtGui.QFont()
        font.setPixelSize(16)
        font.setFamily('Arial')
        font.setHintingPreference(QtGui.QFont.PreferNoHinting)
        self.font = font

        self.text = text
        self.rect = self.getCenteredRect()
        self.outline = self.getTextOutline()

        self.state_hovered = False
        self.state_pressed = False

        self.locked_rect = self.rect
        self.locked_pos = QtCore.QPointF(0, 0)

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

        self.prepareGeometryChange()
        self.rect = self.locked_rect.translated(diff)

    @override
    def mouseDoubleClickEvent(self, event):
        self.recenter()

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
        return self.rect

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

        self.paintOutline(painter)
        self.paintText(painter)

        painter.restore()

    def paintOutline(self, painter):
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

    def paintText(self, painter):
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

    def isHighlighted(self):
        if self.state_pressed:
            return True
        if self.state_hovered and self.scene().pressed_item is None:
            return True
        return False

    def getCenteredRect(self):
        rect = QtGui.QFontMetrics(self.font).tightBoundingRect(self.text)
        rect = rect.translated(-rect.center())
        rect = rect.adjusted(-3, -3, 3, 3)
        return rect

    def getTextOutline(self):
        path = QtGui.QPainterPath()
        path.setFillRule(QtCore.Qt.WindingFill)
        path.addText(0, 0, self.font, self.text)
        return path

    def recenter(self):
        self.prepareGeometryChange()
        self.rect = self.getCenteredRect()

class Edge(QtWidgets.QGraphicsLineItem):
    def __init__(self, node1, node2, segments=2):
        super().__init__()
        self.setAcceptHoverEvents(True)
        self.setZValue(-1)
        self.segments = segments
        self.node1 = node1
        self.node2 = node2

        self.style = EdgeStyle.Bubbles
        self.state_hovered = False
        self._highlight_color = QtCore.Qt.magenta

        self.label = Label(str(segments), self)
        self.label.set_white_outline(True)
        self.set_style(EdgeStyle.Bubbles)

    def shape(self):
        line = self.line()
        path = QtGui.QPainterPath()
        if line == QtCore.QLineF():
            return path
        path.moveTo(line.p1())
        path.lineTo(line.p2())
        pen = self.pen()
        pen.setWidth(pen.width() + 12)
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

        if self.style.has_bubbles:
            self.paintBubbles(painter)

        painter.restore()

    def paintHoverLine(self, painter):
        painter.save()
        pen = QtGui.QPen(self._highlight_color, 6)
        painter.setPen(pen)
        painter.drawLine(self.line())
        painter.restore()

    def paintBubbles(self, painter):
        if self.segments > 1:
            for dot in range(1, self.segments):
                center = self.line().pointAt(dot/self.segments)
                if self.state_hovered:
                    painter.save()
                    painter.setPen(QtCore.Qt.NoPen)
                    painter.setBrush(self._highlight_color)
                    painter.drawEllipse(center, 6, 6)
                    painter.restore()
                painter.drawEllipse(center, 2.5, 2.5)

    def set_style(self, style):
        self.style = style
        self.label.setVisible(self.style.has_text)
        self.label.recenter()
        self.update()

    def set_hovered(self, value):
        self.state_hovered = value
        self.label.set_hovered(value)

    def set_highlight_color(self, value):
        self._highlight_color = value

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
        self.setLine(line)

        center = line.pointAt(0.5)
        self.label.setPos(center)


class Vertex(QtWidgets.QGraphicsEllipseItem):
    def __init__(self, x, y, r=2.5):
        super().__init__(-r, -r, r * 2, r * 2)

        self.parent = None
        self.children = list()
        self.siblings = list()
        self.edges = dict()

        self.setAcceptHoverEvents(True)
        self.setFlag(QtWidgets.QGraphicsItem.ItemIsMovable, True)
        self.setFlag(QtWidgets.QGraphicsItem.ItemSendsGeometryChanges, True)
        self.setPen(QtGui.QPen(QtCore.Qt.black, 2))
        self.setBrush(self.pen().color())
        self.setPos(x, y)

        self._rotational_setting = None
        self._recursive_setting = None
        self._highlight_color = QtCore.Qt.magenta

        self.radius = r
        self.locked_distance = None
        self.locked_rotation = None
        self.locked_angle = None
        self.locked_transform = None
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
        parent = self.parentItem()
        if change == QtWidgets.QGraphicsItem.ItemPositionHasChanged:
            for edge in self.edges.values():
                edge.adjustPosition()
        return super().itemChange(change, value)

    @override
    def hoverEnterEvent(self, event):
        super().hoverEnterEvent(event)
        self.set_hovered(True)

    @override
    def hoverLeaveEvent(self, event):
        super().hoverLeaveEvent(event)
        self.set_hovered(False)

    @override
    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            center = self.parent.scenePos() if self.parent else None
            if self.isMovementRecursive():
                return self.applyRecursive(type(self).lockPosition, event, center)
            return self.lockPosition(event, center)

        super().mousePressEvent(event)
        self.set_pressed(True)

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        self.set_pressed(False)
        self.set_hovered(True)

    @override
    def mouseMoveEvent(self, event):
        if self.isMovementRotational():
            return self.moveRotationally(event)
        return self.moveOrthogonally(event)

    def isHighlighted(self):
        if self.state_pressed:
            return True
        if self.state_hovered and self.scene().pressed_item is None:
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
        if self.parent and self._rotational_setting:
            edge = self.edges[self.parent]
            edge.state_hovered = value
            edge.update()

    def set_hovered(self, value):
        self.state_hovered = value
        if self.parent and self._rotational_setting:
            edge = self.edges[self.parent]
            edge.set_hovered(value)

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

    def _applyRecursive(self, siblings, visited, func, *args, **kwargs):
        if self in visited:
            return
        visited.add(self)

        func(self, *args, **kwargs)

        for child in self.children:
            child._applyRecursive(True, visited, func, *args, **kwargs)

        if not siblings:
            return
        for sibling in self.siblings:
            sibling._applyRecursive(True, visited, func, *args, **kwargs)

    def applyRecursive(self, func, *args, **kwargs):
        self._applyRecursive(False, set(), func, *args, **kwargs)

    def lockPosition(self, event, center=None):
        self.locked_event_pos = event.scenePos()
        self.locked_pos = self.pos()

        if center:
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
            return self.applyRecursive(type(self).applyTranspose, diff)
        return self.applyTranspose(diff)

    def moveRotationally(self, event):
        epos = event.scenePos()
        line = QtCore.QLineF(self.locked_center, epos)
        angle =  self.locked_angle - line.angle()
        center = self.locked_center

        transform = QtGui.QTransform()
        transform.translate(center.x(), center.y())
        transform.rotate(angle)
        transform.translate(-center.x(), -center.y())

        if self.isMovementRecursive():
            return self.applyRecursive(type(self).applyTransform, transform)
        return self.applyTransform(transform)


class Node(Vertex):
    def __init__(self, x, y, r, text, weights):
        super().__init__(x, y, r)
        self.weights = weights
        self.pies = dict()
        self.text = text

        font = QtGui.QFont()
        font.setPixelSize(16)
        font.setFamily('Arial')
        self.font = font

        self.label = Label(text, self)

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
