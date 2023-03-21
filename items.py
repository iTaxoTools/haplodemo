from math import degrees, atan2

from PySide6 import QtWidgets
from PySide6 import QtGui
from PySide6 import QtCore


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
        self.setFlag(QtWidgets.QGraphicsItem.ItemIsMovable, True)
        self.setFlag(QtWidgets.QGraphicsItem.ItemSendsGeometryChanges, True)

        # This one option would be very convenient, but bugs out PDF export...
        # self.setFlag(QtWidgets.QGraphicsItem.ItemIgnoresTransformations, True)

        self._highlight_color = QtCore.Qt.magenta

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

    def set_locked(self, value):
        self.setFlag(QtWidgets.QGraphicsItem.ItemIsMovable, not value)

    def set_highlight_color(self, value):
        self._highlight_color = value

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

    def boundingRect(self):
        t = self.sceneTransform()
        angle = atan2(t.m12(), t.m11())
        t2 = QtGui.QTransform()
        t2.rotate(-degrees(angle))
        return t2.mapRect(self.rect)

    def shape(self):
        t = self.sceneTransform()
        angle = atan2(t.m12(), t.m11())
        t2 = QtGui.QTransform()
        t2.rotate(-degrees(angle))
        polygon = t2.mapToPolygon(self.rect)

        path = QtGui.QPainterPath()
        path.addPolygon(polygon)
        return path

    def paint(self, painter, options, widget=None):
        painter.save()

        t = self.sceneTransform()
        angle = atan2(t.m12(), t.m11())
        painter.rotate(-degrees(angle))

        pos = QtGui.QFontMetrics(self.font).boundingRect(self.text).center()
        pos -= self.rect.center()
        painter.translate(-pos)

        self.paint_outline(painter)
        self.paint_text(painter)

        painter.restore()

    def paint_outline(self, painter):
        if not self.isHighlighted():
            return
        color = self._highlight_color
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

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self.locked_rect = self.rect
            self.locked_pos = event.scenePos()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        epos = event.scenePos()
        diff = (epos - self.locked_pos).toPoint()

        self.prepareGeometryChange()
        self.rect = self.locked_rect.translated(diff)

    def mouseDoubleClickEvent(self, event):
        self.prepareGeometryChange()
        self.rect = self.getCenteredRect()


class Edge(QtWidgets.QGraphicsLineItem):
    def __init__(self, parent, node1, node2, segments=2):
        super().__init__(parent)
        self.setFlag(QtWidgets.QGraphicsItem.ItemStacksBehindParent, True)
        self.setPen(QtGui.QPen(QtCore.Qt.black, 2))
        self.setZValue(-1)
        self.segments = segments
        self.node1 = node1
        self.node2 = node2

        self.state_highlighted = False
        self._highlight_color = QtCore.Qt.magenta

    def paint(self, painter, options, widget=None):
        painter.save()

        if self.state_highlighted:
            pen = QtGui.QPen(self._highlight_color, 4)
        else:
            pen = self.pen()

        painter.setPen(pen)
        painter.setBrush(pen.color())

        painter.drawLine(self.line())

        if self.segments > 1:
            for dot in range(1, self.segments):
                center = self.line().pointAt(dot/self.segments)
                painter.drawEllipse(center, 2.5, 2.5)

        painter.restore()

    def set_highlight_color(self, value):
        self._highlight_color = value

    def boundingRect(self):
        # Expand to account for segment dots
        return super().boundingRect().adjusted(-50, -50, 50, 50)

    def adjustPosition(self):
        transform, _ = self.parentItem().sceneTransform().inverted()
        pos1 = transform.map(self.node1.scenePos())
        pos2 = transform.map(self.node2.scenePos())
        rad1 = self.node1.radius
        rad2 = self.node2.radius

        line = QtCore.QLineF(
            pos1.x(),
            pos1.y(),
            pos2.x(),
            pos2.y())
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


