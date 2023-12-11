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
from math import log, sqrt

from itaxotools.common.bindings import Binder, Instance, Property, PropertyObject
from itaxotools.haplodemo.models import (
    DivisionListModel,
    MemberTreeModel,
    PartitionListModel,
)
from itaxotools.haplodemo.palettes import Palette
from itaxotools.haplodemo.types import LayoutType


def get_default_font():
    font = QtGui.QFont("Arial")
    font.setPixelSize(14)
    return font


class NodeSizeSettings(PropertyObject):
    base_radius = Property(int, 20)
    linear_factor = Property(float, 1.0)
    area_factor = Property(float, 1.0)
    logarithmic_factor = Property(float, 1.0)
    logarithmic_base = Property(float, 10)

    has_base_radius = Property(bool, True)
    has_linear_factor = Property(bool, False)
    has_area_factor = Property(bool, False)
    has_logarithmic_factor = Property(bool, True)

    def radius_for_weight(self, weight: int) -> float:
        base = self.base_radius
        assert base > 0
        if self.has_linear_factor:
            return self.linear_factor * base * (weight - 1) + base
        elif self.has_area_factor:
            return base * sqrt(1 + self.area_factor * (weight - 1))
        elif self.has_logarithmic_factor:
            if weight == 0:
                return 0
            if self.logarithmic_base > 0:
                return (
                    self.logarithmic_factor * base * log(weight, self.logarithmic_base)
                    + base
                )
        return base

    def get_all_values(self):
        return [property.value for property in self.properties]

    def set_all_values(self, base: int, linear: float, area: float, log: float):
        self.base_radius = base
        self.linear_factor = linear
        self.area_factor = area
        self.logarithmic_factor = log
        self.logarithmic_base = 10

        self.has_linear_factor = bool(linear)
        self.has_area_factor = bool(area)
        self.has_logarithmic_factor = bool(log)


class ScaleSettings(PropertyObject):
    marks = Property(list, [5, 10, 20])


class FieldSettings(PropertyObject):
    show_groups = Property(bool, True)
    show_isolated = Property(bool, True)


class Settings(PropertyObject):
    partitions = Property(PartitionListModel, Instance, tag="frozen")
    divisions = Property(DivisionListModel, Instance, tag="frozen")
    members = Property(MemberTreeModel, Instance, tag="frozen")

    node_sizes = Property(NodeSizeSettings, Instance, tag="frozen")
    fields = Property(FieldSettings, Instance, tag="frozen")
    scale = Property(ScaleSettings, Instance, tag="frozen")

    partition_index = Property(QtCore.QModelIndex, Instance)

    palette = Property(Palette, Palette.Spring())
    highlight_color = Property(QtGui.QColor, QtCore.Qt.magenta)

    font = Property(QtGui.QFont, get_default_font())
    snapping_movement = Property(bool, True)
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

    node_label_template = Property(str, "NAME")
    edge_label_template = Property(str, "(WEIGHT)")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.binder = Binder()
        self.binder.bind(self.properties.palette, self.divisions.set_palette)
        self.binder.bind(
            self.properties.palette,
            self.properties.highlight_color,
            lambda x: x.highlight,
        )
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
            [p for p in self.properties if p.tag != "frozen"],
            self.node_sizes.properties,
            self.fields.properties,
            self.scale.properties,
        )
        for property in properties:
            property.set(property.default)
        self.binder.update()
