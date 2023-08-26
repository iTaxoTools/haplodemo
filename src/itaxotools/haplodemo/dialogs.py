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

from itaxotools.common.bindings import Binder, Property, PropertyObject
from itaxotools.common.utility import AttrDict, type_convert

from .items.types import EdgeStyle
from .scene import NodeSizeSettings, ScaleSettings
from .widgets import GLineEdit, PenWidthField, PenWidthSlider, RadioButtonGroup


class OptionsDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            self.windowFlags() |
            QtCore.Qt.MSWindowsFixedSizeDialogHint |
            QtCore.Qt.WindowStaysOnTopHint)
        self.binder = Binder()

    def hintedResize(self, width, height):
        size = self.sizeHint()
        width = max(width, size.width())
        height = max(height, size.height())
        self.resize(width, height)

    def draw_dialog(self, contents):
        ok = QtWidgets.QPushButton('OK')
        cancel = QtWidgets.QPushButton('Cancel')
        apply = QtWidgets.QPushButton('Apply')

        ok.clicked.connect(self.accept)
        cancel.clicked.connect(self.reject)
        apply.clicked.connect(self.apply)

        cancel.setAutoDefault(True)

        buttons = QtWidgets.QHBoxLayout()
        buttons.addStretch(1)
        buttons.addWidget(ok)
        buttons.addWidget(cancel)
        buttons.addWidget(apply)

        layout = QtWidgets.QVBoxLayout()
        layout.addLayout(contents, 1)
        layout.addSpacing(8)
        layout.addLayout(buttons)
        self.setLayout(layout)

    def accept(self):
        super().accept()

    def apply(self):
        pass


class BoundOptionsDialog(OptionsDialog):
    def __init__(self, parent, settings, global_settings):
        super().__init__(parent)
        self.settings = settings
        self.global_settings = global_settings
        self.pull()

    def show(self):
        super().show()
        self.pull()

    def pull(self):
        for property in self.settings.properties:
            global_value = self.global_settings.properties[property.key].value
            property.set(global_value)

    def push(self):
        for property in self.settings.properties:
            self.global_settings.properties[property.key].set(property.value)


class EdgeStyleSettings(PropertyObject):
    style = Property(EdgeStyle, EdgeStyle.Bubbles)
    cutoff = Property(int, 3)


class EdgeStyleDialog(OptionsDialog):
    def __init__(self, parent, scene):
        super().__init__(parent)
        self.setWindowTitle('Haplodemo - Edge style')

        self.scene = scene
        self.settings = EdgeStyleSettings()

        contents = self.draw_contents()
        self.draw_dialog(contents)
        self.hintedResize(280, 60)

    def draw_contents(self):
        label_info = QtWidgets.QLabel('Massively style all edges. To set the style for individual edges instead, double click them.')
        label_info.setWordWrap(True)

        label_more_info = QtWidgets.QLabel('Edges with more segments than the cutoff value will be collapsed. Set it to zero to collapse no edges, or -1 to collapse all edges.')
        label_more_info.setWordWrap(True)

        label_style = QtWidgets.QLabel('Style:')
        bubbles = QtWidgets.QRadioButton('Bubbles')
        bars = QtWidgets.QRadioButton('Bars')
        plain = QtWidgets.QRadioButton('Plain')

        group = RadioButtonGroup()
        group.add(bubbles, EdgeStyle.Bubbles)
        group.add(bars, EdgeStyle.Bars)
        group.add(plain, EdgeStyle.Plain)

        label_cutoff = QtWidgets.QLabel('Cutoff:')
        cutoff = GLineEdit()
        cutoff.setTextMargins(2, 0, 2, 0)
        validator = QtGui.QIntValidator()
        cutoff.setValidator(validator)

        self.binder.bind(group.valueChanged, self.settings.properties.style)
        self.binder.bind(self.settings.properties.style, group.setValue)

        self.binder.bind(cutoff.textEditedSafe, self.settings.properties.cutoff, lambda x: type_convert(x, int, None))
        self.binder.bind(self.settings.properties.cutoff, cutoff.setText, lambda x: type_convert(x, str, ''))

        controls = QtWidgets.QGridLayout()
        controls.setContentsMargins(8, 8, 8, 8)
        controls.setColumnMinimumWidth(1, 8)
        controls.addWidget(label_style, 0, 0)
        controls.addWidget(bubbles, 0, 2)
        controls.addWidget(bars, 0, 3)
        controls.addWidget(plain, 0, 4)
        controls.addWidget(label_cutoff, 1, 0)
        controls.addWidget(cutoff, 1, 2, 1, 3)

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(label_info)
        layout.addLayout(controls, 1)
        layout.addWidget(label_more_info)
        return layout

    def show(self):
        for property in self.settings.properties:
            property.set(property.default)
        super().show()

    def accept(self):
        self.apply()
        super().accept()

    def apply(self):
        self.scene.style_edges(self.settings.style, self.settings.cutoff)


