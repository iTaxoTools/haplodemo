from PySide6 import QtWidgets
from PySide6 import QtGui
from PySide6 import QtCore

from itaxotools.common.utility import override


class LabelNew(QtWidgets.QGraphicsItem):
    def __init__(self, text, parent):
        super().__init__(parent)
        self.setFlag(QtWidgets.QGraphicsItem.ItemIsMovable, True)
        self.setFlag(QtWidgets.QGraphicsItem.ItemSendsGeometryChanges, True)

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
        self.prepareGeometryChange()
        self.rect = self.getCenteredRect()

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

        self.paint_outline(painter)
        self.paint_text(painter)

        painter.restore()

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


class EdgeNew(QtWidgets.QGraphicsLineItem):
    def __init__(self, node1, node2, segments=2):
        super().__init__()
        # self.setFlag(QtWidgets.QGraphicsItem.ItemStacksBehindParent, True)
        self.setPen(QtGui.QPen(QtCore.Qt.black, 2))
        self.setZValue(-1)
        self.segments = segments
        self.node1 = node1
        self.node2 = node2

        self.state_highlighted = False
        self._highlight_color = QtCore.Qt.magenta

    @override
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

    @override
    def boundingRect(self):
        # Expand to account for segment dots
        return super().boundingRect().adjusted(-50, -50, 50, 50)

    def set_highlight_color(self, value):
        self._highlight_color = value

    def adjustPosition(self):
        pos1 = self.node1.scenePos()
        pos2 = self.node2.scenePos()
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


class VertexNew(QtWidgets.QGraphicsEllipseItem):
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

    def set_rotational_setting(self, value):
        self._rotational_setting = value

    def set_recursive_setting(self, value):
        self._recursive_setting = value

    def set_highlight_color(self, value):
        self._highlight_color = value

    def isMovementRotational(self):
        if not self._rotational_setting:
            return False
        return isinstance(self.parent, VertexNew)

    def isMovementRecursive(self):
        return self._recursive_setting

    def lockTransform(self, event, center=None, recursive=False):
        self.locked_event_pos = event.scenePos()
        self.locked_pos = self.pos()

        if center:
            line = QtCore.QLineF(center, event.scenePos())
            self.locked_angle = line.angle()
            self.locked_center = center

        if recursive:
            for child in self.children:
                child.lockTransform(event, center, recursive)

    @override
    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            center = self.parent.scenePos() if self.parent else None
            recursive = self.isMovementRecursive()
            self.lockTransform(event, center, recursive)
        super().mousePressEvent(event)

    @override
    def mouseMoveEvent(self, event):
        if self.isMovementRotational():
            return self.moveRotationally(event)
        return self.moveOrthogonally(event)

    def moveOrthogonally(self, event):
        epos = event.scenePos()
        diff = epos - self.locked_event_pos
        self.setPos(self.locked_pos + diff)

        if self.isMovementRecursive():
            for child in self.children:
                child.moveOrthogonally(event)

    def moveRotationally(self, event):
        epos = event.scenePos()
        line = QtCore.QLineF(self.locked_center, epos)
        angle =  self.locked_angle - line.angle()
        center = self.locked_center

        transform = QtGui.QTransform()
        transform.translate(center.x(), center.y())
        transform.rotate(angle)
        transform.translate(-center.x(), -center.y())

        recursive = self.isMovementRecursive()
        self.applyTransform(transform, recursive)

    def applyTransform(self, transform, recursive=False):
        pos = transform.map(self.locked_pos)
        self.setPos(pos)

        if recursive:
            for child in self.children:
                child.applyTransform(transform, recursive)


class NodeNew(VertexNew):
    def __init__(self, x, y, r, text, weights):
        super().__init__(x, y, r)
        self.weights = weights
        self.pies = dict()
        self.text = text

        font = QtGui.QFont()
        font.setPixelSize(16)
        font.setFamily('Arial')
        self.font = font

        self.label = LabelNew(text, self)

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
