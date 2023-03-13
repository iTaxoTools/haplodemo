import sys
from PySide6.QtWidgets import (
    QApplication, QGraphicsView, QGraphicsScene, QGraphicsEllipseItem,
    QGraphicsLineItem, QGraphicsItem, QGraphicsTextItem, QDialog,
    QPushButton, QVBoxLayout, QFileDialog  )
from PySide6.QtGui import QPen, QPainter, QFont, QColor, QPdfWriter
from PySide6.QtCore import Qt, QPointF, Signal, QSize, QRect
from PySide6.QtSvg import QSvgGenerator
from PySide6.QtPrintSupport import QPrinter


class EllipseItem(QGraphicsEllipseItem):
    def __init__(self, x, y, r, text, brush):
        super().__init__(0, 0, r, r)
        self.setFlag(QGraphicsItem.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges, True)
        self.setBrush(brush)
        self.setPos(x, y)

        # Create a QGraphicsTextItem and set its position to the center of the ellipse
        self.textItem = QGraphicsTextItem(text, self)
        font = QFont()
        font.setPointSize(14)
        self.textItem.setFont(font)
        self.textItem.setDefaultTextColor(Qt.white)
        self.textItem.setPos(self.rect().width() / 2 - self.textItem.boundingRect().width() / 2, self.rect().height() / 2 - self.textItem.boundingRect().height() / 2)

    def itemChange(self, change, value):
        if self.scene() is not None:
            if change == QGraphicsItem.ItemPositionHasChanged:
                # Emit a signal to notify that the item has been moved
                self.scene().itemMoved.emit()
        return super().itemChange(change, value)


class Scene(QGraphicsScene):
    itemMoved = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.line1 = QGraphicsLineItem()
        self.line1.setPen(QPen(Qt.black, 2))
        self.addItem(self.line1)

        self.line2 = QGraphicsLineItem()
        self.line2.setPen(QPen(Qt.black, 2))
        self.addItem(self.line2)

        self.ellipse1 = EllipseItem(85, 140, 50, 'A', QColor('#20639b'))
        self.addItem(self.ellipse1)

        self.ellipse2 = EllipseItem(200, 200, 50, 'B', QColor('#ed553b'))
        self.addItem(self.ellipse2)

        self.ellipse3 = EllipseItem(180, 110, 30, 'C', QColor('#3caea3'))
        self.addItem(self.ellipse3)

        # Connect the itemMoved signal to the updateLines slot
        self.itemMoved.connect(self.updateLines)
        self.updateLines()

    def updateLines(self):
        # Get the center points of the ellipses
        center1 = self.ellipse1.scenePos() + QPointF(self.ellipse1.rect().width() / 2, self.ellipse1.rect().height() / 2)
        center2 = self.ellipse2.scenePos() + QPointF(self.ellipse2.rect().width() / 2, self.ellipse2.rect().height() / 2)
        center3 = self.ellipse3.scenePos() + QPointF(self.ellipse3.rect().width() / 2, self.ellipse3.rect().height() / 2)

        # Set the starting and ending points of the line
        self.line1.setLine(center1.x(), center1.y(), center2.x(), center2.y())
        self.line2.setLine(center1.x(), center1.y(), center3.x(), center3.y())

class Window(QDialog):
    def __init__(self):
        super().__init__()
        self.resize(400, 400)

        view = QGraphicsView()
        scene = Scene()
        view.setRenderHints(QPainter.Antialiasing)
        view.setScene(scene)

        button_svg = QPushButton('Export SVG')
        button_svg.clicked.connect(self.export_svg)

        button_pdf = QPushButton('Export PDF')
        button_pdf.clicked.connect(self.export_pdf)

        button_pdf2 = QPushButton('Print PDF')
        button_pdf2.clicked.connect(self.print_pdf)

        layout = QVBoxLayout()
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

        generator = QSvgGenerator()
        generator.setFileName(file)
        generator.setSize(QSize(200, 200))
        generator.setViewBox(QRect(0, 0, 200, 200))

        painter = QPainter()
        painter.begin(generator)
        self.graph.render(painter)
        painter.end()

    def export_pdf(self):
        file, _ = QFileDialog.getSaveFileName(
            self, 'Export As...', 'graph.pdf', 'PDF Files (*.pdf)')
        if not file:
            return
        print('PDF >', file)

        writer = QPdfWriter(file)

        painter = QPainter()
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

        painter = QPainter()
        painter.begin(printer)
        self.graph.render(painter)
        painter.end()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = Window()
    window.show()

    sys.exit(app.exec())
