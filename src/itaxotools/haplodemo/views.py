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

from PySide6 import QtCore, QtGui, QtWidgets

from typing import Callable

from itaxotools.common.utility import override

from .models import DivisionListModel, MemberTreeModel


class ColorDelegate(QtWidgets.QStyledItemDelegate):
    def paint(self, painter, option, index):
        super().paint(painter, option, index)

        # Draw the decoration icon on top of the background
        decoration_rect = QtCore.QRect(
            option.rect.x() + 2, option.rect.y() + 2, 16, option.rect.height() - 4
        )
        icon = index.data(QtCore.Qt.DecorationRole)
        if icon and not icon.isNull():
            icon.paint(painter, decoration_rect)

    def createEditor(self, parent, option, index):
        editor = QtWidgets.QColorDialog(parent=parent)
        editor.setOption(QtWidgets.QColorDialog.DontUseNativeDialog, True)
        return editor

    def setEditorData(self, editor, index):
        color = index.model().data(index, QtCore.Qt.EditRole)
        editor.setCurrentColor(QtGui.QColor(color))

    def setModelData(self, editor, model, index):
        model.setData(index, editor.currentColor().name(), QtCore.Qt.EditRole)

    def updateEditorGeometry(self, editor, option, index):
        # Override required for centering the dialog
        pass

    @staticmethod
    def setCustomColors(palette):
        for i in range(16):
            QtWidgets.QColorDialog.setCustomColor(i, QtGui.QColor(palette[i]))


class DivisionView(QtWidgets.QListView):
    def __init__(self, divisions: DivisionListModel):
        super().__init__()
        self.setModel(divisions)
        self.setItemDelegate(ColorDelegate(self))


class MemberView(QtWidgets.QTreeView):
    nodeSelected = QtCore.Signal(str)

    def __init__(self, members: MemberTreeModel):
        super().__init__()
        self._maximum_string_length = 0
        self._string_padding = 60
        self._minimum_width = 140
        self._maximum_width = 360

        self.setSelectionBehavior(
            QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.setAlternatingRowColors(True)
        self.setHeaderHidden(True)
        self.setModel(members)

    @override
    def setModel(self, model: MemberTreeModel):
        if self.model():
            self.model().modelReset.disconnect(self.handle_model_reset)
        super().setModel(model)
        model.modelReset.connect(self.handle_model_reset)
        self.expandAll()

    @override
    def setFont(self, font):
        super().setFont(font)
        self.update_maximum_string_length()

    @override
    def minimumSizeHint(self) -> QtCore.QSize:
        hint = super().sizeHint()
        return QtCore.QSize(self._minimum_width, hint.height())

    @override
    def sizeHint(self) -> QtCore.QSize:
        hint = super().sizeHint()
        width = self._maximum_string_length + self._string_padding
        width = max(width, self._minimum_width)
        width = min(width, self._maximum_width)
        return QtCore.QSize(width, hint.height())

    def handle_model_reset(self):
        self.expandAll()
        self.update_maximum_string_length()

    def update_maximum_string_length(self):
        metrics = QtGui.QFontMetrics(self.font())
        length = self.get_maximum_string_length(metrics.horizontalAdvance)
        self._maximum_string_length = length

    def get_maximum_string_length(
        self, pixels_from_string: Callable[[str], int], parent=QtCore.QModelIndex()
    ) -> int:
        model = self.model()
        rows = model.rowCount(parent)
        lengths = [0]

        for row in range(rows):
            index = model.index(row, 0, parent)
            data = model.data(index)
            lengths.append(pixels_from_string(data))

            if model.hasChildren(index):
                max_children_length = self.get_maximum_string_length(
                    pixels_from_string, index
                )
                lengths.append(max_children_length)

        return max(lengths)

    @override
    def selectionChanged(self, selected, deselected):
        super().selectionChanged(selected, deselected)
        indices = selected.indexes()
        if not indices:
            self.nodeSelected.emit(None)
            return

        index = indices[0]
        parent_index = self.model().parent(index)
        if parent_index.isValid():
            index = parent_index
        name = self.model().data(index)
        self.nodeSelected.emit(name)

    def select(self, index: QtCore.QModelIndex):
        self.clearSelection()
        if not index.isValid():
            return
        self.selectionModel().select(index, QtCore.QItemSelectionModel.Select)
        self.scrollTo(index)
