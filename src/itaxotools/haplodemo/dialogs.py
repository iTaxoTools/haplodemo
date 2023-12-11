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

from PySide6 import QtCore, QtGui, QtWidgets

from itaxotools.common.bindings import Binder, Property, PropertyObject
from itaxotools.common.utility import AttrDict, type_convert

from .history import (
    ApplyCommand,
    EdgeStyleCommand,
    NodeMovementCommand,
    PropertyChangedCommand,
    PropertyGroupCommand,
    UndoCommand,
)
from .items.edges import Edge
from .items.nodes import Vertex
from .items.types import EdgeStyle
from .settings import NodeSizeSettings, ScaleSettings
from .widgets import (
    ClickableDoubleSpinBox,
    ClickableSpinBox,
    GLineEdit,
    PenWidthField,
    PenWidthSlider,
    RadioButtonGroup,
)


class OptionsDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            self.windowFlags()
            | QtCore.Qt.MSWindowsFixedSizeDialogHint
            | QtCore.Qt.WindowStaysOnTopHint
        )
        self.binder = Binder()

    def hintedResize(self, width, height):
        size = self.sizeHint()
        width = max(width, size.width())
        height = max(height, size.height())
        self.resize(width, height)

    def draw_dialog(self, contents):
        ok = QtWidgets.QPushButton("OK")
        cancel = QtWidgets.QPushButton("Cancel")
        apply = QtWidgets.QPushButton("Apply")

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
    def __init__(
        self, parent, settings: PropertyObject, global_settings: PropertyObject
    ):
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

    def accept(self):
        self.apply()
        super().accept()


class BoundOptionsDialogWithHistory(BoundOptionsDialog):
    commandPosted = QtCore.Signal(QtGui.QUndoCommand)
    command_text = "Property group change"

    def __init__(self, parent, settings, global_settings):
        super().__init__(parent, settings, global_settings)

    def push(self):
        if self.did_properties_change():
            command = self.undo_command()
            self.commandPosted.emit(command)
        super().push()

    def undo_command(self) -> UndoCommand:
        command = PropertyGroupCommand(self.command_text)
        self.add_subcommands(command)
        return command

    def add_subcommands(self, command: UndoCommand):
        for property in self.settings.properties:
            global_property = self.global_settings.properties[property.key]
            old_value = global_property.value
            new_value = property.value
            PropertyChangedCommand(global_property, old_value, new_value, command)

    def did_properties_change(self) -> bool:
        for property in self.settings.properties:
            global_property = self.global_settings.properties[property.key]
            old_value = global_property.value
            new_value = property.value
            if old_value != new_value:
                return True
        return False


class EdgeStyleSettings(PropertyObject):
    style = Property(EdgeStyle, EdgeStyle.Bubbles)
    cutoff = Property(int, 3)


class EdgeStyleDialog(OptionsDialog):
    commandPosted = QtCore.Signal(QtGui.QUndoCommand)

    def __init__(self, parent, scene):
        super().__init__(parent)
        self.setWindowTitle("Haplodemo - Edge style")

        self.scene = scene
        self.settings = EdgeStyleSettings()
        self.dirty = True

        contents = self.draw_contents()
        self.draw_dialog(contents)
        self.hintedResize(280, 60)

    def draw_contents(self):
        label_info = QtWidgets.QLabel(
            "Massively style all edges. To set the style for individual edges instead, double click them."
        )
        label_info.setWordWrap(True)

        label_more_info = QtWidgets.QLabel(
            "Edges with more segments than the cutoff value will be collapsed. Set it to zero to collapse no edges, or -1 to collapse all edges."
        )
        label_more_info.setWordWrap(True)

        label_style = QtWidgets.QLabel("Style:")
        bubbles = QtWidgets.QRadioButton("Bubbles")
        bars = QtWidgets.QRadioButton("Bars")
        plain = QtWidgets.QRadioButton("Plain")

        group = RadioButtonGroup()
        group.add(bubbles, EdgeStyle.Bubbles)
        group.add(bars, EdgeStyle.Bars)
        group.add(plain, EdgeStyle.Plain)

        label_cutoff = QtWidgets.QLabel("Cutoff:")
        cutoff = GLineEdit()
        cutoff.setTextMargins(2, 0, 2, 0)
        validator = QtGui.QIntValidator()
        cutoff.setValidator(validator)

        self.binder.bind(group.valueChanged, self.settings.properties.style)
        self.binder.bind(self.settings.properties.style, group.setValue)

        self.binder.bind(
            cutoff.textEditedSafe,
            self.settings.properties.cutoff,
            lambda x: type_convert(x, int, None),
        )
        self.binder.bind(
            self.settings.properties.cutoff,
            cutoff.setText,
            lambda x: type_convert(x, str, ""),
        )

        group.valueChanged.connect(self.set_dirty)
        cutoff.textEditedSafe.connect(self.set_dirty)

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

    def set_dirty(self):
        self.dirty = True

    def show(self):
        for property in self.settings.properties:
            property.set(property.default)
        self.dirty = True
        super().show()

    def accept(self):
        self.apply()
        super().accept()

    def apply(self):
        if not self.dirty:
            return
        self.dirty = False

        self.scene.style_edges(self.settings.style, self.settings.cutoff)

        command = UndoCommand()
        command.setText("Style edges")
        for edge in (item for item in self.scene.items() if isinstance(item, Edge)):
            EdgeStyleCommand(edge, command)
        self.commandPosted.emit(command)


