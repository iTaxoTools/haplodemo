import sys
from dataclasses import dataclass
from collections import defaultdict
from math import degrees, atan2

from PySide6 import QtWidgets
from PySide6 import QtGui
from PySide6 import QtCore
from PySide6 import QtSvg

from itaxotools.common.bindings import PropertyObject, Property, Binder, Instance
# from itaxotools.common.utility import override

from palettes import Palette


@dataclass
class Division:
    key: str
    color: str


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
    colorMapChanged = QtCore.Signal(object)

    def __init__(self, names=[], palette=Palette.Spring(), parent=None):
        super().__init__(parent)
        self._palette = palette
        self._default_color = palette.default
        self._divisions = list()
        self.set_divisions_from_keys(names)
        self.set_palette(palette)

        self.dataChanged.connect(self.handle_data_changed)
        self.modelReset.connect(self.handle_data_changed)

    def set_divisions_from_keys(self, keys):
        self.beginResetModel()
        palette = self._palette
        self._divisions = [Division(keys[i], palette[i]) for i in range(len(keys))]
        self.endResetModel()

    def set_palette(self, palette):
        self.beginResetModel()
        self._default_color = palette.default
        for index, division in enumerate(self._divisions):
            division.color = palette[index]
        self.endResetModel()

    def get_color_map(self):
        map = {d.key: d.color for d in self._divisions}
        return defaultdict(lambda: self._default_color, map)

    def handle_data_changed(self, *args, **kwargs):
        self.colorMapChanged.emit(self.get_color_map())

    def rowCount(self, parent=QtCore.QModelIndex()):
        return len(self._divisions)

    def data(self, index, role=QtCore.Qt.DisplayRole):
        if not index.isValid() or not (0 <= index.row() < self.rowCount()):
            return None

        key = self._divisions[index.row()].key
        color = self._divisions[index.row()].color

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

            self._divisions[index.row()].color = color
            self.dataChanged.emit(index, index)
            return True

        return False

    def flags(self, index):
        return QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable


class Settings(PropertyObject):
    palette = Property(Palette, Palette.Spring())
    divisions = Property(DivisionListModel, Instance)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.binder = Binder()
        self.binder.bind(self.properties.palette, self.divisions.set_palette)


class Label(QtWidgets.QGraphicsItem):
    def __init__(self, text, parent):
        super().__init__(parent)
        self.setFlag(QtWidgets.QGraphicsItem.ItemIsMovable, True)
        self.setFlag(QtWidgets.QGraphicsItem.ItemSendsGeometryChanges, True)

        # This one option would be very convenient, but bugs out PDF export...
        # self.setFlag(QtWidgets.QGraphicsItem.ItemIgnoresTransformations, True)

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

    def paint(self, painter, options, widget = None):
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
        color = QtGui.QColor('#8aef52')
        pen = QtGui.QPen(color, 3, QtCore.Qt.SolidLine, QtCore.Qt.RoundCap, QtCore.Qt.RoundJoin)
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
        self.locked_distance = None
        self.locked_rotation = None
        self.locked_angle = None
        self.locked_transform = None
        self.state_hovered = False
        self.state_pressed = False
        self.items = dict()

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

    def isMovementRotational(self):
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

    def paint(self, painter, options, widget = None):
        self.paint_node(painter)
        self.paint_pies(painter)
        # self.paint_text(painter)

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

    def paint_text(self, painter):
        #deprecated, to be removed
        painter.save()

        t = self.sceneTransform()
        angle = atan2(t.m12(), t.m11())
        painter.rotate(-degrees(angle))

        painter.setFont(self.font)

        r = self.radius
        rect = QtCore.QRect(-r, -r, 2 * r, 2 * r)
        painter.drawText(rect, QtCore.Qt.AlignCenter, self.text)
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

    def paint(self, painter, options, widget = None):
        pass


