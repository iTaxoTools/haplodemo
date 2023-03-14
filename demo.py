import sys
from dataclasses import dataclass

from PySide6 import QtWidgets
from PySide6 import QtGui
from PySide6 import QtCore
from PySide6 import QtSvg


@dataclass
class Division:
    name: str
    color: str

    @classmethod
    def colorize_list(cls, names: list[str], colors: list[str]):
        return [cls(names[i], colors[i]) for i in range(len(names))]


class PastelPalette(list):
    colors = [
        '#fbb4ae',
        '#b3cde3',
        '#ccebc5',
        '#decbe4',
        '#fed9a6',
        '#ffffcc',
        '#e5d8bd',
        '#fddaec',
    ]
    default = '#f2f2f2'

    def __init__(self):
        super().__init__(self.colors)

    def __getitem__(self, index):
        if index < len(self):
            return super().__getitem__(index)
        return self.default


class ColorDelegate(QtWidgets.QStyledItemDelegate):
    def __init__(self, parent=None, palette=None):
        super().__init__(parent)
        if not palette:
            return
        for i in range(16):
            QtWidgets.QColorDialog.setCustomColor(i, QtGui.QColor(palette[i]))

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


class DivisionListModel(QtCore.QAbstractListModel):
    def __init__(self, divisions, parent=None):
        super().__init__(parent)
        self._divisions = divisions

    def rowCount(self, parent=QtCore.QModelIndex()):
        return len(self._divisions)

    def data(self, index, role=QtCore.Qt.DisplayRole):
        if not index.isValid() or not (0 <= index.row() < self.rowCount()):
            return None

        name = self._divisions[index.row()].name
        color = self._divisions[index.row()].color

        if role == QtCore.Qt.DisplayRole:
            return name
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


class Label(QtWidgets.QGraphicsTextItem):
    def __init__(self, text, parent):
        super().__init__(text, parent)
        # self.setFlag(QtWidgets.QGraphicsItem.ItemIgnoresTransformations, True)
        self.setDefaultTextColor(QtCore.Qt.white)
        self.setAcceptHoverEvents(False)

        font = QtGui.QFont()
        font.setPixelSize(16)
        font.setFamily('Arial')
        self.setFont(font)
        self.adjustSize()

        self.setPos(
            parent.radius - self.boundingRect().width() / 2,
            parent.radius - self.boundingRect().height() / 2)


class Edge(QtWidgets.QGraphicsLineItem):
    def __init__(self, parent, segments=2):
        super().__init__(parent)
        self.setFlag(QtWidgets.QGraphicsItem.ItemStacksBehindParent, True)
        self.setPen(QtGui.QPen(QtCore.Qt.black, 2))
        self.segments = segments

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


