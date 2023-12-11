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
from itaxotools.common.utility import override

from .items.bezier import BezierCurve
from .items.boundary import BoundaryRect
from .items.edges import Edge
from .items.labels import Label
from .items.nodes import Vertex


class UndoStack(QtGui.QUndoStack):
    """Commands are not merged immediately, rather we wait for the
    first unmergable command, then merge all commands before it"""

    @override
    def push(self, cmd: UndoCommand):
        self.merge_history(cmd)
        super().push(cmd)

    @override
    def undo(self):
        super().undo()
        command: UndoCommand = self.command(self.index() - 1)
        if command is not None and command.isObsolete():
            self.undo()

    def merge_history(self, new_command: UndoCommand):
        if not self.index() > 0:
            return

        current_command: UndoCommand = self.command(self.index() - 1)
        if current_command.can_merge_with(new_command):
            return

        index = self.index()
        while True:
            index -= 1
            older_command: UndoCommand = self.command(index - 1)
            newer_command: UndoCommand = self.command(index)
            if older_command is None or newer_command is None:
                return
            if older_command.can_merge_with(newer_command):
                older_command.merge_with(newer_command)
                newer_command.setObsolete(True)
            else:
                return


class UndoCommandMeta(type(QtGui.QUndoCommand)):
    _command_id_counter = 1000

    def __new__(cls, name, bases, attrs):
        cls._command_id_counter += 1
        attrs["_command_id"] = cls._command_id_counter
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

    @override
    def mergeWith(self, other: QtGui.QUndoCommand) -> bool:
        """Never use the default merging strategy"""
        return False

    @override
    def id(self) -> int:
        return self._command_id

    def merge_with(self, other: QtGui.QUndoCommand) -> None:
        raise NotImplementedError()

    def can_merge_with(self, other: UndoCommand) -> bool:
        return False

    def merge_children_with(self, other: UndoCommand) -> bool:
        our_children: list[UndoCommand] = [
            self.child(x) for x in range(self.childCount())
        ]
        other_children: list[UndoCommand] = [
            other.child(x) for x in range(other.childCount())
        ]

        for other_child in other_children:
            other_child_merged = False
            for our_child in our_children:
                if our_child.can_merge_with(other_child):
                    our_child.merge_with(other_child)
                    other_child_merged = True
                    break
            if not other_child_merged:
                return False

        return True


class BezierEditCommand(UndoCommand):
    def __init__(self, item: BezierCurve, parent=None):
        super().__init__(parent)
        self.setText("Edit bezier")
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

    def can_merge_with(self, other: NodeMovementCommand) -> bool:
        if self.id() != other.id():
            return False
        if self.item != other.item:
            return False
        return True

    def merge_with(self, other: NodeMovementCommand):
        self.new_p1 = other.new_p1
        self.new_p2 = other.new_p2
        self.new_c1 = other.new_c1
        self.new_c2 = other.new_c2


class NodeMovementCommand(UndoCommand):
    def __init__(self, item: Vertex, recurse=True, parent=None):
        super().__init__(parent)
        self.setText("Move node")
        self.item = item
        self.old_pos = QtCore.QPointF(item.locked_pos)
        self.new_pos = QtCore.QPointF(item.pos())

        for bezier in item.beziers.values():
            BezierEditCommand(bezier, self)

        def create_child_command(node):
            if node is not self.item:
                NodeMovementCommand(node, parent=self)

        if item.isMovementRecursive() and recurse:
            item.mapNodeRecursive(create_child_command)

    def undo(self):
        super().undo()
        self.item.setPos(self.old_pos)
        self.item.update()

    def redo(self):
        super().redo()
        self.item.setPos(self.new_pos)
        self.item.update()

    def can_merge_with(self, other: NodeMovementCommand) -> bool:
        if self.id() != other.id():
            return False
        if self.item != other.item:
            return False
        return True

    def merge_with(self, other: NodeMovementCommand):
        self.new_pos = other.new_pos
        self.merge_children_with(other)


class EdgeStyleCommand(UndoCommand):
    def __init__(self, item: Edge, parent=None):
        super().__init__(parent)
        self.setText("Style edge")
        self.item = item
        self.old_style = item.locked_style
        self.new_style = item.style

    def undo(self):
        super().undo()
        self.item.set_style(self.old_style)

    def redo(self):
        super().redo()
        self.item.set_style(self.new_style)

    def can_merge_with(self, other: EdgeStyleCommand) -> bool:
        if self.id() != other.id():
            return False
        if self.item != other.item:
            return False
        return True

    def merge_with(self, other: EdgeStyleCommand):
        self.new_style = other.new_style


class LabelMovementCommand(UndoCommand):
    def __init__(self, item: Label, parent=None):
        super().__init__(parent)
        self.setText("Move label")
        self.item = item
        self.old_rect = QtCore.QRect(item.locked_rect)
        self.new_rect = QtCore.QRect(item.rect)

    def undo(self):
        super().undo()
        self.item.setRect(self.old_rect)

    def redo(self):
        super().redo()
        self.item.setRect(self.new_rect)

    def can_merge_with(self, other: LabelMovementCommand) -> bool:
        if self.id() != other.id():
            return False
        if self.item != other.item:
            return False
        return True

    def merge_with(self, other: LabelMovementCommand):
        self.new_rect = other.new_rect


class SoloMovementCommand(UndoCommand):
    def __init__(self, item: Vertex, parent=None):
        super().__init__(parent)
        self.setText("Move item")
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

    def can_merge_with(self, other: SoloMovementCommand) -> bool:
        if self.id() != other.id():
            return False
        if self.item != other.item:
            return False
        return True

    def merge_with(self, other: SoloMovementCommand):
        self.new_pos = other.new_pos


class BoundaryResizedCommand(UndoCommand):
    def __init__(self, item: BoundaryRect, parent=None):
        super().__init__(parent)
        self.setText("Resize boundary")
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

    def can_merge_with(self, other: BoundaryResizedCommand) -> bool:
        if self.id() != other.id():
            return False
        if self.item != other.item:
            return False
        return True

    def merge_with(self, other: BoundaryResizedCommand):
        self.new_rect = other.new_rect


class SceneRotationCommand(UndoCommand):
    def __init__(self, scene: QtWidgets.QGraphicsScene, parent=None):
        super().__init__(parent)
        self.setText("Scene rotation")
        self.scene = scene

        for node in (item for item in scene.items() if isinstance(item, Vertex)):
            if node.in_scene_rotation:
                NodeMovementCommand(node, parent=self)

    def can_merge_with(self, other: SceneRotationCommand) -> bool:
        if self.id() != other.id():
            return False
        if self.scene != other.scene:
            return False
        return True

    def merge_with(self, other: SceneRotationCommand):
        self.merge_children_with(other)


class PropertyGroupCommand(UndoCommand):
    def __init__(self, text: str, parent=None):
        super().__init__(parent)
        self.setText(text)


class PropertyChangedCommand(UndoCommand):
    def __init__(
        self, property: PropertyRef, old_value: object, new_value: object, parent=None
    ):
        super().__init__(parent)
        self.setText(f"Property {property.key} change")
        self.property = property
        self.old_value = old_value
        self.new_value = new_value

    def undo(self):
        super().undo()
        self.property.set(self.old_value)

    def redo(self):
        super().redo()
        self.property.set(self.new_value)


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


class ApplyCommand(CustomCommand):
    def __init__(self, text: str, apply: Callable, parent=None):
        super().__init__(text, apply, apply, parent)
