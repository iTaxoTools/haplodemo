import sys
from dataclasses import dataclass
from math import degrees, atan2

from PySide6 import QtWidgets
from PySide6 import QtGui
from PySide6 import QtCore
from PySide6 import QtSvg

from itaxotools.common.bindings import PropertyObject, Property, Binder

from palettes import Palette


class Settings(PropertyObject):
    palette = Property(Palette, Palette.Spring())


@dataclass
class Division:
    key: str
    color: str

    @classmethod
    def colorize_list(cls, names: list[str], colors: Palette):
        return [cls(names[i], colors[i]) for i in range(len(names))]


class ColorDelegate(QtWidgets.QStyledItemDelegate):
    def paint(self, painter, option, index):
        super().paint(painter, option, index)

        # Draw the decoration icon on top of the background
        decoration_rect = QtCore.QRect(option.rect.x() + 2, option.rect.y() + 2, 16, option.rect.height() - 4)
        icon = index.data(QtCore.Qt.DecorationRole)
        if icon and not icon.isNull():
            icon.paint(painter, decoration_rect)

    def createEditor(self, parent, option, index):
        editor = QtWidgets.QColorDialog(parent=parent)
        editor.setOption(QtWidgets.QColorDialog.DontUseNativeDialog, True)
        return editor

    def setEditorData(self, editor, index):
        color = index.model().data(index, QtCore.Qt.EditRole)
        editor.setCurrentColor(QtGui.QColor(color))

    def setModelData(self, editor, model, index):
        model.setData(index, editor.currentColor().name(), QtCore.Qt.EditRole)

    def updateEditorGeometry(self, editor, option, index):
        # Override required for centering the dialog
        pass

    @staticmethod
    def setCustomColors(palette):
        for i in range(16):
            QtWidgets.QColorDialog.setCustomColor(i, QtGui.QColor(palette[i]))


class DivisionListModel(QtCore.QAbstractListModel):
    def __init__(self, names, palette, parent=None):
        super().__init__(parent)
        self._colors = list()
        self._names = names
        self.colorize(palette)

    def colorize(self, palette):
        self._colors = Division.colorize_list(self._names, palette)
        self._key_map = {division.key: index for index, division in enumerate(self._colors)}
        self.dataChanged.emit(self.createIndex(0, 0), self.createIndex(len(self._colors), 0))

    def getKeyColor(self, key):
        index = self._key_map[key]
        return self._colors[index].color

    def rowCount(self, parent=QtCore.QModelIndex()):
        return len(self._colors)

    def data(self, index, role=QtCore.Qt.DisplayRole):
        if not index.isValid() or not (0 <= index.row() < self.rowCount()):
            return None

        key = self._colors[index.row()].key
        color = self._colors[index.row()].color

        if role == QtCore.Qt.DisplayRole:
            return key
        elif role == QtCore.Qt.EditRole:
            return color
        elif role == QtCore.Qt.DecorationRole:
            color = QtGui.QColor(color)
            pixmap = QtGui.QPixmap(16, 16)
            pixmap.fill(color)
            return QtGui.QIcon(pixmap)

        return None

    def setData(self, index, value, role=QtCore.Qt.EditRole):
        if not index.isValid() or not (0 <= index.row() < self.rowCount()):
            return False

        if role == QtCore.Qt.EditRole:
            color = value.strip()
            if not color.startswith('#'):
                color = '#' + color

            if not QtGui.QColor.isValidColor(color):
                return False

            self._colors[index.row()].color = color
            self.dataChanged.emit(index, index)
            return True

        return False

    def flags(self, index):
        return QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable


class Label(QtWidgets.QGraphicsItem):
    def __init__(self, text, parent):
        super().__init__(parent)
        self.setFlag(QtWidgets.QGraphicsItem.ItemIsMovable, True)

        # This one option would be very convenient, but bugs out PDF export...
        # self.setFlag(QtWidgets.QGraphicsItem.ItemIgnoresTransformations, True)

        font = QtGui.QFont()
        font.setPixelSize(16)
        font.setFamily('Arial')
        self.font = font

        self.text = text
        rect = QtGui.QFontMetrics(font).boundingRect(text)
        rect = rect.translated(-rect.center())
        self.rect = rect.adjusted(-2, -2, 2, 2)

        self.locked_rect = self.rect
        self.locked_pos = QtCore.QPointF(0, 0)

    def boundingRect(self):
        t = self.sceneTransform()
        angle = atan2(t.m12(), t.m11())
        t2 = QtGui.QTransform()
        t2.rotate(-degrees(angle))
        return t2.mapRect(self.rect)

    def paint(self, painter, options, widget = None):
        painter.save()

        t = self.sceneTransform()
        angle = atan2(t.m12(), t.m11())
        painter.rotate(-degrees(angle))

        painter.setFont(self.font)
        painter.drawText(self.rect, QtCore.Qt.AlignCenter, self.text)
        # painter.drawRect(self.rect)

        painter.restore()

    def shape(self):
        path = QtGui.QPainterPath()
        path.addRect(self.boundingRect())
        return path

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


