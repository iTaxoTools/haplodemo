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

from enum import Enum, auto


class EdgeDecoration(Enum):
    Bubbles = auto()
    Bars = auto()
    DoubleStrike = auto()


class EdgeStyle(Enum):
    Bubbles = "Bubbles", EdgeDecoration.Bubbles, False, False, None
    Bars = "Bars", EdgeDecoration.Bars, False, False, None
    Collapsed = "Collapsed", EdgeDecoration.DoubleStrike, False, True, 16
    PlainWithText = "Plain with text", None, False, True, None
    DotsWithText = "Dots with text", None, True, True, None
    Plain = "Plain", None, False, False, None
    Dots = "Dots", None, True, False, None

    def __new__(cls, name, decoration, has_dots, has_text, text_offset):
        value = len(cls.__members__) + 1
        obj = object.__new__(cls)
        obj._value_ = value
        obj.label = name
        obj.decoration = decoration
        obj.has_dots = has_dots
        obj.has_text = has_text
        obj.text_offset = text_offset

        members = list(cls.__members__.values())
        if members:
            members[-1].next = obj
            obj.next = members[0]

        return obj

    def __repr__(self):
        cls_name = self.__class__.__name__
        return f"{cls_name}.{self._name_}"

    def __str__(self):
        return self.label


class Direction(Enum):
    Center = auto()
    Left = auto()
    Right = auto()
    Top = auto()
    Bottom = auto()
