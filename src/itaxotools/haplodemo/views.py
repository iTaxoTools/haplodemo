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

from itaxotools.haplodemo.models import DivisionListModel, MemberTreeModel


class ColorDelegate(QtWidgets.QStyledItemDelegate):
    def paint(self, painter, option, index):
        super().paint(painter, option, index)

        # Draw the decoration icon on top of the background
        decoration_rect = QtCore.QRect(option.rect.x() + 2, option.rect.y() + 2, 16, option.rect.height() - 4)
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
    def __init__(self, members: MemberTreeModel):
        super().__init__()
        self.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self.setHeaderHidden(True)
        self.setModel(members)

    def setModel(self, model: MemberTreeModel):
        if self.model():
            self.model().modelReset.disconnect(self.expandAll)
        super().setModel(model)
        model.modelReset.connect(self.expandAll)
        self.expandAll()

    def select(self, index: QtCore.QModelIndex | None):
        if index is None or not index.isValid():
            self.clearSelection()
            index_top = self.model().index(0, 0)
            self.scrollTo(index_top)
            return
        self.selectionModel().select(index, QtCore.QItemSelectionModel.Select)
        self.scrollTo(index)