class NodeSizeDialog(BoundOptionsDialogWithHistory):
    def __init__(self, parent, scene, global_settings):
        super().__init__(parent, NodeSizeSettings(), global_settings)
        self.setWindowTitle("Haplodemo - Node size")

        self.scene = scene

        contents = self.draw_contents()
        self.draw_dialog(contents)

    def draw_contents(self):
        properties = self.settings.properties

        label_info = QtWidgets.QLabel(
            "Resize nodes based on their individual weight, which corresponds to haplotype count. Node sizes are in pixels."
        )
        label_info.setWordWrap(True)

        radios = AttrDict()
        radios.linear_factor = QtWidgets.QRadioButton("Linear factor:")
        radios.area_factor = QtWidgets.QRadioButton("Area factor:")
        radios.logarithmic_factor = QtWidgets.QRadioButton("Log. factor:")

        style = QtWidgets.QApplication.style()
        indicator_width = style.pixelMetric(
            QtWidgets.QStyle.PM_ExclusiveIndicatorWidth, None, radios.linear_factor
        )
        indicator_spacing = style.pixelMetric(
            QtWidgets.QStyle.PM_RadioButtonLabelSpacing, None, radios.linear_factor
        )

        base_radius_pattern = QtWidgets.QLabel("\u2B9E")
        base_radius_pattern.setFixedWidth(indicator_width)
        font = base_radius_pattern.font()
        font.setPixelSize(14)
        font.setBold(True)
        font.setStyleStrategy(QtGui.QFont.PreferAntialias)
        font.setHintingPreference(QtGui.QFont.PreferNoHinting)
        base_radius_pattern.setFont(font)

        base_radius_label = QtWidgets.QLabel("Base radius:")

        base_radius_layout = QtWidgets.QHBoxLayout()
        base_radius_layout.setContentsMargins(0, 0, 0, 0)
        base_radius_layout.setSpacing(indicator_spacing)
        base_radius_layout.addWidget(base_radius_pattern)
        base_radius_layout.addWidget(base_radius_label)

        self.binder.bind(radios.linear_factor.toggled, properties.has_linear_factor)
        self.binder.bind(properties.has_linear_factor, radios.linear_factor.setChecked)

        self.binder.bind(radios.area_factor.toggled, properties.has_area_factor)
        self.binder.bind(properties.has_area_factor, radios.area_factor.setChecked)

        self.binder.bind(
            radios.logarithmic_factor.toggled, properties.has_logarithmic_factor
        )
        self.binder.bind(
            properties.has_logarithmic_factor, radios.logarithmic_factor.setChecked
        )

        fields = AttrDict()
        fields.linear_factor = self.create_float_box(properties.linear_factor)
        fields.area_factor = self.create_float_box(properties.area_factor)
        fields.logarithmic_factor = self.create_float_box(properties.logarithmic_factor)
        fields.base_radius = self.create_int_box(properties.base_radius)

        self.binder.bind(fields.linear_factor.clicked, properties.has_linear_factor)
        self.binder.bind(fields.area_factor.clicked, properties.has_area_factor)
        self.binder.bind(
            fields.logarithmic_factor.clicked, properties.has_logarithmic_factor
        )

        self.binder.bind(
            properties.has_linear_factor, fields.linear_factor.set_text_black
        )
        self.binder.bind(properties.has_area_factor, fields.area_factor.set_text_black)
        self.binder.bind(
            properties.has_logarithmic_factor, fields.logarithmic_factor.set_text_black
        )
        self.binder.bind(properties.has_base_radius, fields.base_radius.set_text_black)

        descrs = AttrDict()
        descrs.linear_factor = QtWidgets.QLabel(
            "Proportional radius growth with weight."
        )
        descrs.area_factor = QtWidgets.QLabel("Proportional area growth with weight.")
        descrs.logarithmic_factor = QtWidgets.QLabel(
            "Logarithmic radius growth (base 10)."
        )
        descrs.base_radius = QtWidgets.QLabel("Node radius when weight is 1.")

        for descr in descrs.values():
            font = descr.font()
            font.setItalic(True)
            descr.setFont(font)

        controls = QtWidgets.QGridLayout()
        controls.setContentsMargins(16, 16, 16, 8)
        controls.setColumnMinimumWidth(1, 8)
        controls.setColumnMinimumWidth(2, 60)
        controls.setColumnMinimumWidth(3, 8)
        controls.setColumnStretch(4, 1)

        row = 0
        controls.addWidget(radios.linear_factor, row, 0)
        controls.addWidget(fields.linear_factor, row, 2)
        controls.addWidget(descrs.linear_factor, row, 4)

        row += 1
        controls.addWidget(radios.area_factor, row, 0)
        controls.addWidget(fields.area_factor, row, 2)
        controls.addWidget(descrs.area_factor, row, 4)

        row += 1
        controls.addWidget(radios.logarithmic_factor, row, 0)
        controls.addWidget(fields.logarithmic_factor, row, 2)
        controls.addWidget(descrs.logarithmic_factor, row, 4)

        row += 1
        controls.setRowMinimumHeight(row, 16)

        row += 1
        controls.addLayout(base_radius_layout, row, 0)
        controls.addWidget(fields.base_radius, row, 2)
        controls.addWidget(descrs.base_radius, row, 4)

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(label_info, 1)
        layout.addLayout(controls, 1)
        return layout

    def create_int_box(self, property: Property) -> ClickableSpinBox:
        box = ClickableSpinBox()
        box.setMinimum(5)
        box.setMaximum(100000)
        box.setSingleStep(5)
        self.binder.bind(
            box.valueChanged, property, lambda x: type_convert(x, int, None)
        )
        self.binder.bind(property, box.setValue, lambda x: type_convert(x, int, 0))
        return box

    def create_float_box(self, property: Property) -> ClickableDoubleSpinBox:
        box = ClickableDoubleSpinBox()
        box.setMinimum(0)
        box.setMaximum(float("inf"))
        box.setSingleStep(0.1)
        box.setDecimals(2)
        self.binder.bind(
            box.valueChanged, property, lambda x: type_convert(x, float, None)
        )
        self.binder.bind(property, box.setValue, lambda x: type_convert(x, float, 0))
        return box

    def pull(self):
        super().pull()
        self.settings.logarithmic_base = 10

    def apply(self):
        self.push()
        self.scene.style_nodes()

    def undo_command(self) -> UndoCommand:
        command = ApplyCommand(self.command_text, self.scene.style_nodes)
        self.add_subcommands(command)
        return command