class Vertex(QtWidgets.QGraphicsEllipseItem):
    def __init__(self, x, y, r=2.5):
        super().__init__(-r, -r, r * 2, r * 2)
        self.setAcceptHoverEvents(True)
        self.setFlag(QtWidgets.QGraphicsItem.ItemIsMovable, True)
        self.setFlag(QtWidgets.QGraphicsItem.ItemSendsGeometryChanges, True)
        self.setPen(QtGui.QPen(QtCore.Qt.black, 2))
        self.setBrush(self.pen().color())
        self.setPos(x, y)

        self._rotational_setting = None
        self._highlight_color = QtCore.Qt.magenta

        self.radius = r
        self.locked_distance = None
        self.locked_rotation = None
        self.locked_angle = None
        self.locked_transform = None
        self.state_hovered = False
        self.state_pressed = False
        self.edges = dict()

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

    def addChild(self, item, segments=1):
        self.edges[item] = Edge(self, self, item, segments)
        item.setParentItem(self)
        self.adjustItemEdge(item)

    def boundingRect(self):
        # Hack to prevent drag n draw glitch
        return self.rect().adjusted(-50, -50, 50, 50)

    def shape(self):
        path = QtGui.QPainterPath()
        path.addEllipse(self.rect().adjusted(-3, -3, 3, 3))
        return path

    def itemChange(self, change, value):
        parent = self.parentItem()
        if change == QtWidgets.QGraphicsItem.ItemPositionHasChanged:
            if isinstance(parent, Vertex):
                parent.adjustItemEdge(self)
            elif isinstance(parent, Block):
                parent.adjustItemEdges(self)
        return super().itemChange(change, value)

    def adjustItemEdge(self, item):
        edge = self.edges[item]
        edge.adjustPosition()

    def lockTransform(self, event):
        line = QtCore.QLineF(0, 0, self.pos().x(), self.pos().y())
        self.locked_distance = line.length()
        self.locked_rotation = self.rotation()
        self.locked_angle = line.angle()

        clicked_pos = self.mapToParent(event.pos())
        eline = QtCore.QLineF(0, 0, clicked_pos.x(), clicked_pos.y())
        transform = QtGui.QTransform()
        transform.rotate(eline.angle() - line.angle())
        self.locked_transform = transform

    def set_rotational_setting(self, value):
        self._rotational_setting = value

    def set_highlight_color(self, value):
        self._highlight_color = value

    def isMovementRotational(self):
        if not self._rotational_setting:
            return False
        return isinstance(self.parentItem(), Vertex)

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self.lockTransform(event)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        epos = self.mapToParent(event.pos())
        if not self.isMovementRotational():
            self.setPos(epos)
            return

        line = QtCore.QLineF(0, 0, epos.x(), epos.y())
        line.setLength(self.locked_distance)
        line = self.locked_transform.map(line)
        new_pos = line.p2()
        new_angle = self.locked_angle - line.angle()
        self.setPos(new_pos)
        self.setRotation(self.locked_rotation + new_angle)


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

        t = self.sceneTransform()
        angle = atan2(t.m12(), t.m11())
        painter.rotate(-degrees(angle))

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

    def mouseDoubleClickEvent(self, event):
        super().mouseDoubleClickEvent(event)
        self.label.mouseDoubleClickEvent(event)


class Block(QtWidgets.QGraphicsItem):
    def __init__(self, parent):
        super().__init__(parent)
        self.setFlag(QtWidgets.QGraphicsItem.ItemStacksBehindParent, True)
        self.parent_node = parent
        self.edges = dict()
        self.main = None

    def setMainNode(self, node, segments=1):
        self.main = node
        edge = Edge(self, self.parent_node, node, segments)
        self.edges[node] = [edge]
        node.setParentItem(self)
        self.adjustItemEdges(node)

    def addNode(self, node, segments=1):
        self.edges[node] = []
        node.setParentItem(self)

    def addEdge(self, node1, node2, segments=1):
        edge = Edge(self, node1, node2, segments)
        self.edges[node1].append(edge)
        self.edges[node2].append(edge)
        edge.adjustPosition()

    def adjustItemEdges(self, node):
        for edge in self.edges[node]:
            edge.adjustPosition()

    def boundingRect(self):
        return QtCore.QRect(0, 0, 0, 0)

    def paint(self, painter, options, widget=None):
        pass