class NodeSizeDialog(BoundOptionsDialog):
    def __init__(self, parent, scene, global_settings):
        super().__init__(parent, NodeSizeSettings(), global_settings)
        self.setWindowTitle('Haplodemo - Node size')

        self.scene = scene

        contents = self.draw_contents()
        self.draw_dialog(contents)

    def draw_contents(self):
        label_info = QtWidgets.QLabel('Set node radius (r) from node weight (w) according to the following formula:')
        label_info.setWordWrap(True)

        dot = ' \u00B7 '
        sub = '<sub>b</sub>'
        formula = f'r = a{dot}log{sub}(c{dot}w+d) + e{dot}w + f'
        label_formula = QtWidgets.QLabel(formula)
        label_formula.setStyleSheet("padding: 4; font: 16px;")
        label_formula.setAlignment(QtCore.Qt.AlignCenter)

        labels = AttrDict()
        for x in ['a', 'b', 'c', 'd', 'e', 'f']:
            labels[x] = QtWidgets.QLabel(f'{x}:')

        fields = AttrDict()
        for x in ['a', 'b', 'c', 'd', 'e', 'f']:
            field = QtWidgets.QDoubleSpinBox()
            field.setMaximum(float('inf'))
            field.setSingleStep(1)
            field.setDecimals(2)
            property = self.settings.properties[x]
            self.binder.bind(field.valueChanged, property, lambda x: type_convert(x, float, None))
            self.binder.bind(property, field.setValue, lambda x: type_convert(x, float, 0))
            fields[x] = field

        fields.b.setMinimum(2)

        controls = QtWidgets.QGridLayout()
        controls.setContentsMargins(8, 8, 8, 8)
        controls.setColumnMinimumWidth(1, 8)
        controls.setColumnMinimumWidth(3, 8)
        controls.setColumnMinimumWidth(5, 8)
        controls.setColumnStretch(2, 1)
        controls.setColumnStretch(6, 1)

        controls.addWidget(labels.a, 0, 0)
        controls.addWidget(fields.a, 0, 2)
        controls.addWidget(labels.b, 0, 4)
        controls.addWidget(fields.b, 0, 6)

        controls.addWidget(labels.c, 1, 0)
        controls.addWidget(fields.c, 1, 2)
        controls.addWidget(labels.d, 1, 4)
        controls.addWidget(fields.d, 1, 6)

        controls.addWidget(labels.e, 2, 0)
        controls.addWidget(fields.e, 2, 2)
        controls.addWidget(labels.f, 2, 4)
        controls.addWidget(fields.f, 2, 6)

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(label_info, 1)
        layout.addWidget(label_formula, 0)
        layout.addLayout(controls, 1)
        return layout

    def apply(self):
        self.push()
        self.scene.style_nodes()


class LabelFormatSettings(PropertyObject):
    node_label_template = Property(str, None)
    edge_label_template = Property(str, None)


