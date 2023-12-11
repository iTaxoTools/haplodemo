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

from itaxotools.common.types import Type


class Palette(list, Type):
    label = "Palette"
    default = "gray"
    highlight = "#8aef52"
    colors = []

    def __init__(self):
        super().__init__(self.colors)

    def __getitem__(self, index):
        if index < len(self):
            return super().__getitem__(index)
        return self.default


class Set1(Palette):
    label = "Set1"
    default = "#999999"
    highlight = "#94f335"
    colors = [
        "#e41a1c",
        "#377eb8",
        "#4daf4a",
        "#984ea3",
        "#ff7f00",
        "#ffff33",
        "#a65628",
        "#f781bf",
    ]


class Spring(Palette):
    label = "Spring"
    default = "#bbbbbb"
    highlight = "#d3f789"
    colors = [
        "#fd7f6f",
        "#7eb0d5",
        "#b2e061",
        "#bd7ebe",
        "#ffb55a",
        "#ffee65",
        "#beb9db",
        "#fdcce5",
        "#8bd3c7",
    ]


class Pastel(Palette):
    label = "Pastel"
    default = "#e2e2e2"
    highlight = "#cefbc1"
    colors = [
        "#fbb4ae",
        "#b3cde3",
        "#ccebc5",
        "#decbe4",
        "#fed9a6",
        "#ffffcc",
        "#e5d8bd",
        "#fddaec",
    ]


class Tab10(Palette):
    label = "Tab10"
    default = "#c7c7c7"
    highlight = "#6bcf58"
    colors = [
        "#1f77b4",
        "#ff7f0e",
        "#2ca02c",
        "#d62728",
        "#9467bd",
        "#8c564b",
        "#e377c2",
        "#7f7f7f",
        "#bcbd22",
        "#17becf",
    ]


class RetroMetro(Palette):
    label = "RetroMetro"
    default = "#979797"
    highlight = "#a5d657"
    colors = [
        "#ea5545",
        "#f46a9b",
        "#ef9b20",
        "#edbf33",
        "#ede15b",
        "#bdcf32",
        "#87bc45",
        "#27aeef",
        "#b33dc6",
    ]


class Spectrum(Palette):
    label = "Spectrum"
    default = "#858585"
    highlight = "#bce931"
    colors = [
        "#0fb5ae",
        "#4046ca",
        "#f68511",
        "#de3d82",
        "#7e84fa",
        "#72e06a",
        "#147af3",
        "#7326d3",
        "#e8c600",
        "#cb5d00",
        "#008f5d",
        "#bce931",
    ]


class Grayscale(Palette):
    label = "Grayscale"
    default = "#070707"
    highlight = "#bcbcbc"
    colors = [
        "#252525",
        "#cccccc",
        "#636363",
        "#f7f7f7",
        "#969696",
    ]
