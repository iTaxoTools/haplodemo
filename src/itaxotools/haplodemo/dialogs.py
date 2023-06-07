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

from .items import EdgeStyle
from .widgets import GLineEdit, RadioButtonGroup


class OptionsDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(self.windowFlags() | QtCore.Qt.MSWindowsFixedSizeDialogHint)
        self.binder = Binder()

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
        self.apply()
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
        self.resize(280, 0)

        self.scene = scene
        self.settings = EdgeStyleSettings()

        contents = self.draw_contents()
        self.draw_dialog(contents)

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
        self.scene.styleEdges(self.settings.style, self.settings.cutoff)


class NodeSizeSettings(PropertyObject):
    node_a = Property(float, None)
    node_b = Property(float, None)
    node_c = Property(float, None)
    node_d = Property(float, None)
    node_e = Property(float, None)
    node_f = Property(float, None)


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
            property = self.settings.properties[f'node_{x}']
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
        settings = self.settings
        self.scene.styleNodes(
            settings.node_a,
            settings.node_b,
            settings.node_c,
            settings.node_d,
            settings.node_e,
            settings.node_f,
        )
        self.push()


class LabelFormatSettings(PropertyObject):
    node_label_template = Property(str, None)
    edge_label_template = Property(str, None)


class LabelFormatDialog(BoundOptionsDialog):
    def __init__(self, parent, scene, global_settings):
        super().__init__(parent, LabelFormatSettings(), global_settings)
        self.setWindowTitle('Haplodemo - Label format')
        self.resize(340, 0)

        self.scene = scene

        contents = self.draw_contents()
        self.draw_dialog(contents)

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
        self.scene.styleLabels(
            settings.node_label_template,
            settings.edge_label_template,
        )
        self.push()