class Edge(QtWidgets.QGraphicsLineItem):
    def __init__(self, parent, node1, node2, segments=2):
        super().__init__(parent)
        self.setFlag(QtWidgets.QGraphicsItem.ItemStacksBehindParent, True)
        self.setPen(QtGui.QPen(QtCore.Qt.black, 2))
        self.setZValue(-1)
        self.segments = segments
        self.node1 = node1
        self.node2 = node2

    def paint(self, painter, options, widget = None):
        super().paint(painter, options, widget)

        if self.segments < 2:
            return

        painter.save()
        painter.setPen(self.pen())
        painter.setBrush(self.pen().color())

        for dot in range(1, self.segments):
            center = self.line().pointAt(dot/self.segments)
            painter.drawEllipse(center, 2.5, 2.5)

        painter.restore()

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

        self.radius = r
        self.locked_distance = 0
        self.locked_rotation = 0
        self.locked_angle = 0
        self.state_hovered = False
        self.state_pressed = False
        self.items = dict()

        self.lockTransform()

    def paint(self, painter, options, widget = None):
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
            return QtGui.QPen(QtGui.QColor('#8aef52'), 4)
        return self.pen()

    def addChild(self, item, segments=1):
        self.items[item] = Edge(self, self, item, segments)
        item.setParentItem(self)
        self.adjustItemEdge(item)

    def boundingRect(self):
        # Hack to prevent drag n draw glitch
        return self.rect().adjusted(-50, -50, 50, 50)

    def itemChange(self, change, value):
        parent = self.parentItem()
        if change == QtWidgets.QGraphicsItem.ItemPositionHasChanged:
            if isinstance(parent, Vertex):
                parent.adjustItemEdge(self)
            elif isinstance(parent, Block):
                parent.adjustItemEdges(self)
        return super().itemChange(change, value)

    def adjustItemEdge(self, item):
        edge = self.items[item]
        edge.adjustPosition()

    def lockTransform(self):
        line = QtCore.QLineF(0, 0, self.pos().x(), self.pos().y())
        self.locked_distance = line.length()
        self.locked_angle = line.angle()
        self.locked_rotation = self.rotation()

    def isMovementRotational(self):
        return isinstance(self.parentItem(), Vertex)

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self.lockTransform()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        epos = self.mapToParent(event.pos())
        if not self.isMovementRotational():
            self.setPos(epos)
            return

        line = QtCore.QLineF(0, 0, epos.x(), epos.y())
        line.setLength(self.locked_distance)
        new_pos = line.p2()
        new_angle = self.locked_angle - line.angle()
        self.setPos(new_pos)
        self.setRotation(self.locked_rotation + new_angle)


class Node(Vertex):
    def __init__(self, x, y, r, text, weights, divisions):
        super().__init__(x, y, r)
        self.divisions = divisions
        self.weights = weights
        self.pies = dict()
        self.text = text

        font = QtGui.QFont()
        font.setPixelSize(16)
        font.setFamily('Arial')
        self.font = font

        self.label = Label(text, self)

        self.updateColors()

    def updateColors(self):
        total_weight = sum(weight for weight in self.weights.values())

        weight_items = iter(self.weights.items())
        first_key, _ = next(weight_items)
        first_color = self.divisions.getKeyColor(first_key)
        self.setBrush(QtGui.QBrush(first_color))

        self.pies = dict()
        for key, weight in weight_items:
            color = self.divisions.getKeyColor(key)
            span = int(5760 * weight / total_weight)
            self.pies[color] = span

    def paint(self, painter, options, widget = None):
        self.paintNode(painter)
        self.paintPies(painter)
        # self.paintText(painter)

    def paintNode(self, painter):
        painter.save()
        if self.pies:
            painter.setPen(QtCore.Qt.NoPen)
        else:
            painter.setPen(self.getBorderPen())
        painter.setBrush(self.brush())
        painter.drawEllipse(self.rect())
        painter.restore()

    def paintPies(self, painter):
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

    def paintText(self, painter):
        painter.save()

        t = self.sceneTransform()
        angle = atan2(t.m12(), t.m11())
        painter.rotate(-degrees(angle))

        painter.setFont(self.font)

        r = self.radius
        rect = QtCore.QRect(-r, -r, 2 * r, 2 * r)
        painter.drawText(rect, QtCore.Qt.AlignCenter, self.text)
        painter.restore()


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

    def paint(self, painter, options, widget = None):
        pass


