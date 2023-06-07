# -----------------------------------------------------------------------------
# Haplodemo - Visualize, edit and export haplotype networks
# Copyright (C) 2023  Patmanidis Stefanos
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
# -----------------------------------------------------------------------------

from PySide6 import QtCore, QtGui


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
