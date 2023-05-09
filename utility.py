from PySide6 import QtCore
from PySide6 import QtGui

def shapeFromPath(path: QtGui.QPainterPath, pen: QtGui.QPen):
    # reimplement qt_graphicsItem_shapeFromPath
    penWidthZero = 0.00000001
    if path == QtGui.QPainterPath() or pen == QtCore.Qt.NoPen:
        return path
    ps = QtGui.QPainterPathStroker()
    ps.setCapStyle(pen.capStyle())
    if pen.widthF() <= 0.0:
        ps.setWidth(penWidthZero)
    else:
        ps.setWidth(pen.widthF())
    ps.setJoinStyle(pen.joinStyle())
    ps.setMiterLimit(pen.miterLimit())
    p = ps.createStroke(path)
    p.addPath(path)
    return p