class LabelFormatSettings(PropertyObject):
    node_label_template = Property(str, None)
    edge_label_template = Property(str, None)


class LabelFormatDialog(BoundOptionsDialogWithHistory):
    def __init__(self, parent, scene, global_settings):
        super().__init__(parent, LabelFormatSettings(), global_settings)
        self.setWindowTitle("Haplodemo - Label format")

        self.scene = scene

        contents = self.draw_contents()
        self.draw_dialog(contents)
        self.hintedResize(340, 0)

    def draw_contents(self):
        label_info = QtWidgets.QLabel(
            'Set all labels from templates, where "NAME" and "WEIGHT" are replaced by the corresponding values.'
        )
        label_info.setWordWrap(True)

        label_nodes = QtWidgets.QLabel("Nodes:")
        label_edges = QtWidgets.QLabel("Edges:")

        field_nodes = GLineEdit()
        field_edges = GLineEdit()

        field_nodes.setTextMargins(2, 0, 2, 0)
        field_edges.setTextMargins(2, 0, 2, 0)

        self.binder.bind(
            field_nodes.textEditedSafe, self.settings.properties.node_label_template
        )
        self.binder.bind(
            self.settings.properties.node_label_template, field_nodes.setText
        )

        self.binder.bind(
            field_edges.textEditedSafe, self.settings.properties.edge_label_template
        )
        self.binder.bind(
            self.settings.properties.edge_label_template, field_edges.setText
        )

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
        self.push()
        self.scene.style_labels()

    def undo_command(self) -> UndoCommand:
        command = ApplyCommand(self.command_text, self.scene.style_labels)
        self.add_subcommands(command)
        return command