class Scene(QtWidgets.QGraphicsScene):
    itemMoved = QtCore.Signal()
    divisionDataChanged = QtCore.Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.division_model = None
        self.hovered_item = None
        self.pressed_item = None

    def setDivisionModel(self, model):
        if self.division_model is not None:
            self.division_model.dataChanged.disconnect(self.divisionDataChanged)
        model.dataChanged.connect(self.divisionDataChanged)
        self.division_model = model

    def addNodes(self):
        self.node1 = Node(85, 140, 35, 'Alpha', {'X': 4, 'Y': 3, 'Z': 2}, self.division_model)
        self.addItem(self.node1)

        self.node2 = Node(95, -30, 20, 'Beta', {'X': 4, 'Z': 2}, self.division_model)
        self.node1.addChild(self.node2, 2)

        self.node3 = Node(115, 60, 25, 'C', {'Y': 6, 'Z': 2}, self.division_model)
        self.node1.addChild(self.node3, 3)

        self.node4 = Node(60, -30, 15, 'D', {'Y': 1}, self.division_model)
        self.node3.addChild(self.node4, 1)

        self.vertex1 = Vertex(-60, 60)
        self.node3.addChild(self.vertex1, 2)

        self.node5 = Node(-80, 40, 30, 'E', {'X': 1}, self.division_model)
        self.vertex1.addChild(self.node5, 4)

        self.block1 = Block(self.vertex1)

        self.node6 = Node(60, 20, 15, 'R', {'Z': 1}, self.division_model)
        self.block1.setMainNode(self.node6)

        self.node7 = Node(100, 80, 15, 'S', {'Z': 1}, self.division_model)
        self.block1.addNode(self.node7)
        self.block1.addEdge(self.node7, self.node6, 2)

        self.node8 = Node(20, 80, 15, 'T', {'Y': 1}, self.division_model)
        self.block1.addNode(self.node8)
        self.block1.addEdge(self.node8, self.node6)
        self.block1.addEdge(self.node8, self.node7)

        self.node9 = Node(20, -40, 10, 'x', {'Z': 1}, self.division_model)
        self.node7.addChild(self.node9)

        self.divisionDataChanged.connect(self.node1.updateColors)
        self.divisionDataChanged.connect(self.node2.updateColors)
        self.divisionDataChanged.connect(self.node3.updateColors)
        self.divisionDataChanged.connect(self.node4.updateColors)
        self.divisionDataChanged.connect(self.node5.updateColors)
        self.divisionDataChanged.connect(self.node6.updateColors)
        self.divisionDataChanged.connect(self.node7.updateColors)
        self.divisionDataChanged.connect(self.node8.updateColors)
        self.divisionDataChanged.connect(self.node9.updateColors)

    def event(self, event):
        if event.type() == QtCore.QEvent.GraphicsSceneMouseMove:
            self.customHoverEvent(event)
        if event.type() == QtCore.QEvent.GraphicsSceneLeave:
            self.mouseLeaveEvent(event)
        return super().event(event)

    def mouseLeaveEvent(self, event):
        self.setHoveredItem(None)

    def customHoverEvent(self, event):
        # This is required, since the default hover implementation
        # sends the event to the parent of the hovered item,
        # which we don't want!
        for item in self.items(event.scenePos()):
            if item == self.hovered_item:
                return
            if isinstance(item, Vertex):
                self.setHoveredItem(item)
                return
        self.setHoveredItem(None)

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        if event.button() != QtCore.Qt.LeftButton:
            return
        for item in self.items(event.scenePos()):
            if isinstance(item, Vertex):
                self.setPressedItem(item)
                return

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        if event.button() == QtCore.Qt.LeftButton:
            self.setPressedItem(None)

    def setHoveredItem(self, item):
        if self.hovered_item is not None:
            self.hovered_item.state_hovered = False
        self.hovered_item = item
        if item is not None:
            item.state_hovered = True
            item.update()

    def setPressedItem(self, item):
        if self.pressed_item is not None:
            self.pressed_item.state_pressed = False
        self.pressed_item = item
        if item is not None:
            item.state_pressed = True
            item.update()


