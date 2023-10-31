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

from PySide6 import QtCore, QtGui, QtWidgets

from typing import Callable

from itaxotools.common.bindings import PropertyRef

from .items.bezier import BezierCurve
from .items.boundary import BoundaryRect
from .items.nodes import Vertex


class UndoCommandMeta(type(QtGui.QUndoCommand)):
    _command_id_counter = 1000

    def __new__(cls, name, bases, attrs):
        cls._command_id_counter += 1
        attrs['_command_id'] = cls._command_id_counter
        return super().__new__(cls, name, bases, attrs)


class UndoCommand(QtGui.QUndoCommand, metaclass=UndoCommandMeta):
    """Keep references to all commands in order to
    avoid corruption due to garbage collection"""

    _commands = list()
    _command_id = 1000

    @classmethod
    def clear_history(cls):
        """Causes crash for nested commands"""
        # cls._commands = list()
        return

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

    def id(self) -> int:
        return self._command_id


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


class SoloMovementCommand(UndoCommand):
    def __init__(self, item: Vertex, parent=None):
        super().__init__(parent)
        self.setText('Move item')
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


class BoundaryResizedCommand(UndoCommand):
    def __init__(self, item: BoundaryRect, parent=None):
        super().__init__(parent)
        self.setText('Resize boundary')
        self.item = item
        self.old_rect = QtCore.QRectF(item.locked_rect)
        self.new_rect = QtCore.QRectF(item.rect())

    def undo(self):
        super().undo()
        self.item.setRect(self.old_rect)
        self.item.adjust_rects()
        self.item.update()

    def redo(self):
        super().redo()
        self.item.setRect(self.new_rect)
        self.item.adjust_rects()
        self.item.update()

    def mergeWith(self, other: BoundaryResizedCommand) -> bool:
        if self.item != other.item:
            return False
        self.new_rect = other.new_rect
        return True


class SceneRotationCommand(UndoCommand):
    def __init__(self, scene: QtWidgets.QGraphicsScene, parent=None):
        super().__init__(parent)
        self.setText('Scene rotation')
        self.scene = scene

        for node in (item for item in scene.items() if isinstance(item, Vertex)):
            if node.in_scene_rotation:
                NodeMovementCommand(node, self)

    def mergeWith(self, other: SceneRotationCommand) -> bool:
        if self.scene != other.scene:
            return False
        self.mergeChildrenWith(other)
        return True


class PropertyGroupCommand(UndoCommand):
    def __init__(self, text: str, parent=None):
        super().__init__(parent)
        self.setText(text)

    def mergeWith(self, other: UndoCommand) -> bool:
        return False


class PropertyChangedCommand(UndoCommand):
    def __init__(self, property: PropertyRef, old_value: object, new_value: object, parent=None):
        super().__init__(parent)
        self.setText(f'Property {property.key} change')
        self.property = property
        self.old_value = old_value
        self.new_value = new_value

    def undo(self):
        super().undo()
        self.property.set(self.old_value)

    def redo(self):
        super().redo()
        self.property.set(self.new_value)

    def mergeWith(self, other: UndoCommand) -> bool:
        return False


class CustomCommand(UndoCommand):
    def __init__(self, text: str, undo: Callable, redo: Callable, parent=None):
        super().__init__(parent)
        self.undo_callable = undo
        self.redo_callable = redo
        self.setText(text)

    def undo(self):
        super().undo()
        self.undo_callable()

    def redo(self):
        super().redo()
        self.redo_callable()

    def mergeWith(self, other: UndoCommand) -> bool:
        return False


class ApplyCommand(CustomCommand):
    def __init__(self, text: str, apply: Callable, parent=None):
        super().__init__(text, apply, apply, parent)