class Node(QtWidgets.QGraphicsEllipseItem):
    def __init__(self, x, y, r, text, color=QtCore.Qt.black, divisions=None):
        super().__init__(0, 0, r * 2, r * 2)
        self.setAcceptHoverEvents(True)
        self.setFlag(QtWidgets.QGraphicsItem.ItemIsMovable, True)
        self.setFlag(QtWidgets.QGraphicsItem.ItemSendsGeometryChanges, True)
        self.setBrush(color)
        self.setPen(QtGui.QPen(QtCore.Qt.black, 2))
        self.setPos(x, y)

        self.radius = r
        self.hovered = False
        self.divisions = dict()
        self.items = dict()

        self.textItem = Label(text, self)

        if divisions:
            self.setDivisions(divisions)

    def paint(self, painter, options, widget = None):
        painter.save()
        painter.setPen(self.pen() if not self.hovered else QtGui.QPen(QtGui.QColor('#8aef52'), 4))
        painter.setBrush(self.brush())
        painter.drawEllipse(self.rect())
        if self.divisions:
            self.paintDivisions(painter)
        painter.restore()

    def paintDivisions(self, painter):
        painter.setPen(QtCore.Qt.NoPen)
        total_weight = sum(weight for weight in self.divisions.values())
        starting_angle = 16 * 90

        items = iter(self.divisions.items())
        next(items)
        for color, weight in items:
            span = int(5760 * weight / total_weight)
            painter.setBrush(QtGui.QBrush(color))
            painter.drawPie(self.rect(), starting_angle, span)
            starting_angle += span

        painter.setBrush(QtCore.Qt.NoBrush)
        painter.setPen(self.pen() if not self.hovered else QtGui.QPen(QtGui.QColor('#8aef52'), 4))
        painter.drawEllipse(self.rect())

    def addChild(self, item, segments=1):
        self.items[item] = Edge(self, segments)
        item.setParentItem(self)
        self.adjustItemEdge(item)

    def setDivisions(self, divisions):
        self.divisions = divisions
        color = next(iter(divisions.keys()))
        self.setBrush(QtGui.QBrush(color))

    def boundingRect(self):
        # Hack to prevent drag n draw glitch
        return self.rect().adjusted(-50, -50, 50, 50)

    def itemChange(self, change, value):
        parent = self.parentItem()
        if isinstance(parent, Node):
            if change == QtWidgets.QGraphicsItem.ItemPositionHasChanged:
                parent.adjustItemEdge(self)
        return super().itemChange(change, value)

    def adjustItemEdge(self, item):
        edge = self.items[item]

        line = QtCore.QLineF(
            self.radius,
            self.radius,
            item.pos().x() + item.radius,
            item.pos().y() + item.radius)
        length = line.length()

        if length < (self.radius + item.radius):
            edge.hide()
            return
        edge.show()

        line.setLength(length - self.radius - item.radius)

        unit = line.unitVector()
        unit.setLength(self.radius)
        unit.translate(-unit.x1(), -unit.y1())

        line.translate(unit.x2(), unit.y2())
        edge.setLine(line)


class Scene(QtWidgets.QGraphicsScene):
    itemMoved = QtCore.Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._division_model = None
        self._hoveredItem = None

    def setDivisionModel(self, model):
        self._division_model = model

    def addNodes(self):
        self.node1 = Node(85, 140, 35, 'A', divisions={'#20639b': 4, '#ed553b': 3, '#3caea3': 2})
        self.addItem(self.node1)

        self.node2 = Node(95, -30, 20, 'B', divisions={'#20639b': 4, '#3caea3': 2})
        self.node1.addChild(self.node2, 2)

        self.node3 = Node(115, 60, 25, 'C', divisions={'#ed553b': 6, '#3caea3': 2})
        self.node1.addChild(self.node3, 3)

        self.node4 = Node(60, -30, 15, 'D', QtGui.QColor('#ed553b'))
        self.node3.addChild(self.node4, 1)

        self.node5 = Node(60, 60, 15, 'E', QtGui.QColor('#3caea3'))
        self.node3.addChild(self.node5, 2)

    def event(self, event):
        if event.type() == QtCore.QEvent.GraphicsSceneMouseMove:
            self.hoverEvent(event)
        return super().event(event)

    def hoverEvent(self, event):
        # This is required, since the default hover implementation
        # sends the event to the parent of the hovered item,
        # which we don't want!
        for item in self.items(event.scenePos()):
            if item == self._hoveredItem:
                return
            if isinstance(item, Node):
                self.setHoveredItem(item)
                return
        self.setHoveredItem(None)

    def setHoveredItem(self, item):
        if self._hoveredItem is not None:
            self._hoveredItem.hovered = False
        self._hoveredItem = item
        if item is not None:
            item.hovered = True
            item.update()


class Window(QtWidgets.QDialog):
    def __init__(self):
        super().__init__()
        self.resize(400, 500)
        self.setWindowTitle('Haplodemo')

        palette = PastelPalette()
        divisions = Division.colorize_list(
            ['Alpha', 'Beta', 'Gamma'], palette
        )

        division_model = DivisionListModel(divisions)

        scene = Scene()
        scene.setDivisionModel(division_model)
        scene.addNodes()

        scene_view = QtWidgets.QGraphicsView()
        scene_view.setRenderHints(QtGui.QPainter.Antialiasing)
        scene_view.setScene(scene)

        division_view = QtWidgets.QListView()
        division_view.setModel(division_model)
        division_view.setItemDelegate(ColorDelegate(self, palette))

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
        layout.addWidget(division_view, 1)
        layout.addLayout(buttons)
        self.setLayout(layout)

        self.scene_view = scene_view

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
