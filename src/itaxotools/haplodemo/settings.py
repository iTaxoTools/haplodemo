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

from itertools import chain

from itaxotools.common.bindings import (
    Binder, Instance, Property, PropertyObject)

from itaxotools.haplodemo.models import DivisionListModel, PartitionListModel
from itaxotools.haplodemo.palettes import Palette
from itaxotools.haplodemo.types import LayoutType


def get_default_font():
    font = QtGui.QFont('Arial')
    font.setPixelSize(14)
    return font


class NodeSizeSettings(PropertyObject):
    a = Property(float, 10)
    b = Property(float, 2)
    c = Property(float, 0.2)
    d = Property(float, 1)
    e = Property(float, 0)
    f = Property(float, 5)

    def get_all_values(self):
        return [property.value for property in self.properties]

    def set_all_values(self, *values):
        for property, value in zip(self.properties, values):
            property.value = value


class ScaleSettings(PropertyObject):
    marks = Property(list, [5, 10, 20])


class FieldSettings(PropertyObject):
    show_groups = Property(bool, True)
    show_isolated = Property(bool, True)


class Settings(PropertyObject):
    partitions = Property(PartitionListModel, Instance, tag='frozen')
    divisions = Property(DivisionListModel, Instance, tag='frozen')

    node_sizes = Property(NodeSizeSettings, Instance, tag='frozen')
    fields = Property(FieldSettings, Instance, tag='frozen')
    scale = Property(ScaleSettings, Instance, tag='frozen')

    partition_index = Property(QtCore.QModelIndex, Instance)

    palette = Property(Palette, Palette.Spring())
    highlight_color = Property(QtGui.QColor, QtCore.Qt.magenta)

    font = Property(QtGui.QFont, get_default_font())
    rotational_movement = Property(bool, True)
    recursive_movement = Property(bool, True)
    label_movement = Property(bool, False)

    rotate_scene = Property(bool, False)
    show_legend = Property(bool, False)
    show_scale = Property(bool, False)

    layout = Property(LayoutType, LayoutType.ModifiedSpring)
    layout_scale = Property(float, 3)
    edge_length = Property(float, 100)

    pen_width_nodes = Property(float, 1)
    pen_width_edges = Property(float, 2)

    node_label_template = Property(str, 'NAME')
    edge_label_template = Property(str, '(WEIGHT)')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.binder = Binder()
        self.binder.bind(self.properties.palette, self.divisions.set_palette)
        self.binder.bind(self.properties.palette, self.properties.highlight_color, lambda x: x.highlight)
        self.binder.bind(self.properties.font, self.enforce_pixel_size)

    def enforce_pixel_size(self, font: QtGui.QFont | None):
        if font is None:
            return
        if font.pixelSize() == -1:
            font = QtGui.QFont(font)
            size = font.pointSize()
            font.setPixelSize(size)
            self.font = font

    def reset(self):
        properties = chain(
            [p for p in self.properties if p.tag != 'frozen'],
            self.node_sizes.properties,
            self.fields.properties,
            self.scale.properties,
        )
        for property in properties:
            property.set(property.default)
        self.binder.update()
