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


class UndoCommand(QtGui.QUndoCommand):
    """Keep references to all commands in order to
    avoid corruption due to garbage collection"""

    _commands = list()

    @classmethod
    def clear_history(cls):
        """Causes crash for nested commands"""
        return
        cls._commands = list()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._commands.append(self)

    def mergeChildrenWith(self, other: UndoCommand) -> bool:
        our_children = [self.child(x) for x in range(self.childCount())]
        other_children = [other.child(x) for x in range(other.childCount())]

        for other_child in other_children:
            other_child_merged = False
            for our_child in our_children:
                merged = our_child.mergeWith(other_child)
                if merged:
                    other_child_merged = True
                    break
            if not other_child_merged:
                return False

        return True


class BezierEditCommand(UndoCommand):
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
        super().undo()
        self.item.p1 = self.old_p1
        self.item.p2 = self.old_p2
        self.item.c1 = self.old_c1
        self.item.c2 = self.old_c2
        self.item.update_path()

    def redo(self):
        super().redo()
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


class NodeMovementCommand(UndoCommand):
    def __init__(self, item: Vertex, parent=None):
        super().__init__(parent)
        self.setText('Move node')
        self.item = item
        self.old_pos = QtCore.QPointF(item.locked_pos)
        self.new_pos = QtCore.QPointF(item.pos())

        for bezier in item.beziers.values():
            BezierEditCommand(bezier, self)

        def create_child_command(node):
            if node is not self.item:
                NodeMovementCommand(node, self)

        if item.isMovementRecursive():
            item.mapNodeRecursive(create_child_command)

    def undo(self):
        super().undo()
        self.item.setPos(self.old_pos)
        self.item.update()

    def redo(self):
        super().redo()
        self.item.setPos(self.new_pos)
        self.item.update()

    def mergeWith(self, other: NodeMovementCommand) -> bool:
        if self.item != other.item:
            return False
        self.new_pos = other.new_pos
        self.mergeChildrenWith(other)
        return True

    def id(self) -> int:
        return 1001


class SoloMovementCommand(UndoCommand):
    def __init__(self, item: Vertex, parent=None):
        super().__init__(parent)
        self.setText('Move solo item')
        self.item = item
        self.old_pos = QtCore.QPointF(item._locked_item_pos)
        self.new_pos = QtCore.QPointF(item.pos())

    def undo(self):
        super().undo()
        self.item.setPos(self.old_pos)
        self.item.update()

    def redo(self):
        super().redo()
        self.item.setPos(self.new_pos)
        self.item.update()

    def mergeWith(self, other: SoloMovementCommand) -> bool:
        if self.item != other.item:
            return False
        self.new_pos = other.new_pos
        return True

    def id(self) -> int:
        return 1003
