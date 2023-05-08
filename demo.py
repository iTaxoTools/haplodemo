import sys
from dataclasses import dataclass
from collections import defaultdict

from PySide6 import QtWidgets
from PySide6 import QtGui
from PySide6 import QtCore
from PySide6 import QtSvg

from itaxotools.common.bindings import PropertyObject, Property, Binder, Instance
# from itaxotools.common.utility import override

from items import Vertex, Node, Label, Edge, BezierCurve
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
    highlight_color = Property(QtGui.QColor, QtCore.Qt.magenta)
    rotational_movement = Property(bool, True)
    recursive_movement = Property(bool, True)
    label_movement = Property(bool, False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.binder = Binder()
        self.binder.bind(self.properties.palette, self.divisions.set_palette)
        self.binder.bind(self.properties.palette, self.properties.highlight_color, lambda x: x.highlight)


class Scene(QtWidgets.QGraphicsScene):
    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.hovered_item = None
        self.pressed_item = None
        self.lighlighted_edge = None
        self.binder = Binder()

    def addBezier(self):
        item = BezierCurve(QtCore.QPointF(0, 0), QtCore.QPointF(200, 0))
        self.addItem(item)
        item.setPos(60, 160)

    def addNodes(self):
        node1 = self.create_node(85, 140, 35, 'Alphanumerical', {'X': 4, 'Y': 3, 'Z': 2})
        self.addItem(node1)

        node2 = self.create_node(node1.pos().x() + 95, node1.pos().y() - 30, 20, 'Beta', {'X': 4, 'Z': 2})
        self.add_child(node1, node2, 2)

        node3 = self.create_node(node1.pos().x() + 115, node1.pos().y() + 60, 25, 'C', {'Y': 6, 'Z': 2})
        self.add_child(node1, node3, 3)

        node4 = self.create_node(node3.pos().x() + 60, node3.pos().y() - 30, 15, 'D', {'Y': 1})
        self.add_child(node3, node4, 1)

        vertex1 = self.create_vertex(node3.pos().x() - 60, node3.pos().y() + 60)
        self.add_child(node3, vertex1, 2)

        node5 = self.create_node(vertex1.pos().x() - 80, vertex1.pos().y() + 40, 30, 'Error', {'?': 1})
        self.add_child(vertex1, node5, 4)

        node6 = self.create_node(vertex1.pos().x() + 60, vertex1.pos().y() + 20, 15, 'R', {'Z': 1})
        self.add_child(vertex1, node6, 1)

        node7 = self.create_node(vertex1.pos().x() + 100, vertex1.pos().y() + 80, 15, 'S', {'Z': 1})
        self.add_sibling(node6, node7, 2)

        node8 = self.create_node(vertex1.pos().x() + 20, vertex1.pos().y() + 80, 15, 'T', {'Y': 1})
        self.add_sibling(node6, node8, 1)
        self.add_sibling(node7, node8, 1)

        node9 = self.create_node(node7.pos().x() + 20, node7.pos().y() - 40, 10, 'x', {'Z': 1})
        self.add_child(node7, node9, 1)

    def addManyNodes(self, dx, dy):
        for x in range(dx):
            nodex = self.create_node(20, 80 * x, 15, f'x{x}', {'X': 1})
            self.addItem(nodex)

            for y in range(dy):
                nodey = self.create_node(nodex.pos().x() + 80 + 40 * y, nodex.pos().y() + 40, 15, f'y{y}', {'Y': 1})
                self.add_child(nodex, nodey)

    def create_vertex(self, *args, **kwargs):
        item = Vertex(*args, **kwargs)
        self.binder.bind(self.settings.properties.rotational_movement, item.set_rotational_setting)
        self.binder.bind(self.settings.properties.recursive_movement, item.set_recursive_setting)
        self.binder.bind(self.settings.properties.highlight_color, item.set_highlight_color)
        return item

    def create_node(self, *args, **kwargs):
        item = Node(*args, **kwargs)
        self.binder.bind(self.settings.divisions.colorMapChanged, item.update_colors)
        self.binder.bind(self.settings.properties.rotational_movement, item.set_rotational_setting)
        self.binder.bind(self.settings.properties.recursive_movement, item.set_recursive_setting)
        self.binder.bind(self.settings.properties.label_movement, item.label.set_locked, lambda x: not x)
        self.binder.bind(self.settings.properties.highlight_color, item.label.set_highlight_color)
        self.binder.bind(self.settings.properties.highlight_color, item.set_highlight_color)
        return item

    def create_edge(self, *args, **kwargs):
        item = Edge(*args, **kwargs)
        self.binder.bind(self.settings.properties.highlight_color, item.set_highlight_color)
        return item

    def add_child(self, parent, child, segments=1):
        edge = self.create_edge(parent, child, segments)
        parent.addChild(child, edge)
        self.addItem(edge)
        self.addItem(child)

    def add_sibling(self, vertex, sibling, segments=1):
        edge = self.create_edge(vertex, sibling, segments)
        vertex.addSibling(sibling, edge)
        self.addItem(edge)

        if not sibling.scene():
            self.addItem(sibling)

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
        if self.pressed_item is None:
            edge = self.get_item_edge(item)
            self.set_highlighted_edge(edge)

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
        edge = self.get_item_edge(item)
        self.set_highlighted_edge(edge)

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

    def get_item_edge(self, item):
        if item is None:
            return None
        if isinstance(item, Label):
            item = item.parentItem()
        if isinstance(item.parentItem(), Vertex):
            return item.parentItem().edges[item]
        return None

    def set_highlighted_edge(self, edge):
        if self.lighlighted_edge is not None:
            self._set_highlighted_edge_state(False)
        self.lighlighted_edge = edge
        if edge is not None:
            self._set_highlighted_edge_state(True)

    def _set_highlighted_edge_state(self, state: bool):
        edge = self.lighlighted_edge
        edge.state_highlighted = state
        edge.update()


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


class ToggleButton(QtWidgets.QPushButton):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setCheckable(True)
        self.checkmark = QtGui.QPolygon([
            QtCore.QPoint(-3, 0),
            QtCore.QPoint(-2, 3),
            QtCore.QPoint(5, -5)])

    def paintEvent(self, event):
        super().paintEvent(event)
        if not self.isChecked():
            return

        m = QtGui.QFontMetrics(self.font())
        w = self.width() - m.boundingRect(self.text()).width()
        w = w / 2 - 14
        h = self.height() / 2 + 1

        painter = QtGui.QPainter(self)
        painter.translate(w, h)
        painter.setPen(QtGui.QPen(QtGui.QColor('#333'), 1.5))
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        painter.drawPolyline(self.checkmark)
        painter.end()


class Window(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(QtCore.Qt.Window)
        self.resize(400, 500)
        self.setWindowTitle('Haplodemo')

        settings = Settings()
        settings.divisions.set_divisions_from_keys(['X', 'Y', 'Z'])

        scene = Scene(settings)
        # scene.addManyNodes(8, 32)
        # scene.addBezier()
        scene.addNodes()

        scene_view = QtWidgets.QGraphicsView()
        scene_view.setRenderHints(QtGui.QPainter.Antialiasing)
        # This just makes things worse when moving text around:
        # scene_view.setRenderHints( QtGui.QPainter.TextAntialiasing)
        scene_view.setScene(scene)

        palette_selector = PaletteSelector()

        toggle_rotation = ToggleButton('Rotate nodes')
        toggle_recursive = ToggleButton('Move children')
        toggle_labels = ToggleButton('Unlock labels')

        division_view = QtWidgets.QListView()
        division_view.setModel(settings.divisions)
        division_view.setItemDelegate(ColorDelegate(self))

        button_svg = QtWidgets.QPushButton('Export as SVG')
        button_svg.clicked.connect(lambda: self.export_svg())

        button_pdf = QtWidgets.QPushButton('Export as PDF')
        button_pdf.clicked.connect(lambda: self.export_pdf())

        button_png = QtWidgets.QPushButton('Export as PNG')
        button_png.clicked.connect(lambda: self.export_png())

        options = QtWidgets.QGridLayout()
        options.addWidget(toggle_rotation, 0, 0)
        options.addWidget(toggle_recursive, 0, 1)
        options.addWidget(toggle_labels, 1, 0, 1, 2)

        buttons = QtWidgets.QHBoxLayout()
        buttons.addWidget(button_svg)
        buttons.addWidget(button_pdf)
        buttons.addWidget(button_png)

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(scene_view, 10)
        layout.addWidget(palette_selector)
        layout.addWidget(division_view, 1)
        layout.addLayout(options)
        layout.addLayout(buttons)
        self.setLayout(layout)

        self.scene_view = scene_view

        self.binder = Binder()

        self.binder.bind(palette_selector.currentValueChanged, settings.properties.palette)
        self.binder.bind(settings.properties.palette, palette_selector.setValue)
        self.binder.bind(settings.properties.palette, ColorDelegate.setCustomColors)

        self.binder.bind(settings.properties.rotational_movement, toggle_rotation.setChecked)
        self.binder.bind(toggle_rotation.toggled, settings.properties.rotational_movement)

        self.binder.bind(settings.properties.recursive_movement, toggle_recursive.setChecked)
        self.binder.bind(toggle_recursive.toggled, settings.properties.recursive_movement)

        self.binder.bind(settings.properties.label_movement, toggle_labels.setChecked)
        self.binder.bind(toggle_labels.toggled, settings.properties.label_movement)

        action = QtGui.QAction()
        action.setShortcut(QtGui.QKeySequence.Save)
        action.triggered.connect(self.quick_save)
        self.quick_save_action = action
        self.addAction(action)

    def quick_save(self):
        self.export_svg('graph.svg')
        self.export_pdf('graph.pdf')
        self.export_png('graph.png')

    def export_svg(self, file=None):
        if file is None:
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

    def export_pdf(self, file=None):
        if file is None:
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

    def export_png(self, file=None):
        if file is None:
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
