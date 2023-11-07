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

"""
Due to the new MRO for PySide>=6.5, these protocols must be first
and not subclass QtWidgets.QGraphicsItem. Instead, we assume that
the next item in the MRO is a subclass of QtWidgets.QGraphicsItem.
"""

from PySide6 import QtCore, QtWidgets

from itaxotools.common.utility import override


class HoverableItem:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        super().setAcceptHoverEvents(True)
        self._state_hovered = False

    @override
    def hoverEnterEvent(self, event):
        super().hoverEnterEvent(event)
        self.set_hovered(True)

    @override
    def hoverLeaveEvent(self, event):
        super().hoverLeaveEvent(event)
        self.set_hovered(False)

    def set_hovered(self, value):
        self._state_hovered = value
        super().update()

    def is_hovered(self):
        return self._state_hovered


class HighlightableItem(HoverableItem):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._highlight_color = QtCore.Qt.magenta

    def set_highlight_color(self, value):
        self._highlight_color = value
        super().update()

    def highlight_color(self):
        return self._highlight_color

    def is_highlighted(self):
        return self._state_hovered


class SoloMovableItem:
    """
    By default, moving an item also moves other selected items.
    This class avoids this behaviour, moving only the item itself.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        super().setFlag(QtWidgets.QGraphicsItem.ItemIsMovable)
        super().setFlag(QtWidgets.QGraphicsItem.ItemIsSelectable, False)
        super().setAcceptedMouseButtons(QtCore.Qt.LeftButton)
        self._locked_drag_pos = None

    @override
    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self._locked_drag_pos = event.pos()
        super().mousePressEvent(event)

    @override
    def mouseMoveEvent(self, event):
        if self._locked_drag_pos:
            delta = event.pos() - self._locked_drag_pos
            super().setPos(super().pos() + delta)
        else:
            super().mouseMoveEvent(event)

    @override
    def mouseReleaseEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self._locked_drag_pos = None
        super().mouseReleaseEvent(event)


class SoloMovableItemWithHistory(SoloMovableItem):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._locked_item_pos = super().pos()

    @override
    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self._locked_item_pos = super().pos()
        super().mousePressEvent(event)

    @override
    def mouseReleaseEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            if self._locked_item_pos != self.pos():
                self.post_solo_movement()
        super().mouseReleaseEvent(event)

    def post_solo_movement(self):
        if not self.scene():
            return
        self.scene().handle_solo_movement(self)


class IgnorableItem:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._ignore_events = False

    def set_ignore_events(self, value):
        self._ignore_events = value

    def sceneEvent(self, event):
        if self._ignore_events:
            return False
        return super().sceneEvent(event)