class ScaleMarksDialog(BoundOptionsDialogWithHistory):
    def __init__(self, parent, scene, global_settings):
        super().__init__(parent, ScaleSettings(), global_settings)
        self.setWindowTitle("Haplodemo - Scale marks")

        self.scene = scene

        contents = self.draw_contents()
        self.draw_dialog(contents)
        self.hintedResize(360, 1)

    def draw_contents(self):
        label_info = QtWidgets.QLabel(
            "Define what node sizes are marked on the scale in the form of a comma separated list."
        )
        label_info.setWordWrap(True)

        self.marks = GLineEdit()
        self.marks.setTextMargins(2, 0, 2, 0)

        self.auto = QtWidgets.QPushButton("Auto")

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
            color = "red"
        else:
            color = "black"
        self.marks.setStyleSheet(f"color: {color};")

    def get_auto_marks(self):
        marks = self.scene.get_marks_from_nodes()
        text = self.get_text_from_marks(marks)
        self.marks.setText(text)

    def get_text_from_marks(self, marks: list[int]) -> str:
        text = ", ".join(str(mark) for mark in marks)
        return text

    def get_marks_from_text(self, text: str) -> list[int]:
        marks = text.split(",")
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


class PenWidthDialog(BoundOptionsDialogWithHistory):
    def __init__(self, parent, scene, global_settings):
        super().__init__(parent, PenWidthSettings(), global_settings)
        self.setWindowTitle("Haplodemo - Pen width")

        self.scene = scene

        contents = self.draw_contents()
        self.draw_dialog(contents)
        self.hintedResize(480, 190)

    def draw_contents(self):
        label_info = QtWidgets.QLabel(
            "Set the pen width for drawing node outlines and edges:"
        )
        label_info.setWordWrap(True)

        label_nodes = QtWidgets.QLabel("Nodes:")
        label_edges = QtWidgets.QLabel("Edges:")

        slide_nodes = PenWidthSlider()
        slide_edges = PenWidthSlider()

        field_nodes = PenWidthField()
        field_edges = PenWidthField()

        self.binder.bind(
            slide_nodes.valueChanged,
            self.settings.properties.pen_width_nodes,
            lambda x: x / 10,
        )
        self.binder.bind(
            self.settings.properties.pen_width_nodes,
            slide_nodes.setValue,
            lambda x: x * 10,
        )

        self.binder.bind(
            slide_edges.valueChanged,
            self.settings.properties.pen_width_edges,
            lambda x: x / 10,
        )
        self.binder.bind(
            self.settings.properties.pen_width_edges,
            slide_edges.setValue,
            lambda x: x * 10,
        )

        self.binder.bind(
            field_nodes.valueChanged, self.settings.properties.pen_width_nodes
        )
        self.binder.bind(self.settings.properties.pen_width_nodes, field_nodes.setValue)

        self.binder.bind(
            field_edges.valueChanged, self.settings.properties.pen_width_edges
        )
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

    commandPosted = QtCore.Signal(QtGui.QUndoCommand)

    def __init__(self, parent, settings: PropertyObject):
        super().__init__(parent)
        self.settings = settings
        self.setWindowTitle("Select font")
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

        old_value = QtGui.QFont(self.settings.font)
        new_value = QtGui.QFont(font)
        command = PropertyChangedCommand(
            self.settings.properties.font, old_value, new_value
        )
        self.commandPosted.emit(command)

        self.settings.font = QtGui.QFont(font)


class EdgeLengthDialog(OptionsDialog):
    commandPosted = QtCore.Signal(QtGui.QUndoCommand)

    def __init__(self, parent, scene, settings: PropertyObject):
        super().__init__(parent)
        self.setWindowTitle("Haplodemo - Edge length")

        self.scene = scene
        self.settings = settings
        self.dirty = True

        contents = self.draw_contents()
        self.draw_dialog(contents)
        self.hintedResize(320, 40)

    def draw_contents(self):
        label_info = QtWidgets.QLabel(
            "Massively set the length for all edges, based on the number of mutations between nodes."
        )
        label_info.setWordWrap(True)

        label_more_info = QtWidgets.QLabel(
            "Length is measured edge-to-edge, not center-to-center."
        )
        label_more_info.setWordWrap(True)

        label = QtWidgets.QLabel("Length per mutation:")

        length = QtWidgets.QDoubleSpinBox()
        length.setMinimum(0)
        length.setMaximum(float("inf"))
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
        self.apply()
        super().accept()

    def apply(self):
        if not self.dirty:
            return
        self.dirty = False

        length = self.length.value()

        property = self.settings.properties.edge_length
        command = PropertyChangedCommand(property, property.value, length)

        self.scene.resize_edges(length)
        self.settings.edge_length = length

        for node in (item for item in self.scene.items() if isinstance(item, Vertex)):
            NodeMovementCommand(node, recurse=False, parent=command)
        self.commandPosted.emit(command)