class Scene(QtWidgets.QGraphicsScene):
    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.hovered_item = None
        self.pressed_item = None
        self.binder = Binder()

    def addNodes(self):
        self.node1 = self.create_node(85, 140, 35, 'Alphanumerical', {'X': 4, 'Y': 3, 'Z': 2})
        self.addItem(self.node1)

        self.node2 = self.create_node(95, -30, 20, 'Beta', {'X': 4, 'Z': 2})
        self.node1.addChild(self.node2, 2)

        self.node3 = self.create_node(115, 60, 25, 'C', {'Y': 6, 'Z': 2})
        self.node1.addChild(self.node3, 3)

        self.node4 = self.create_node(60, -30, 15, 'D', {'Y': 1})
        self.node3.addChild(self.node4, 1)

        self.vertex1 = self.create_vertex(-60, 60)
        self.node3.addChild(self.vertex1, 2)

        self.node5 = self.create_node(-80, 40, 30, 'Error', {'?': 1})
        self.vertex1.addChild(self.node5, 4)

        self.block1 = self.create_block(self.vertex1)

        self.node6 = self.create_node(60, 20, 15, 'R', {'Z': 1})
        self.block1.setMainNode(self.node6)

        self.node7 = self.create_node(100, 80, 15, 'S', {'Z': 1})
        self.block1.addNode(self.node7)
        self.block1.addEdge(self.node7, self.node6, 2)

        self.node8 = self.create_node(20, 80, 15, 'T', {'Y': 1})
        self.block1.addNode(self.node8)
        self.block1.addEdge(self.node8, self.node6)
        self.block1.addEdge(self.node8, self.node7)

        self.node9 = self.create_node(20, -40, 10, 'x', {'Z': 1})
        self.node7.addChild(self.node9)

    def addManyNodes(self, dx, dy):
        block = Block(None)
        self.addItem(block)
        for x in range(dx):
            nodex = self.create_node(20, 80 * x, 15, f'x{x}', {'X': 1})
            block.addNode(nodex)

            for y in range(dy):
                nodey = self.create_node(80 + 40 * y, 40, 15, f'y{y}', {'Y': 1})
                nodex.addChild(nodey)

    def create_node(self, *args, **kwargs):
        node = Node(*args, **kwargs)
        self.binder.bind(self.settings.divisions.colorMapChanged, node.update_colors)
        return node

    def create_vertex(self, *args, **kwargs):
        return Vertex(*args, **kwargs)

    def create_block(self, *args, **kwargs):
        return Block(*args, **kwargs)

    def event(self, event):
        if event.type() == QtCore.QEvent.GraphicsSceneMouseMove:
            self.customHoverEvent(event)
        if event.type() == QtCore.QEvent.GraphicsSceneLeave:
            self.mouseLeaveEvent(event)
        return super().event(event)

    def mouseLeaveEvent(self, event):
        self.set_hovered_item(None)

    def customHoverEvent(self, event):
        # This is required, since the default hover implementation
        # sends the event to the parent of the hovered item,
        # which we don't want!
        for item in self.items(event.scenePos()):
            if item == self.hovered_item:
                return
            if isinstance(item, Vertex) or isinstance(item, Label):
                self.set_hovered_item(item)
                return
        self.set_hovered_item(None)

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        if event.button() != QtCore.Qt.LeftButton:
            return
        for item in self.items(event.scenePos()):
            if isinstance(item, Vertex) or isinstance(item, Label):
                self.set_pressed_item(item)
                return

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        if event.button() == QtCore.Qt.LeftButton:
            self.set_pressed_item(None)

    def set_hovered_item(self, item):
        if self.hovered_item is not None:
            self._set_hovered_item_state(False)
        self.hovered_item = item
        if item is not None:
            self._set_hovered_item_state(True)

    def _set_hovered_item_state(self, state: bool):
        item = self.hovered_item
        if isinstance(item, Label):
            item.parentItem().state_hovered = state
            item.parentItem().update()
        if isinstance(item, Node):
            item.label.state_hovered = state
            item.label.update()
        item.state_hovered = state
        item.update()

    def set_pressed_item(self, item):
        if self.pressed_item is not None:
            self._set_pressed_item_state(False)
        self.pressed_item = item
        if item is not None:
            self._set_pressed_item_state(True)

    def _set_pressed_item_state(self, state: bool):
        item = self.pressed_item
        if isinstance(item, Label):
            item.parentItem().state_pressed = state
            item.parentItem().update()
        if isinstance(item, Node):
            item.label.state_pressed = state
            item.label.update()
        item.state_pressed = state
        item.update()


class PaletteSelector(QtWidgets.QComboBox):
    currentValueChanged = QtCore.Signal(Palette)

    def __init__(self):
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
        self.setWindowFlags(QtCore.Qt.Window)
        self.resize(400, 500)
        self.setWindowTitle('Haplodemo')

        settings = Settings()
        settings.divisions.set_divisions_from_keys(['X', 'Y', 'Z'])

        scene = Scene(settings)
        # scene.addManyNodes(8, 32)
        scene.addNodes()

        scene_view = QtWidgets.QGraphicsView()
        scene_view.setRenderHints(QtGui.QPainter.Antialiasing)
        # This just makes things worse when moving text around:
        # scene_view.setRenderHints( QtGui.QPainter.TextAntialiasing)
        scene_view.setScene(scene)

        palette_selector = PaletteSelector()

        division_view = QtWidgets.QListView()
        division_view.setModel(settings.divisions)
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
