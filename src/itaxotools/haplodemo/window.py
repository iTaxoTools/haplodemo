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
    EdgeStyleDialog, LabelFormatDialog, NodeSizeDialog, ScaleMarksDialog)
from .scene import GraphicsScene, GraphicsView, Settings
from .widgets import ColorDelegate, DivisionView, PaletteSelector, ToggleButton
from .zoom import ZoomControl


class Window(QtWidgets.QWidget):
    def __init__(self, opengl=False):
        super().__init__()
        self.setWindowFlags(QtCore.Qt.Window)
        self.resize(840, 520)
        self.setWindowTitle('Haplodemo')

        settings = Settings()
        settings.divisions.set_divisions_from_keys(['X', 'Y', 'Z'])
        settings.font = QtGui.QFont('Arial', 16)
        settings.scale.marks = [2, 10, 30]

        scene = GraphicsScene(settings)
        scene.set_boundary(0, 0, 400, 320)
        # scene.showLegend()
        # scene.showScale()
        # scene.addManyNodes(8, 32)
        # scene.addBezier()
        scene.addNodes()

        scene.styleLabels(settings.node_label_template, settings.edge_label_template)

        scene_view = GraphicsView(scene, opengl)

        palette_selector = PaletteSelector()

        self.edge_style_dialog = EdgeStyleDialog(self, scene)
        self.edge_style_dialog.apply()

        self.node_size_dialog = NodeSizeDialog(self, scene, settings.node_sizes)
        self.node_size_dialog.apply()

        self.scale_style_dialog = ScaleMarksDialog(self, scene, settings.scale)
        self.scale_style_dialog.apply()

        self.label_format_dialog = LabelFormatDialog(self, scene, settings)
        self.label_format_dialog.apply()

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

        dialogs = QtWidgets.QVBoxLayout()
        dialogs.addWidget(mass_style_edges)
        dialogs.addWidget(mass_resize_nodes)
        dialogs.addWidget(style_scale)
        dialogs.addWidget(mass_format_labels)
        dialogs.addWidget(select_font)

        toggles = QtWidgets.QVBoxLayout()
        toggles.addWidget(toggle_rotation)
        toggles.addWidget(toggle_recursive)
        toggles.addWidget(toggle_labels)
        toggles.addWidget(toggle_legend)
        toggles.addWidget(toggle_scale)

        sidebar = QtWidgets.QVBoxLayout()
        sidebar.setContentsMargins(0, 0, 0, 0)
        sidebar.addLayout(exports)
        sidebar.addSpacing(4)
        sidebar.addWidget(HLineSeparator(1))
        sidebar.addSpacing(4)
        sidebar.addLayout(dialogs)
        sidebar.addSpacing(4)
        sidebar.addWidget(HLineSeparator(1))
        sidebar.addSpacing(4)
        sidebar.addLayout(toggles)
        sidebar.addSpacing(4)
        sidebar.addWidget(HLineSeparator(1))
        sidebar.addSpacing(4)
        sidebar.addWidget(palette_selector)
        sidebar.addWidget(division_view, 1)

        sidebar_widget = QtWidgets.QWidget()
        sidebar_widget.setLayout(sidebar)
        sidebar_widget.setFixedWidth(160)

        layout = QtWidgets.QHBoxLayout()
        layout.addWidget(sidebar_widget)
        layout.addWidget(scene_view, 1)
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
