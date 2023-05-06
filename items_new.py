from math import degrees, atan2

from PySide6 import QtWidgets
from PySide6 import QtGui
from PySide6 import QtCore


class VertexNew(QtWidgets.QGraphicsEllipseItem):
    def __init__(self, x, y, r=2.5):
        super().__init__(-r, -r, r * 2, r * 2)
        self.setAcceptHoverEvents(True)
        self.setFlag(QtWidgets.QGraphicsItem.ItemIsMovable, True)
        self.setFlag(QtWidgets.QGraphicsItem.ItemSendsGeometryChanges, True)
        self.setPen(QtGui.QPen(QtCore.Qt.black, 2))
        self.setBrush(self.pen().color())
        self.setPos(x, y)

        self.parent = None
        self.children = set()
        self.siblings = set()
        self.edges = dict()

        self._rotational_setting = None
        self._highlight_color = QtCore.Qt.magenta

        self.radius = r
        self.locked_distance = None
        self.locked_rotation = None
        self.locked_angle = None
        self.locked_transform = None
        self.state_hovered = False
        self.state_pressed = False

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

    # def addChild(self, item, segments=1):
    #     self.edges[item] = Edge(self, self, item, segments)
    #     item.setParentItem(self)
    #     self.adjustItemEdge(item)

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
            try:
                for edge in self.edges.values():
                    edge.adjustPosition()
            except AttributeError:
                pass
            # if isinstance(parent, VertexNew):
            #     parent.adjustItemEdge(self)
            # elif isinstance(parent, Block):
            #     parent.adjustItemEdges(self)
        return super().itemChange(change, value)

    # def adjustItemEdge(self, item):
    #     edge = self.edges[item]
    #     edge.adjustPosition()

    # def lockTransform(self, event):
    #     line = QtCore.QLineF(0, 0, self.pos().x(), self.pos().y())
    #     self.locked_distance = line.length()
    #     self.locked_rotation = self.rotation()
    #     self.locked_angle = line.angle()
    #
    #     clicked_pos = self.mapToParent(event.pos())
    #     eline = QtCore.QLineF(0, 0, clicked_pos.x(), clicked_pos.y())
    #     transform = QtGui.QTransform()
    #     transform.rotate(eline.angle() - line.angle())
    #     self.locked_transform = transform

    def set_rotational_setting(self, value):
        self._rotational_setting = value

    def set_highlight_color(self, value):
        self._highlight_color = value

    def isMovementRotational(self):
        return False
        # if not self._rotational_setting:
        #     return False
        # return isinstance(self.parentItem(), VertexNew)

    # def mousePressEvent(self, event):
    #     if event.button() == QtCore.Qt.LeftButton:
    #         self.lockTransform(event)
    #     super().mousePressEvent(event)

    # def mouseMoveEvent(self, event):
    #     epos = self.mapToParent(event.pos())
    #     if not self.isMovementRotational():
    #         self.setPos(epos)
    #         return
    #
    #     line = QtCore.QLineF(0, 0, epos.x(), epos.y())
    #     line.setLength(self.locked_distance)
    #     line = self.locked_transform.map(line)
    #     new_pos = line.p2()
    #     new_angle = self.locked_angle - line.angle()
    #     self.setPos(new_pos)
    #     self.setRotation(self.locked_rotation + new_angle)
