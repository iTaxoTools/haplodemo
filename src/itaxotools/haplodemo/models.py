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

from collections import defaultdict

from itaxotools.common.utility import override

from .palettes import Palette
from .types import Division, MemberItem, Partition


class PartitionListModel(QtCore.QAbstractListModel):
    partitionsChanged = QtCore.Signal(object)
    PartitionRole = QtCore.Qt.UserRole

    def __init__(self, parent=None):
        super().__init__(parent)
        self._partitions: list[Partition] = []

    @override
    def rowCount(self, parent=QtCore.QModelIndex()):
        return len(self._partitions)

    @override
    def data(self, index, role=QtCore.Qt.DisplayRole):
        if not index.isValid() or not (0 <= index.row() < self.rowCount()):
            return None

        partition = self._partitions[index.row()]

        if role == QtCore.Qt.DisplayRole:
            return partition.key
        elif role == QtCore.Qt.EditRole:
            return partition.key
        elif role == self.PartitionRole:
            return partition

        return None

    @override
    def flags(self, index):
        return QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable

    def set_partitions(self, partitions: iter[tuple[str, dict[str, str]]]):
        self.beginResetModel()
        self._partitions = [Partition(key, map) for key, map in partitions]
        self.endResetModel()
        self.partitionsChanged.emit(self.all())

    def all(self):
        return list(self._partitions)


class DivisionListModel(QtCore.QAbstractListModel):
    colorMapChanged = QtCore.Signal(object)
    divisionsChanged = QtCore.Signal(object)

    def __init__(self, names=[], palette=Palette.Spring(), parent=None):
        super().__init__(parent)
        self._palette = palette
        self._default_color = palette.default
        self._divisions = list()
        self.set_divisions_from_keys(names)
        self.set_palette(palette)

        self.dataChanged.connect(self.handle_data_changed)
        self.modelReset.connect(self.handle_data_changed)

    @override
    def rowCount(self, parent=QtCore.QModelIndex()):
        return len(self._divisions)

    @override
    def data(self, index, role=QtCore.Qt.DisplayRole):
        if not index.isValid() or not (0 <= index.row() < self.rowCount()):
            return None

        key = self._divisions[index.row()].key
        color = self._divisions[index.row()].color

        if role == QtCore.Qt.DisplayRole:
            return key
        elif role == QtCore.Qt.EditRole:
            return color
        elif role == QtCore.Qt.DecorationRole:
            color = QtGui.QColor(color)
            pixmap = QtGui.QPixmap(16, 16)
            pixmap.fill(color)
            return QtGui.QIcon(pixmap)

        return None

    @override
    def setData(self, index, value, role=QtCore.Qt.EditRole):
        if not index.isValid() or not (0 <= index.row() < self.rowCount()):
            return False

        if role == QtCore.Qt.EditRole:
            color = value.strip()
            if not color.startswith("#"):
                color = "#" + color

            if not QtGui.QColor.isValidColor(color):
                return False

            self._divisions[index.row()].color = color
            self.dataChanged.emit(index, index)
            return True

        return False

    @override
    def flags(self, index):
        return (
            QtCore.Qt.ItemIsEditable
            | QtCore.Qt.ItemIsEnabled
            | QtCore.Qt.ItemIsSelectable
        )

    def set_divisions_from_keys(self, keys):
        self.beginResetModel()
        palette = self._palette
        self._divisions = [Division(keys[i], palette[i]) for i in range(len(keys))]
        self.endResetModel()
        self.divisionsChanged.emit(self.all())

    def set_palette(self, palette):
        self.beginResetModel()
        self._default_color = palette.default
        for index, division in enumerate(self._divisions):
            division.color = palette[index]
        self.endResetModel()

    def get_color_map(self):
        map = {d.key: d.color for d in self._divisions}
        return defaultdict(lambda: self._default_color, map)

    def handle_data_changed(self, *args, **kwargs):
        self.colorMapChanged.emit(self.get_color_map())

    def all(self):
        return list(self._divisions)


class MemberTreeModel(QtCore.QAbstractItemModel):
    def __init__(self, root: MemberItem = None, parent=None):
        super().__init__(parent)
        self.root_item = None
        self.set_root(root)

    def set_dict(self, data: dict[str, iter[str]]):
        root_item = MemberItem("root")
        for node_name, member_names in data.items():
            node_item = MemberItem(node_name, root_item)
            for member_name in member_names:
                MemberItem(member_name, node_item)
        self.set_root(root_item)

    def set_root(self, root: MemberItem = None):
        self.beginResetModel()
        if not root:
            self.root_item = MemberItem("None")
        else:
            self.root_item = root
        self.endResetModel()

    def get_index_map(self) -> dict[str, QtCore.QModelIndex]:
        return defaultdict(
            QtCore.QModelIndex,
            {
                node.name: self.createIndex(row, 0, node)
                for row, node in enumerate(self.root_item.children)
            },
        )

    @override
    def index(self, row, column, parent=QtCore.QModelIndex()):
        if not self.hasIndex(row, column, parent):
            return QtCore.QModelIndex()
        if not parent.isValid():
            parent_item = self.root_item
        else:
            parent_item = parent.internalPointer()
        child_item = parent_item.children[row]
        if child_item:
            return self.createIndex(row, column, child_item)
        return QtCore.QModelIndex()

    @override
    def parent(self, index):
        if not index.isValid():
            return QtCore.QModelIndex()
        child_item = index.internalPointer()
        parent_item = child_item.parent
        if parent_item == self.root_item:
            return QtCore.QModelIndex()
        return self.createIndex(parent_item.index, 0, parent_item)

    @override
    def rowCount(self, parent=QtCore.QModelIndex()):
        if parent.column() > 0:
            return 0
        if not parent.isValid():
            parent_item = self.root_item
        else:
            parent_item = parent.internalPointer()
        return len(parent_item.children)

    @override
    def columnCount(self, parent=QtCore.QModelIndex()):
        return 1

    @override
    def data(self, index, role=QtCore.Qt.DisplayRole):
        if not index.isValid():
            return None
        if role != QtCore.Qt.DisplayRole:
            return None
        item = index.internalPointer()
        return item.name