class PaletteSelector(QtWidgets.QComboBox):
    currentValueChanged = QtCore.Signal(Palette)

    def __init__(self, settings):
        super().__init__()
        self._palettes = []
        for palette in Palette:
            self._palettes.append(palette)
            self.addItem(palette.label)
        self.currentIndexChanged.connect(self.handleIndexChanged)

    def handleIndexChanged(self, index):
        self.currentValueChanged.emit(self._palettes[index]())

    def setValue(self, value):
        index = self._palettes.index(value.type)
        self.setCurrentIndex(index)


class Window(QtWidgets.QDialog):
    def __init__(self):
        super().__init__()
        self.resize(400, 500)
        self.setWindowTitle('Haplodemo')

        settings = Settings()
        palette = settings.palette
        divisions = ['X', 'Y', 'Z']

        division_model = DivisionListModel(divisions, palette)

        scene = Scene()
        scene.setDivisionModel(division_model)
        scene.addNodes()

        scene_view = QtWidgets.QGraphicsView()
        scene_view.setRenderHints(QtGui.QPainter.Antialiasing)
        scene_view.setScene(scene)

        palette_selector = PaletteSelector(settings)

        division_view = QtWidgets.QListView()
        division_view.setModel(division_model)
        division_view.setItemDelegate(ColorDelegate(self))

        button_svg = QtWidgets.QPushButton('Export as SVG')
        button_svg.clicked.connect(self.export_svg)

        button_pdf = QtWidgets.QPushButton('Export as PDF')
        button_pdf.clicked.connect(self.export_pdf)

        button_png = QtWidgets.QPushButton('Export as PNG')
        button_png.clicked.connect(self.export_png)

        buttons = QtWidgets.QHBoxLayout()
        buttons.addWidget(button_svg)
        buttons.addWidget(button_pdf)
        buttons.addWidget(button_png)

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(scene_view, 10)
        layout.addWidget(palette_selector)
        layout.addWidget(division_view, 1)
        layout.addLayout(buttons)
        self.setLayout(layout)

        self.scene_view = scene_view

        self.binder = Binder()
        self.binder.bind(palette_selector.currentValueChanged, settings.properties.palette)
        self.binder.bind(settings.properties.palette, palette_selector.setValue)
        self.binder.bind(settings.properties.palette, division_model.colorize)
        self.binder.bind(settings.properties.palette, ColorDelegate.setCustomColors)

    def export_svg(self):
        file, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, 'Export As...', 'graph.svg', 'SVG Files (*.svg)')
        if not file:
            return
        print('SVG >', file)

        generator = QtSvg.QSvgGenerator()
        generator.setFileName(file)
        generator.setSize(QtCore.QSize(200, 200))
        generator.setViewBox(QtCore.QRect(0, 0, 200, 200))

        painter = QtGui.QPainter()
        painter.begin(generator)
        self.scene_view.render(painter)
        painter.end()

    def export_pdf(self):
        file, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, 'Export As...', 'graph.pdf', 'PDF Files (*.pdf)')
        if not file:
            return
        print('PDF >', file)

        writer = QtGui.QPdfWriter(file)

        painter = QtGui.QPainter()
        painter.begin(writer)
        self.scene_view.render(painter)
        painter.end()

    def export_png(self):
        file, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, 'Export As...', 'graph.png', 'PNG Files (*.png)')
        if not file:
            return
        print('PNG >', file)

        width, height = 400, 400
        pixmap = QtGui.QPixmap(width, height)
        pixmap.fill(QtCore.Qt.white)

        painter = QtGui.QPainter()
        painter.begin(pixmap)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        self.scene_view.render(painter)
        painter.end()

        pixmap.save(file)


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    window = Window()
    window.show()

    sys.exit(app.exec())