class LabelFormatDialog(BoundOptionsDialog):
    def __init__(self, parent, scene, global_settings):
        super().__init__(parent, LabelFormatSettings(), global_settings)
        self.setWindowTitle('Haplodemo - Label format')

        self.scene = scene

        contents = self.draw_contents()
        self.draw_dialog(contents)
        self.hintedResize(340, 0)

    def draw_contents(self):
        label_info = QtWidgets.QLabel('Set all labels from templates, where "NAME" and "WEIGHT" are replaced by the corresponding values.')
        label_info.setWordWrap(True)

        label_nodes = QtWidgets.QLabel('Nodes:')
        label_edges = QtWidgets.QLabel('Edges:')

        field_nodes = GLineEdit()
        field_edges = GLineEdit()

        field_nodes.setTextMargins(2, 0, 2, 0)
        field_edges.setTextMargins(2, 0, 2, 0)

        self.binder.bind(field_nodes.textEditedSafe, self.settings.properties.node_label_template)
        self.binder.bind(self.settings.properties.node_label_template, field_nodes.setText)

        self.binder.bind(field_edges.textEditedSafe, self.settings.properties.edge_label_template)
        self.binder.bind(self.settings.properties.edge_label_template, field_edges.setText)

        controls = QtWidgets.QGridLayout()
        controls.setContentsMargins(8, 8, 8, 8)
        controls.setColumnMinimumWidth(1, 8)
        controls.setColumnStretch(2, 1)

        controls.addWidget(label_nodes, 0, 0)
        controls.addWidget(field_nodes, 0, 2)

        controls.addWidget(label_edges, 1, 0)
        controls.addWidget(field_edges, 1, 2)

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(label_info, 1)
        layout.addLayout(controls, 1)
        return layout

    def apply(self):
        settings = self.settings
        self.scene.style_labels(
            settings.node_label_template,
            settings.edge_label_template,
        )
        self.push()


class ScaleMarksDialog(BoundOptionsDialog):
    def __init__(self, parent, scene, global_settings):
        super().__init__(parent, ScaleSettings(), global_settings)
        self.setWindowTitle('Haplodemo - Scale marks')

        self.scene = scene

        contents = self.draw_contents()
        self.draw_dialog(contents)
        self.hintedResize(360, 1)

    def draw_contents(self):
        label_info = QtWidgets.QLabel('Define what node sizes are marked on the scale in the form of a comma separated list.')
        label_info.setWordWrap(True)

        self.marks = GLineEdit()
        self.marks.setTextMargins(2, 0, 2, 0)

        self.auto = QtWidgets.QPushButton('Auto')

        self.binder.bind(self.marks.textEditedSafe, self.update_text_color)
        self.binder.bind(self.auto.clicked, self.get_auto_marks)

        controls = QtWidgets.QHBoxLayout()
        controls.addWidget(self.auto)
        controls.addWidget(self.marks, 1)
        controls.setSpacing(16)

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(label_info, 1)
        layout.addLayout(controls, 1)
        layout.setSpacing(16)
        return layout

    def show(self):
        super().show()
        text = self.get_text_from_marks(self.settings.marks)
        self.marks.setText(text)

    def update_text_color(self, text):
        try:
            self.get_marks_from_text(text)
        except Exception:
            color = 'red'
        else:
            color = 'black'
        self.marks.setStyleSheet(f"color: {color};")

    def get_auto_marks(self):
        marks = self.scene.get_marks_from_nodes()
        text = self.get_text_from_marks(marks)
        self.marks.setText(text)

    def get_text_from_marks(self, marks: list[int]) -> str:
        text = ', '.join(str(mark) for mark in marks)
        return text

    def get_marks_from_text(self, text: str) -> list[int]:
        marks = text.split(',')
        marks = [mark.strip() for mark in marks]
        marks = [int(mark) for mark in marks]
        return sorted(set(marks))

    def apply(self):
        try:
            text = self.marks.text()
            marks = self.get_marks_from_text(text)
        except Exception:
            return
        self.settings.marks = marks
        self.push()


class PenWidthSettings(PropertyObject):
    pen_width_nodes = Property(float, None)
    pen_width_edges = Property(float, None)


