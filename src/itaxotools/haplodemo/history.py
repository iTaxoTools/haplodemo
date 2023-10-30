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

from __future__ import annotations

from PySide6 import QtCore, QtGui

from .items.bezier import BezierCurve
from .items.nodes import Vertex


class BezierEditCommand(QtGui.QUndoCommand):
    def __init__(self, item: BezierCurve, parent=None):
        super().__init__(parent)
        self.setText('Edit bezier')
        self.item = item

        self.old_p1 = QtCore.QPointF(item.locked_p1)
        self.old_p2 = QtCore.QPointF(item.locked_p2)
        self.old_c1 = QtCore.QPointF(item.locked_c1)
        self.old_c2 = QtCore.QPointF(item.locked_c2)

        self.new_p1 = QtCore.QPointF(item.p1)
        self.new_p2 = QtCore.QPointF(item.p2)
        self.new_c1 = QtCore.QPointF(item.c1)
        self.new_c2 = QtCore.QPointF(item.c2)

    def undo(self):
        self.item.p1 = self.old_p1
        self.item.p2 = self.old_p2
        self.item.c1 = self.old_c1
        self.item.c2 = self.old_c2
        self.item.update_path()

    def redo(self):
        self.item.p1 = self.new_p1
        self.item.p2 = self.new_p2
        self.item.c1 = self.new_c1
        self.item.c2 = self.new_c2
        self.item.update_path()

    def mergeWith(self, other: NodeMovementCommand) -> bool:
        if self.item != other.item:
            return False
        self.new_p1 = other.new_p1
        self.new_p2 = other.new_p2
        self.new_c1 = other.new_c1
        self.new_c2 = other.new_c2
        return True

    def id(self) -> int:
        return 1002


class NodeMovementCommand(QtGui.QUndoCommand):
    def __init__(self, item: Vertex, parent=None):
        super().__init__(parent)
        self.setText('Move node')
        self.item = item
        self.old_pos = QtCore.QPointF(item.locked_pos)
        self.new_pos = QtCore.QPointF(item.pos())

    def undo(self):
        self.item.setPos(self.old_pos)
        self.item.update()

    def redo(self):
        self.item.setPos(self.new_pos)
        self.item.update()

    def mergeWith(self, other: NodeMovementCommand) -> bool:
        if self.item != other.item:
            return False
        self.new_pos = other.new_pos
        return True

    def id(self) -> int:
        return 1001
