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
from itaxotools.common.widgets import HLineSeparator

from .dialogs import (
    EdgeStyleDialog, LabelFormatDialog, NodeSizeDialog, PenWidthDialog,
    ScaleMarksDialog)
from .scene import GraphicsScene, GraphicsView, Settings
from .types import HaploNode
from .widgets import ColorDelegate, DivisionView, PaletteSelector, ToggleButton
from .zoom import ZoomControl


class Window(QtWidgets.QWidget):
    def __init__(self, opengl=False):
        super().__init__()
        self.setWindowFlags(QtCore.Qt.Window)
        self.resize(960, 520)
        self.setWindowTitle('Haplodemo')

        settings = Settings()
        settings.divisions.set_divisions_from_keys(['X', 'Y', 'Z'])
        settings.font = QtGui.QFont('Arial', 16)
        settings.scale.marks = [2, 10, 30]

        scene = GraphicsScene(settings)
        # scene.addBezier()

        scene.style_labels(settings.node_label_template, settings.edge_label_template)

        scene_view = GraphicsView(scene, opengl)

        palette_selector = PaletteSelector()

        self.edge_style_dialog = EdgeStyleDialog(self, scene)
        self.node_size_dialog = NodeSizeDialog(self, scene, settings.node_sizes)
        self.scale_style_dialog = ScaleMarksDialog(self, scene, settings.scale)
        self.pen_style_dialog = PenWidthDialog(self, scene, settings)
        self.label_format_dialog = LabelFormatDialog(self, scene, settings)

        button_demo_simple = QtWidgets.QPushButton('Load simple demo')
        button_demo_simple.clicked.connect(lambda: self.load_demo_simple())

        button_demo_many = QtWidgets.QPushButton('Load many nodes')
        button_demo_many.clicked.connect(lambda: self.load_demo_many())

        button_demo_tiny_tree = QtWidgets.QPushButton('Load tiny tree')
        button_demo_tiny_tree.clicked.connect(lambda: self.load_demo_tiny_tree())

        button_svg = QtWidgets.QPushButton('Export as SVG')
        button_svg.clicked.connect(lambda: self.export_svg())

        button_pdf = QtWidgets.QPushButton('Export as PDF')
        button_pdf.clicked.connect(lambda: self.export_pdf())

        button_png = QtWidgets.QPushButton('Export as PNG')
        button_png.clicked.connect(lambda: self.export_png())

        mass_style_edges = QtWidgets.QPushButton('Set edge style')
        mass_style_edges.clicked.connect(self.edge_style_dialog.show)

        mass_resize_nodes = QtWidgets.QPushButton('Set node size')
        mass_resize_nodes.clicked.connect(self.node_size_dialog.show)

        style_pens = QtWidgets.QPushButton('Set pen width')
        style_pens.clicked.connect(self.pen_style_dialog.show)

        style_scale = QtWidgets.QPushButton('Set scale marks')
        style_scale.clicked.connect(self.scale_style_dialog.show)

        mass_format_labels = QtWidgets.QPushButton('Set label format')
        mass_format_labels.clicked.connect(self.label_format_dialog.show)

        select_font = QtWidgets.QPushButton('Set font')
        select_font.clicked.connect(self.show_font_dialog)

        toggle_rotation = ToggleButton('Rotate nodes')
        toggle_recursive = ToggleButton('Move children')
        toggle_labels = ToggleButton('Lock labels')
        toggle_legend = ToggleButton('Show legend')
        toggle_scale = ToggleButton('Show scale')

        division_view = DivisionView(settings.divisions)

        exports = QtWidgets.QVBoxLayout()
        exports.addWidget(button_svg)
        exports.addWidget(button_pdf)
        exports.addWidget(button_png)

        demos = QtWidgets.QVBoxLayout()
        demos.addWidget(button_demo_simple)
        demos.addWidget(button_demo_many)
        demos.addWidget(button_demo_tiny_tree)

        toggles = QtWidgets.QVBoxLayout()
        toggles.addWidget(toggle_rotation)
        toggles.addWidget(toggle_recursive)
        toggles.addWidget(toggle_labels)
        toggles.addWidget(toggle_legend)
        toggles.addWidget(toggle_scale)

        dialogs = QtWidgets.QVBoxLayout()
        dialogs.addWidget(mass_style_edges)
        dialogs.addWidget(mass_resize_nodes)
        dialogs.addWidget(style_pens)
        dialogs.addWidget(style_scale)
        dialogs.addWidget(mass_format_labels)
        dialogs.addWidget(select_font)

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
        right_layout.addWidget(palette_selector)
        right_layout.addWidget(division_view, 1)

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

        self.binder.bind(palette_selector.currentValueChanged, settings.properties.palette)
        self.binder.bind(settings.properties.palette, palette_selector.setValue)
        self.binder.bind(settings.properties.palette, ColorDelegate.setCustomColors)

        self.binder.bind(settings.properties.rotational_movement, toggle_rotation.setChecked)
        self.binder.bind(toggle_rotation.toggled, settings.properties.rotational_movement)

        self.binder.bind(settings.properties.recursive_movement, toggle_recursive.setChecked)
        self.binder.bind(toggle_recursive.toggled, settings.properties.recursive_movement)

        self.binder.bind(settings.properties.label_movement, toggle_labels.setChecked, lambda x: not x)
        self.binder.bind(toggle_labels.toggled, settings.properties.label_movement, lambda x: not x)

        self.binder.bind(settings.properties.show_legend, toggle_legend.setChecked)
        self.binder.bind(toggle_legend.toggled, settings.properties.show_legend)

        self.binder.bind(settings.properties.show_scale, toggle_scale.setChecked)
        self.binder.bind(toggle_scale.toggled, settings.properties.show_scale)

        action = QtGui.QAction()
        action.setShortcut(QtGui.QKeySequence.Save)
        action.triggered.connect(self.quick_save)
        self.quick_save_action = action
        self.addAction(action)

        self.load_demo_simple()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        gg = self.scene_view.geometry()
        gg.setTopLeft(QtCore.QPoint(
            gg.bottomRight().x() - self.zoom_control.width() - 16,
            gg.bottomRight().y() - self.zoom_control.height() - 16,
        ))
        self.zoom_control.setGeometry(gg)

    def show_font_dialog(self):
        _, font = QtWidgets.QFontDialog.getFont(
            self.settings.font, self, 'Set Font',
            QtWidgets.QFontDialog.FontDialogOptions.DontUseNativeDialog)
        self.settings.font = font

    def load_demo_simple(self):
        self.scene.clear()

        self.settings.node_sizes.a = 10
        self.settings.node_sizes.b = 2
        self.settings.node_sizes.c = 0.2
        self.settings.node_sizes.d = 1
        self.settings.node_sizes.e = 0
        self.settings.node_sizes.f = 0
        self.settings.show_legend = True
        self.settings.show_scale = True
        self.settings.scale.marks = [5, 40]
        self.settings.font = QtGui.QFont('Arial', 16)

        self.add_demo_nodes_simple()

        self.scene.style_nodes()
        self.scene.set_boundary_to_contents()

    def add_demo_nodes_simple(self):
        scene = self.scene

        node1 = scene.create_node(85, 70, 35, 'Alphanumerical', {'X': 4, 'Y': 3, 'Z': 2})
        scene.addItem(node1)

        node2 = scene.create_node(node1.pos().x() + 95, node1.pos().y() - 30, 20, 'Beta', {'X': 4, 'Z': 2})
        scene.add_child_edge(node1, node2, 2)

        node3 = scene.create_node(node1.pos().x() + 115, node1.pos().y() + 60, 25, 'C', {'Y': 6, 'Z': 2})
        scene.add_child_edge(node1, node3, 3)

        node4 = scene.create_node(node3.pos().x() + 60, node3.pos().y() - 30, 15, 'D', {'Y': 1})
        scene.add_child_edge(node3, node4, 1)

        vertex1 = scene.create_vertex(node3.pos().x() - 60, node3.pos().y() + 60)
        scene.add_child_edge(node3, vertex1, 2)

        node5 = scene.create_node(vertex1.pos().x() - 80, vertex1.pos().y() + 40, 30, 'Error', {'?': 1})
        scene.add_child_edge(vertex1, node5, 4)

        node6 = scene.create_node(vertex1.pos().x() + 60, vertex1.pos().y() + 20, 20, 'R', {'Z': 1})
        scene.add_child_edge(vertex1, node6, 1)

        node7 = scene.create_node(vertex1.pos().x() + 100, vertex1.pos().y() + 80, 10, 'S', {'Z': 1})
        scene.add_sibling_edge(node6, node7, 2)

        node8 = scene.create_node(vertex1.pos().x() + 20, vertex1.pos().y() + 80, 40, 'T', {'Y': 1})
        scene.add_sibling_edge(node6, node8, 1)
        scene.add_sibling_edge(node7, node8, 1)

        node9 = scene.create_node(node7.pos().x() + 20, node7.pos().y() - 40, 5, 'x', {'Z': 1})
        scene.add_child_edge(node7, node9, 1)

    def load_demo_many(self):
        self.scene.clear()

        self.settings.node_sizes.a = 0
        self.settings.node_sizes.b = 0
        self.settings.node_sizes.c = 0
        self.settings.node_sizes.d = 0
        self.settings.node_sizes.e = 0
        self.settings.node_sizes.f = 30
        self.settings.show_legend = False
        self.settings.show_scale = False
        self.settings.font = QtGui.QFont('Arial', 16)

        self.add_demo_nodes_many(8, 32)

        self.scene.style_nodes()
        self.scene.set_boundary_to_contents()

    def add_demo_nodes_many(self, dx, dy):
        scene = self.scene

        for x in range(dx):
            nodex = scene.create_node(20, 80 * x, 15, f'x{x}', {'X': 1})
            scene.addItem(nodex)

            for y in range(dy):
                nodey = scene.create_node(nodex.pos().x() + 80 + 80 * y, nodex.pos().y() + 40, 15, f'y{y}', {'Y': 1})
                scene.add_child_edge(nodex, nodey)

    def load_demo_tiny_tree(self):
        self.settings.node_sizes.a = 0
        self.settings.node_sizes.b = 0
        self.settings.node_sizes.c = 0
        self.settings.node_sizes.d = 0
        self.settings.node_sizes.e = 10
        self.settings.node_sizes.f = 20
        self.settings.show_legend = True
        self.settings.show_scale = True
        self.settings.edge_length = 40
        self.settings.node_label_template = 'WEIGHT'
        self.settings.font = QtGui.QFont('Arial', 24)
        tree = self.get_tiny_tree()
        self.scene.add_nodes_from_tree(tree)

        self.scene.style_labels(
            self.settings.node_label_template,
            self.settings.edge_label_template,
        )

    def get_tiny_tree(self) -> HaploNode:
        root = HaploNode('root')
        root.add_pops(['X'] * 3 + ['Y'] * 5)

        a = HaploNode('a')
        a.add_pops(['X'] * 1)
        root.add_child(a, 1)

        b = HaploNode('b')
        b.add_pops(['Y'] * 3)
        root.add_child(b, 4)

        c = HaploNode('c')
        c.add_pops(['Y'] * 1)
        b.add_child(c, 1)

        d = HaploNode('d')
        d.add_pops(['Z'] * 1)
        b.add_child(d, 2)

        return root

    def quick_save(self):
        self.export_svg('graph.svg')
        self.export_pdf('graph.pdf')
        self.export_png('graph.png')

    def export_svg(self, file=None):
        if file is None:
            file, _ = QtWidgets.QFileDialog.getSaveFileName(
                self, 'Export As...', 'graph.svg', 'SVG Files (*.svg)')
        if not file:
            return
        print('SVG >', file)
        self.scene_view.export_svg(file)

    def export_pdf(self, file=None):
        if file is None:
            file, _ = QtWidgets.QFileDialog.getSaveFileName(
                self, 'Export As...', 'graph.pdf', 'PDF Files (*.pdf)')
        if not file:
            return
        print('PDF >', file)
        self.scene_view.export_pdf(file)

    def export_png(self, file=None):
        if file is None:
            file, _ = QtWidgets.QFileDialog.getSaveFileName(
                self, 'Export As...', 'graph.png', 'PNG Files (*.png)')
        if not file:
            return
        print('PNG >', file)
        self.scene_view.export_png(file)
