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

from PySide6 import QtGui

from .items.nodes import Vertex


class MoveCommand(QtGui.QUndoCommand):
    def __init__(self, item: Vertex, parent=None):
        super().__init__(parent)
        self.setText('Move node')
        self.item = item
        self.scene = self.item.scene()
        self.old_pos = item.locked_pos
        self.new_pos = item.pos()

    def undo(self):
        self.item.setPos(self.old_pos)
        self.scene.update()

    def redo(self):
        self.item.setPos(self.new_pos)
        self.scene.update()

    def mergeWith(self, other: MoveCommand) -> bool:
        if self.item != other.item:
            return False
        self.new_pos = other.new_pos
        return True

    def id(self) -> int:
        return 1001
