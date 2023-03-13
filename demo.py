import sys
from PySide6 import QtWidgets
from PySide6 import QtGui
from PySide6 import QtCore
from PySide6 import QtSvg


class EllipseItem(QtWidgets.QGraphicsEllipseItem):
    def __init__(self, x, y, r, text, brush):
        super().__init__(0, 0, r, r)
        self.setFlag(QtWidgets.QGraphicsItem.ItemIsMovable, True)
        self.setFlag(QtWidgets.QGraphicsItem.ItemSendsGeometryChanges, True)
        self.setBrush(brush)
        self.setPos(x, y)

        # Create a QtWidgets.QGraphicsTextItem and set its position to the center of the ellipse
        self.textItem = QtWidgets.QGraphicsTextItem(text, self)
        font = QtGui.QFont()
        font.setPointSize(14)
        self.textItem.setFont(font)
        self.textItem.setDefaultTextColor(QtCore.Qt.white)
        self.textItem.setPos(self.rect().width() / 2 - self.textItem.boundingRect().width() / 2, self.rect().height() / 2 - self.textItem.boundingRect().height() / 2)

    def itemChange(self, change, value):
        if self.scene() is not None:
            if change == QtWidgets.QGraphicsItem.ItemPositionHasChanged:
                # Emit a QtCore.Signal to notify that the item has been moved
                self.scene().itemMoved.emit()
        return super().itemChange(change, value)


class Scene(QtWidgets.QGraphicsScene):
    itemMoved = QtCore.Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.line1 = QtWidgets.QGraphicsLineItem()
        self.line1.setPen(QtGui.QPen(QtCore.Qt.black, 2))
        self.addItem(self.line1)

        self.line2 = QtWidgets.QGraphicsLineItem()
        self.line2.setPen(QtGui.QPen(QtCore.Qt.black, 2))
        self.addItem(self.line2)

        self.ellipse1 = EllipseItem(85, 140, 50, 'A', QtGui.QColor('#20639b'))
        self.addItem(self.ellipse1)

        self.ellipse2 = EllipseItem(200, 200, 50, 'B', QtGui.QColor('#ed553b'))
        self.addItem(self.ellipse2)

        self.ellipse3 = EllipseItem(180, 110, 30, 'C', QtGui.QColor('#3caea3'))
        self.addItem(self.ellipse3)

        # Connect the itemMoved QtCore.Signal to the updateLines slot
        self.itemMoved.connect(self.updateLines)
        self.updateLines()

    def updateLines(self):
        # Get the center points of the ellipses
        center1 = self.ellipse1.scenePos() + QtCore.QPointF(self.ellipse1.rect().width() / 2, self.ellipse1.rect().height() / 2)
        center2 = self.ellipse2.scenePos() + QtCore.QPointF(self.ellipse2.rect().width() / 2, self.ellipse2.rect().height() / 2)
        center3 = self.ellipse3.scenePos() + QtCore.QPointF(self.ellipse3.rect().width() / 2, self.ellipse3.rect().height() / 2)

        # Set the starting and ending points of the line
        self.line1.setLine(center1.x(), center1.y(), center2.x(), center2.y())
        self.line2.setLine(center1.x(), center1.y(), center3.x(), center3.y())

class Window(QtWidgets.QDialog):
    def __init__(self):
        super().__init__()
        self.resize(400, 400)

        view = QtWidgets.QGraphicsView()
        scene = Scene()
        view.setRenderHints(QtGui.QPainter.Antialiasing)
        view.setScene(scene)

        button_svg = QtWidgets.QPushButton('Export SVG')
        button_svg.clicked.connect(self.export_svg)

        button_pdf = QtWidgets.QPushButton('Export PDF')
        button_pdf.clicked.connect(self.export_pdf)

        button_pdf2 = QtWidgets.QPushButton('Print PDF')
        button_pdf2.clicked.connect(self.print_pdf)

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(view)
        layout.addWidget(button_svg)
        layout.addWidget(button_pdf)
        layout.addWidget(button_pdf2)
        self.setLayout(layout)

        self.graph = view

    def export_svg(self):
        file, _ = QFileDialog.getSaveFileName(
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
        file, _ = QFileDialog.getSaveFileName(
            self, 'Export As...', 'graph.pdf', 'PDF Files (*.pdf)')
        if not file:
            return
        print('PDF >', file)

        writer = QtGui.QPdfWriter(file)

        painter = QtGui.QPainter()
        painter.begin(writer)
        self.graph.render(painter)
        painter.end()

    def print_pdf(self):
        file, _ = QFileDialog.getSaveFileName(
            self, 'Export As...', 'graph.pdf', 'PDF Files (*.pdf)')
        if not file:
            return
        print('PDF >', file)

        printer = QPrinter(QPrinter.HighResolution)
        printer.setOutputFormat(QPrinter.PdfFormat)
        printer.setOutputFileName(file)

        painter = QtGui.QPainter()
        painter.begin(printer)
        self.graph.render(painter)
        painter.end()


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    window = Window()
    window.show()

    sys.exit(app.exec())