class PenWidthDialog(BoundOptionsDialog):
    def __init__(self, parent, scene, global_settings):
        super().__init__(parent, PenWidthSettings(), global_settings)
        self.setWindowTitle('Haplodemo - Pen width')

        self.scene = scene

        contents = self.draw_contents()
        self.draw_dialog(contents)
        self.hintedResize(480, 190)

    def draw_contents(self):
        label_info = QtWidgets.QLabel('Set the pen width for drawing node outlines and edges:')
        label_info.setWordWrap(True)

        label_nodes = QtWidgets.QLabel('Nodes:')
        label_edges = QtWidgets.QLabel('Edges:')

        slide_nodes = PenWidthSlider()
        slide_edges = PenWidthSlider()

        field_nodes = PenWidthField()
        field_edges = PenWidthField()

        self.binder.bind(slide_nodes.valueChanged, self.settings.properties.pen_width_nodes, lambda x: x / 10)
        self.binder.bind(self.settings.properties.pen_width_nodes, slide_nodes.setValue, lambda x: x * 10)

        self.binder.bind(slide_edges.valueChanged, self.settings.properties.pen_width_edges, lambda x: x / 10)
        self.binder.bind(self.settings.properties.pen_width_edges, slide_edges.setValue, lambda x: x * 10)

        self.binder.bind(field_nodes.valueChanged, self.settings.properties.pen_width_nodes)
        self.binder.bind(self.settings.properties.pen_width_nodes, field_nodes.setValue)

        self.binder.bind(field_edges.valueChanged, self.settings.properties.pen_width_edges)
        self.binder.bind(self.settings.properties.pen_width_edges, field_edges.setValue)

        controls = QtWidgets.QGridLayout()
        controls.setContentsMargins(8, 8, 8, 8)
        controls.setColumnMinimumWidth(2, 8)
        controls.setColumnStretch(1, 1)

        controls.addWidget(label_nodes, 0, 0)
        controls.addWidget(slide_nodes, 0, 1)
        controls.addWidget(field_nodes, 0, 2)

        controls.addWidget(label_edges, 1, 0)
        controls.addWidget(slide_edges, 1, 1)
        controls.addWidget(field_edges, 1, 2)

        self.field_nodes = field_nodes
        self.field_edges = field_edges

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(label_info, 1)
        layout.addSpacing(8)
        layout.addLayout(controls, 1)
        return layout

    def apply(self):
        self.field_nodes.setValue(self.settings.pen_width_nodes)
        self.field_edges.setValue(self.settings.pen_width_edges)
        self.push()


class FontDialog(QtWidgets.QFontDialog):
    """Get pixel sized fonts, which are required for rendering properly"""

    def __init__(self, parent, settings):
        super().__init__(parent)
        self.settings = settings
        self.setWindowTitle('Select font')
        self.setOptions(QtWidgets.QFontDialog.FontDialogOptions.DontUseNativeDialog)

    def exec(self):
        font = QtGui.QFont(self.settings.font)
        if font.pointSize() == -1:
            size = font.pixelSize()
            font.setPointSize(size)
        self.setCurrentFont(font)
        super().exec()

    def done(self, result):
        super().done(result)
        font = self.selectedFont()
        if font.pixelSize() == -1:
            size = font.pointSize()
            font.setPixelSize(size)
        self.settings.font = QtGui.QFont(font)


class EdgeLengthDialog(OptionsDialog):
    def __init__(self, parent, scene, settings):
        super().__init__(parent)
        self.setWindowTitle('Haplodemo - Edge length')

        self.scene = scene
        self.settings = settings
        self.dirty = True

        contents = self.draw_contents()
        self.draw_dialog(contents)
        self.hintedResize(320, 40)

    def draw_contents(self):
        label_info = QtWidgets.QLabel('Massively set the length for all edges, based on the number of mutations between nodes.')
        label_info.setWordWrap(True)

        label_more_info = QtWidgets.QLabel('Length is measured edge-to-edge, not center-to-center.')
        label_more_info.setWordWrap(True)

        label = QtWidgets.QLabel('Length per mutation:')

        length = QtWidgets.QDoubleSpinBox()
        length.setMinimum(0)
        length.setMaximum(float('inf'))
        length.setSingleStep(10)
        length.setDecimals(2)

        length.valueChanged.connect(self.set_dirty)

        controls = QtWidgets.QHBoxLayout()
        controls.setContentsMargins(8, 8, 8, 8)
        controls.setSpacing(16)
        controls.addWidget(label)
        controls.addWidget(length, 1)

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(label_info)
        layout.addSpacing(4)
        layout.addLayout(controls, 1)
        layout.addWidget(label_more_info)

        self.length = length

        return layout

    def set_dirty(self):
        self.dirty = True

    def show(self):
        self.length.setValue(self.settings.edge_length)
        self.dirty = True
        super().show()

    def accept(self):
        if self.dirty:
            self.apply()
        super().accept()

    def apply(self):
        length = self.length.value()
        self.scene.resize_edges(length)
        self.dirty = False
