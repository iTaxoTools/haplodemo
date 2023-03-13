import sys
from PySide6 import QtWidgets
from PySide6 import QtGui
from PySide6 import QtCore
from PySide6 import QtSvg


class Label(QtWidgets.QGraphicsTextItem):
    def __init__(self, text, parent):
        super().__init__(text, parent)
        # self.setFlag(QtWidgets.QGraphicsItem.ItemIgnoresTransformations, True)
        self.setDefaultTextColor(QtCore.Qt.white)

        font = QtGui.QFont()
        font.setPixelSize(16)
        font.setFamily('Arial')
        self.setFont(font)
        self.adjustSize()

        self.setPos(
            parent.radius / 2 - self.boundingRect().width() / 2,
            parent.radius / 2 - self.boundingRect().height() / 2)


class Edge(QtWidgets.QGraphicsLineItem):
    def __init__(self, parent):
        super().__init__(parent)
        self.setFlag(QtWidgets.QGraphicsItem.ItemStacksBehindParent, True)
        self.setPen(QtGui.QPen(QtCore.Qt.black, 2))


class Node(QtWidgets.QGraphicsEllipseItem):
    def __init__(self, x, y, r, text, brush):
        super().__init__(0, 0, r, r)
        self.setFlag(QtWidgets.QGraphicsItem.ItemIsMovable, True)
        self.setFlag(QtWidgets.QGraphicsItem.ItemSendsGeometryChanges, True)
        self.setBrush(brush)
        self.setPen(QtGui.QPen(QtCore.Qt.black, 2))
        self.setPos(x, y)

        self.items = dict()
        self.radius = r

        self.textItem = Label(text, self)

    def paint(self, painter, options, widget = None):
        painter.save()
        painter.setPen(self.pen())
        painter.setBrush(self.brush())
        center = QtCore.QPointF(self.radius, self.radius)
        painter.drawEllipse(self.rect())
        painter.restore()

    def addItem(self, item):
        self.items[item] = Edge(self)
        item.setParentItem(self)
        self.adjustItemEdge(item)

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
        edge.setLine(
            self.radius / 2,
            self.radius / 2,
            item.pos().x() + item.radius / 2,
            item.pos().y() + item.radius / 2)


class Scene(QtWidgets.QGraphicsScene):
    itemMoved = QtCore.Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

        self.node1 = Node(85, 140, 70, 'A', QtGui.QColor('#20639b'))
        self.addItem(self.node1)

        self.node2 = Node(95, -30, 40, 'B', QtGui.QColor('#3caea3'))
        self.node1.addItem(self.node2)

        self.node3 = Node(115, 60, 50, 'C', QtGui.QColor('#ed553b'))
        self.node1.addItem(self.node3)

        self.node4 = Node(60, -30, 30, 'D', QtGui.QColor('#3caea3'))
        self.node3.addItem(self.node4)

        self.node5 = Node(60, 60, 30, 'E', QtGui.QColor('#3caea3'))
        self.node3.addItem(self.node5)


class Window(QtWidgets.QDialog):
    def __init__(self):
        super().__init__()
        self.resize(400, 400)
        self.setWindowTitle('Haplodemo')

        view = QtWidgets.QGraphicsView()
        scene = Scene()
        view.setRenderHints(QtGui.QPainter.Antialiasing)
        view.setScene(scene)

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
        layout.addWidget(view)
        layout.addLayout(buttons)
        self.setLayout(layout)

        self.graph = view

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
        self.graph.render(painter)
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
        self.graph.render(painter)
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
        self.graph.render(painter)
        painter.end()

        pixmap.save(file)


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    window = Window()
    window.show()

    sys.exit(app.exec())
