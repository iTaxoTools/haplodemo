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

from itaxotools.common.bindings import Binder
from itaxotools.common.utility import AttrDict
from itaxotools.common.widgets import HLineSeparator

from .demos import DemoLoader
from .dialogs import (
    EdgeLengthDialog,
    EdgeStyleDialog,
    FontDialog,
    LabelFormatDialog,
    NodeSizeDialog,
    PenWidthDialog,
    ScaleMarksDialog,
)
from .history import UndoCommand, UndoStack
from .scene import GraphicsScene, GraphicsView
from .settings import Settings
from .views import ColorDelegate, DivisionView, MemberView
from .visualizer import Visualizer
from .widgets import PaletteSelector, PartitionSelector, ToggleButton
from .zoom import ZoomControl


class Window(QtWidgets.QWidget):
    def __init__(self, opengl=False):
        super().__init__()
        self.setWindowFlags(QtCore.Qt.Window)
        self.resize(960, 520)
        self.setWindowTitle("Haplodemo")

        settings = Settings()

        scene = GraphicsScene(settings)
        visualizer = Visualizer(scene, settings)

        scene_view = GraphicsView(scene, opengl)

        partition_selector = PartitionSelector(settings.partitions)

        palette_selector = PaletteSelector()

        history_stack = UndoStack()
        self.actions = AttrDict()
        self.actions.undo = history_stack.createUndoAction(self, "&Undo")
        self.actions.undo.setShortcut(QtGui.QKeySequence.Undo)
        self.actions.redo = history_stack.createRedoAction(self, "&Redo")
        self.actions.redo.setShortcut(QtGui.QKeySequence.Redo)
        for action in self.actions:
            self.addAction(action)

        undo_button = QtWidgets.QPushButton("Undo")
        undo_button.clicked.connect(history_stack.undo)
        history_stack.canUndoChanged.connect(undo_button.setEnabled)
        undo_button.setEnabled(history_stack.canUndo())

        redo_button = QtWidgets.QPushButton("Redo")
        redo_button.clicked.connect(history_stack.redo)
        history_stack.canRedoChanged.connect(redo_button.setEnabled)
        redo_button.setEnabled(history_stack.canRedo())

        self.node_size_dialog = NodeSizeDialog(self, scene, settings.node_sizes)
        self.edge_style_dialog = EdgeStyleDialog(self, scene)
        self.edge_length_dialog = EdgeLengthDialog(self, scene, settings)
        self.scale_style_dialog = ScaleMarksDialog(self, scene, settings.scale)
        self.pen_style_dialog = PenWidthDialog(self, scene, settings)
        self.label_format_dialog = LabelFormatDialog(self, scene, settings)
        self.font_dialog = FontDialog(self, settings)

        self.demos = DemoLoader(scene, settings, visualizer)

        button_demo_simple = QtWidgets.QPushButton("Load simple demo")
        button_demo_simple.clicked.connect(lambda: self.demos.load_demo_simple())

        button_demo_fields = QtWidgets.QPushButton("Load FOR demo")
        button_demo_fields.clicked.connect(lambda: self.demos.load_demo_fields())

        button_demo_tiny_tree = QtWidgets.QPushButton("Load tiny tree")
        button_demo_tiny_tree.clicked.connect(lambda: self.demos.load_demo_tiny_tree())

        button_demo_long_tree = QtWidgets.QPushButton("Load long tree")
        button_demo_long_tree.clicked.connect(lambda: self.demos.load_demo_long_tree())

        button_demo_heavy_tree = QtWidgets.QPushButton("Load heavy tree")
        button_demo_heavy_tree.clicked.connect(
            lambda: self.demos.load_demo_heavy_tree()
        )

        button_demo_cycled_graph = QtWidgets.QPushButton("Load cycled graph")
        button_demo_cycled_graph.clicked.connect(
            lambda: self.demos.load_demo_cycled_graph()
        )

        button_demo_members_tree = QtWidgets.QPushButton("Load members tree")
        button_demo_members_tree.clicked.connect(
            lambda: self.demos.load_demo_members_tree()
        )

        button_demo_many = QtWidgets.QPushButton("Test performance")
        button_demo_many.clicked.connect(lambda: self.demos.load_demo_many())
        button_demo_many.setStyleSheet("color: #A00;")

        button_svg = QtWidgets.QPushButton("Export as SVG")
        button_svg.clicked.connect(lambda: self.export_svg())

        button_pdf = QtWidgets.QPushButton("Export as PDF")
        button_pdf.clicked.connect(lambda: self.export_pdf())

        button_png = QtWidgets.QPushButton("Export as PNG")
        button_png.clicked.connect(lambda: self.export_png())

        mass_resize_nodes = QtWidgets.QPushButton("Set node size")
        mass_resize_nodes.clicked.connect(self.node_size_dialog.show)

        mass_resize_edges = QtWidgets.QPushButton("Set edge length")
        mass_resize_edges.clicked.connect(self.edge_length_dialog.show)

        mass_style_edges = QtWidgets.QPushButton("Set edge style")
        mass_style_edges.clicked.connect(self.edge_style_dialog.show)

        style_pens = QtWidgets.QPushButton("Set pen width")
        style_pens.clicked.connect(self.pen_style_dialog.show)

        style_scale = QtWidgets.QPushButton("Set scale marks")
        style_scale.clicked.connect(self.scale_style_dialog.show)

        mass_format_labels = QtWidgets.QPushButton("Set label format")
        mass_format_labels.clicked.connect(self.label_format_dialog.show)

        select_font = QtWidgets.QPushButton("Set font")
        select_font.clicked.connect(self.font_dialog.exec)

        toggle_snapping = ToggleButton("Enable snapping")
        toggle_rotation = ToggleButton("Rotate nodes")
        toggle_recursive = ToggleButton("Move children")
        toggle_labels = ToggleButton("Lock labels")
        toggle_legend = ToggleButton("Show legend")
        toggle_scale = ToggleButton("Show scale")
        toggle_field_groups = ToggleButton("Show groups")
        toggle_field_isolated = ToggleButton("Show isolated")
        toggle_scene_rotation = ToggleButton("Rotate scene")

        division_view = DivisionView(settings.divisions)
        member_view = MemberView(settings.members)

        exports = QtWidgets.QVBoxLayout()
        exports.addWidget(button_svg)
        exports.addWidget(button_pdf)
        exports.addWidget(button_png)

        demos = QtWidgets.QVBoxLayout()
        demos.addWidget(button_demo_simple)
        demos.addWidget(button_demo_fields)
        demos.addWidget(button_demo_tiny_tree)
        demos.addWidget(button_demo_long_tree)
        demos.addWidget(button_demo_heavy_tree)
        demos.addWidget(button_demo_cycled_graph)
        demos.addWidget(button_demo_members_tree)
        demos.addWidget(button_demo_many)

        toggles = QtWidgets.QVBoxLayout()
        toggles.addWidget(toggle_scene_rotation)
        toggles.addWidget(toggle_legend)
        toggles.addWidget(toggle_scale)
        toggles.addSpacing(4)
        toggles.addWidget(HLineSeparator(1))
        toggles.addSpacing(4)
        toggles.addWidget(toggle_field_groups)
        toggles.addWidget(toggle_field_isolated)
        toggles.addSpacing(4)
        toggles.addWidget(HLineSeparator(1))
        toggles.addSpacing(4)
        toggles.addWidget(toggle_snapping)
        toggles.addWidget(toggle_rotation)
        toggles.addWidget(toggle_recursive)
        toggles.addWidget(toggle_labels)

        dialogs = QtWidgets.QVBoxLayout()
        dialogs.addWidget(mass_resize_nodes)
        dialogs.addWidget(mass_resize_edges)
        dialogs.addWidget(mass_style_edges)
        dialogs.addWidget(style_pens)
        dialogs.addWidget(style_scale)
        dialogs.addWidget(mass_format_labels)
        dialogs.addWidget(select_font)

        history = QtWidgets.QVBoxLayout()
        history.addWidget(undo_button)
        history.addWidget(redo_button)

        left_layout = QtWidgets.QVBoxLayout()
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.addLayout(demos)
        left_layout.addSpacing(4)
        left_layout.addWidget(HLineSeparator(1))
        left_layout.addSpacing(4)
        left_layout.addLayout(exports)
        left_layout.addSpacing(4)
        left_layout.addWidget(HLineSeparator(1))
        left_layout.addSpacing(4)
        left_layout.addStretch(1)
        left_layout.addSpacing(4)
        left_layout.addWidget(HLineSeparator(1))
        left_layout.addSpacing(4)
        left_layout.addLayout(toggles)

        right_layout = QtWidgets.QVBoxLayout()
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.addLayout(dialogs)
        right_layout.addSpacing(4)
        right_layout.addWidget(HLineSeparator(1))
        right_layout.addSpacing(4)
        right_layout.addLayout(history)
        right_layout.addSpacing(4)
        right_layout.addWidget(HLineSeparator(1))
        right_layout.addSpacing(4)
        right_layout.addWidget(partition_selector)
        right_layout.addWidget(palette_selector)
        right_layout.addWidget(division_view, 1)
        right_layout.addWidget(member_view, 3)

        left_sidebar = QtWidgets.QWidget()
        left_sidebar.setLayout(left_layout)
        left_sidebar.setFixedWidth(160)

        right_sidebar = QtWidgets.QWidget()
        right_sidebar.setLayout(right_layout)
        right_sidebar.setFixedWidth(160)

        layout = QtWidgets.QHBoxLayout()
        layout.addWidget(left_sidebar)
        layout.addWidget(scene_view, 1)
        layout.addWidget(right_sidebar)
        self.setLayout(layout)

        zoom_control = ZoomControl(scene_view, self)

        self.scene = scene
        self.scene_view = scene_view
        self.zoom_control = zoom_control
        self.settings = settings

        self.binder = Binder()

        self.binder.bind(
            settings.partitions.partitionsChanged,
            partition_selector.setVisible,
            lambda partitions: len(partitions) > 0,
        )
        self.binder.bind(
            partition_selector.modelIndexChanged, settings.properties.partition_index
        )
        self.binder.bind(
            settings.properties.partition_index, partition_selector.setModelIndex
        )

        self.binder.bind(
            palette_selector.currentValueChanged, settings.properties.palette
        )
        self.binder.bind(settings.properties.palette, palette_selector.setValue)
        self.binder.bind(settings.properties.palette, ColorDelegate.setCustomColors)

        self.binder.bind(visualizer.nodeIndexSelected, member_view.select)
        self.binder.bind(member_view.nodeSelected, visualizer.select_node_by_name)

        self.binder.bind(scene.commandPosted, history_stack.push)
        self.binder.bind(scene.cleared, UndoCommand.clear_history)
        self.binder.bind(scene.cleared, history_stack.clear)

        self.binder.bind(
            settings.properties.snapping_movement, toggle_snapping.setChecked
        )
        self.binder.bind(toggle_snapping.toggled, settings.properties.snapping_movement)

        self.binder.bind(
            settings.properties.rotational_movement, toggle_rotation.setChecked
        )
        self.binder.bind(
            toggle_rotation.toggled, settings.properties.rotational_movement
        )

        self.binder.bind(
            settings.properties.recursive_movement, toggle_recursive.setChecked
        )
        self.binder.bind(
            toggle_recursive.toggled, settings.properties.recursive_movement
        )

        self.binder.bind(
            settings.properties.label_movement,
            toggle_labels.setChecked,
            lambda x: not x,
        )
        self.binder.bind(
            toggle_labels.toggled, settings.properties.label_movement, lambda x: not x
        )

        self.binder.bind(settings.properties.show_legend, toggle_legend.setChecked)
        self.binder.bind(toggle_legend.toggled, settings.properties.show_legend)

        self.binder.bind(settings.properties.show_scale, toggle_scale.setChecked)
        self.binder.bind(toggle_scale.toggled, settings.properties.show_scale)

        self.binder.bind(
            settings.fields.properties.show_groups, toggle_field_groups.setChecked
        )
        self.binder.bind(
            toggle_field_groups.toggled, settings.fields.properties.show_groups
        )

        self.binder.bind(
            settings.fields.properties.show_isolated, toggle_field_isolated.setChecked
        )
        self.binder.bind(
            toggle_field_isolated.toggled, settings.fields.properties.show_isolated
        )

        self.binder.bind(
            settings.properties.rotate_scene, toggle_scene_rotation.setChecked
        )
        self.binder.bind(
            toggle_scene_rotation.toggled, settings.properties.rotate_scene
        )

        self.binder.bind(self.node_size_dialog.commandPosted, self.scene.commandPosted)
        self.binder.bind(
            self.label_format_dialog.commandPosted, self.scene.commandPosted
        )
        self.binder.bind(
            self.scale_style_dialog.commandPosted, self.scene.commandPosted
        )
        self.binder.bind(self.pen_style_dialog.commandPosted, self.scene.commandPosted)
        self.binder.bind(self.font_dialog.commandPosted, self.scene.commandPosted)
        self.binder.bind(
            self.edge_length_dialog.commandPosted, self.scene.commandPosted
        )
        self.binder.bind(self.edge_style_dialog.commandPosted, self.scene.commandPosted)

        action = QtGui.QAction()
        action.setShortcut(QtGui.QKeySequence.Save)
        action.triggered.connect(self.quick_save)
        self.quick_save_action = action
        self.addAction(action)

        self.demos.load_demo_simple()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        gg = self.scene_view.geometry()
        gg.setTopLeft(
            QtCore.QPoint(
                gg.bottomRight().x() - self.zoom_control.width() - 16,
                gg.bottomRight().y() - self.zoom_control.height() - 16,
            )
        )
        self.zoom_control.setGeometry(gg)

    def quick_save(self):
        self.export_svg("graph.svg")
        self.export_pdf("graph.pdf")
        self.export_png("graph.png")

    def export_svg(self, file=None):
        if file is None:
            file, _ = QtWidgets.QFileDialog.getSaveFileName(
                self, "Export As...", "graph.svg", "SVG Files (*.svg)"
            )
        if not file:
            return
        print("SVG >", file)
        self.scene_view.export_svg(file)

    def export_pdf(self, file=None):
        if file is None:
            file, _ = QtWidgets.QFileDialog.getSaveFileName(
                self, "Export As...", "graph.pdf", "PDF Files (*.pdf)"
            )
        if not file:
            return
        print("PDF >", file)
        self.scene_view.export_pdf(file)

    def export_png(self, file=None):
        if file is None:
            file, _ = QtWidgets.QFileDialog.getSaveFileName(
                self, "Export As...", "graph.png", "PNG Files (*.png)"
            )
        if not file:
            return
        print("PNG >", file)
        self.scene_view.export_png(file)
