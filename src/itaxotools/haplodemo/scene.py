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

from PySide6 import QtCore, QtGui, QtOpenGLWidgets, QtSvg, QtWidgets

from contextlib import contextmanager
from math import cos, radians, sin

from itaxotools.common.bindings import Binder

from .history import (
    BezierEditCommand,
    BoundaryResizedCommand,
    LabelMovementCommand,
    NodeMovementCommand,
    SceneRotationCommand,
    SoloMovementCommand,
)
from .items.bezier import BezierCurve
from .items.boundary import BoundaryOutline, BoundaryRect
from .items.boxes import RectBox
from .items.edges import Edge
from .items.labels import Label
from .items.legend import Legend
from .items.nodes import Node, Vertex
from .items.protocols import HoverableItem, SoloMovableItemWithHistory
from .items.rotate import PivotHandle
from .items.scale import Scale
from .items.types import EdgeStyle
from .settings import Settings


class GraphicsScene(QtWidgets.QGraphicsScene):
    boundaryPlaced = QtCore.Signal()
    rotateModeChanged = QtCore.Signal(bool)
    commandPosted = QtCore.Signal(QtGui.QUndoCommand)
    cleared = QtCore.Signal()

    def __init__(self, settings: Settings, parent=None):
        super().__init__(parent)
        self.installEventFilter(self)

        mid = QtWidgets.QApplication.instance().palette().mid()
        self.setBackgroundBrush(mid)

        self.settings = settings
        self.root = None

        self.boundary = None
        self.legend = None
        self.scale = None
        self.pivot = None

        self._view_scale = None
        self.rotating = False

        self.binder = Binder()
        self.reset_binder()

    def eventFilter(self, obj, event):
        if self.settings.rotate_scene:
            return self.rotateEvent(event)
        return super().eventFilter(obj, event)

    def rotateEvent(self, event):
        grabber = self.mouseGrabberItem()
        if isinstance(grabber, PivotHandle):
            return False

        if event.type() == QtCore.QEvent.GraphicsSceneMouseMove:
            if self.getItemAtPosByType(event.scenePos(), PivotHandle):
                self.pivot.set_hovered(True)
                return False

            self.pivot.set_hovered(False)
            if self.rotating:
                vertices = (item for item in self.items() if isinstance(item, Vertex))
                for vertex in vertices:
                    vertex.moveRotationally(event)
            return True

        elif event.type() == QtCore.QEvent.GraphicsSceneMousePress:
            if self.getItemAtPosByType(event.scenePos(), PivotHandle):
                return False

            center = self.pivot.pos()
            vertices = (item for item in self.items() if isinstance(item, Vertex))
            for vertex in vertices:
                vertex.lockPosition(event, center=center)
                vertex.in_scene_rotation = True
            self.rotating = True
            return True

        elif event.type() == QtCore.QEvent.GraphicsSceneMouseRelease:
            self.handle_scene_rotation()

            vertices = (item for item in self.items() if isinstance(item, Vertex))
            for vertex in vertices:
                vertex.in_scene_rotation = False
            self.rotating = False
            return True

        return False

    def getItemAtPosByType(self, pos, *types):
        if not types:
            types = [QtWidgets.QGraphicsItem]
        for item in self.items(pos):
            if any((isinstance(item, type) for type in types)):
                return item
        return None

    def getItemAtPosByTypeExcluded(self, pos, *types):
        if not types:
            raise TypeError("Must provide at least one type")
        for item in self.items(pos):
            if any((isinstance(item, type) for type in types)):
                continue
            return item
        return None

    def set_boundary_rect(self, x=0, y=0, w=0, h=0):
        if not self.boundary:
            self.boundary = BoundaryRect(x, y, w, h)
            self.addItem(self.boundary)
        elif w == h == 0:
            self.removeItem(self.boundary)
            self.boundary = None
            return
        else:
            self.boundary.setRect(x, y, w, h)
        self.boundaryPlaced.emit()
        self.position_legend()
        self.position_scale()

    def get_item_boundary(self):
        bounds = QtCore.QRectF()
        for item in self.items():
            if not isinstance(item, Vertex):
                continue
            rect = QtCore.QRectF(item.rect())
            rect.translate(item.pos())
            bounds = bounds.united(rect)

        margin = max(bounds.width(), bounds.height()) / 10
        margin = max(margin, 16)

        return bounds, margin

    def set_boundary_to_contents(self):
        bounds, margin = self.get_item_boundary()

        right_margin = 0
        minimum_height = 2 * margin
        if self.settings.show_legend:
            width = self.legend.boundingRect().width()
            height = self.legend.boundingRect().height()
            right_margin = max(right_margin, 2 * margin + width)
            minimum_height += height
        if self.settings.show_scale:
            width = self.scale.get_extended_rect().width()
            height = self.scale.get_extended_rect().height()
            right_margin = max(right_margin, 2 * margin + width)
            minimum_height += height
        if self.settings.show_legend and self.settings.show_scale:
            minimum_height += margin
        right_margin += margin

        bounds.adjust(-margin, -margin, right_margin, margin)

        if bounds.height() < minimum_height:
            diff = minimum_height - bounds.height()
            bounds.setHeight(minimum_height)
            bounds.translate(0, -diff / 2)

        self.set_boundary_rect(
            bounds.x(),
            bounds.y(),
            bounds.width(),
            bounds.height(),
        )

        self.position_legend()
        self.position_scale()

    def show_legend(self, value=True):
        if not self.legend:
            self.legend = Legend()
            self.addItem(self.legend)
            self.binder.bind(
                self.settings.divisions.colorMapChanged, self.legend.update_colors
            )
            self.binder.bind(
                self.settings.divisions.divisionsChanged, self.legend.set_divisions
            )
            self.binder.bind(
                self.settings.properties.highlight_color,
                self.legend.set_highlight_color,
            )
            self.binder.bind(
                self.settings.properties.pen_width_nodes, self.legend.set_pen_width
            )
            self.binder.bind(self.settings.properties.font, self.legend.set_label_font)
            self.legend.set_divisions(self.settings.divisions.all())
        self.legend.setVisible(value)
        self.position_legend()

    def show_scale(self, value=True):
        if not self.scale:
            self.scale = Scale(self.settings)
            self.addItem(self.scale)
            self.binder.bind(self.settings.scale.properties.marks, self.scale.set_marks)
            self.binder.bind(
                self.settings.properties.label_movement,
                self.scale.set_labels_locked,
                lambda x: not x,
            )
            self.binder.bind(
                self.settings.properties.highlight_color, self.scale.set_highlight_color
            )
            self.binder.bind(
                self.settings.properties.pen_width_nodes, self.scale.set_pen_width
            )
            self.binder.bind(self.settings.properties.font, self.scale.set_label_font)
            for property in self.settings.node_sizes.properties:
                self.binder.bind(property, self.scale.update_radii)
        self.scale.setVisible(value)
        self.position_scale()

    def show_pivot(self, value=True):
        if not self.pivot:
            self.pivot = PivotHandle()
            self.addItem(self.pivot)
            self.binder.bind(
                self.settings.properties.highlight_color, self.pivot.set_highlight_color
            )
        self.pivot.setVisible(value)
        self.position_pivot()

    def position_legend(self, margin=None):
        if not self.boundary:
            return
        bounds = self.boundary.rect()
        width = self.legend.rect().width()
        _, margin = self.get_item_boundary()
        self.legend.setPos(
            bounds.x() + bounds.width() - width - margin, bounds.y() + margin
        )

    def position_scale(self):
        if not self.boundary:
            return
        bounds = self.boundary.rect()
        scale = self.scale.get_extended_rect()
        diff = self.scale.get_bottom_margin()
        _, margin = self.get_item_boundary()
        self.scale.setPos(
            bounds.x() + bounds.width() - scale.width() - margin,
            bounds.y() + bounds.height() - diff - margin,
        )

    def position_pivot(self):
        if not self.pivot:
            return

        scale = self._view_scale or 1.0
        self.pivot.adjust_scale(scale)
        pos = self._determine_pivot_pos()
        self.pivot.setPos(pos)

        for item in self.selectedItems():
            item.setSelected(False)

    def _determine_pivot_pos(self) -> QtCore.QPointF():
        if self.selectedItems():
            selection = self.selectedItems()
            selection = [item for item in selection if isinstance(item, Vertex)]
            node = selection[0] if selection else None
            if node:
                return node.pos()
        bounds, _ = self.get_item_boundary()
        return bounds.center()

    def resize_edges(self, length_per_mutation: float):
        vertices = [item for item in self.items() if isinstance(item, Vertex)]
        for vertex in vertices:
            vertex.locked_pos = vertex.pos()
            for bezier in vertex.beziers.values():
                bezier.lock_control_points()

        root = self.root or vertices[0]
        angles = self._get_edge_angles(root)
        self._set_edge_lengths(root, angles, length_per_mutation)

    def _get_edge_angles(self, root: Vertex) -> dict[tuple[Vertex, Vertex], float]:
        def traverser(item: Vertex, angles: dict):
            others = list(item.children) + list(item.siblings)
            if item.parent is not None:
                others += [item.parent]

            for other in others:
                line = QtCore.QLineF(item.pos(), other.pos())
                angles[(item, other)] = line.angle()

        angles = dict()
        root._mapRecursive(
            True, True, set(), set(), traverser, [angles], {}, None, None, None
        )
        return angles

    def _set_edge_lengths(self, root: Vertex, angles: dict, length_per_mutation: float):
        def traverser(item: Vertex, angles: dict):
            item_radius = item.radius if isinstance(item, Node) else 0
            others = item.children + item.siblings
            if item.parent is not None:
                others += [item.parent]

            for other in others:
                edge = item.edges[other]
                other_radius = other.radius if isinstance(other, Node) else 0
                length = item_radius + other_radius + length_per_mutation * edge.weight

                angle_deg = angles[(item, other)]
                angle_rad = radians(angle_deg)
                x = item.pos().x() + length * cos(angle_rad)
                y = item.pos().y() - length * sin(angle_rad)
                other.setPos(x, y)

        root._mapRecursive(
            True, True, set(), set(), traverser, [angles], {}, None, None, None
        )

    def set_boxes_visible(self, show_groups: bool, show_isolated: bool = True):
        for item in self.items():
            match item:
                case RectBox():
                    if len(item.items) == 1:
                        visible = show_isolated
                    else:
                        visible = show_groups
                    item.setVisible(visible)
                case BezierCurve():
                    item.setVisible(show_groups)
                    if not show_groups and item.h1:
                        item.remove_controls()

    def update_boxes_visible(self):
        show_groups = self.settings.fields.show_groups
        show_isolated = self.settings.fields.show_isolated
        self.set_boxes_visible(show_groups, show_isolated)

    def style_edges(self, style_default=EdgeStyle.Bubbles, cutoff=3):
        if not cutoff:
            cutoff = float("inf")
        style_cutoff = {
            EdgeStyle.Bubbles: EdgeStyle.DotsWithText,
            EdgeStyle.Bars: EdgeStyle.Collapsed,
            EdgeStyle.Plain: EdgeStyle.PlainWithText,
        }[style_default]
        edges = (item for item in self.items() if isinstance(item, Edge))

        for edge in edges:
            style = style_default if edge.segments <= cutoff else style_cutoff
            edge.lock_style()
            edge.set_style(style)

    def style_nodes(self):
        nodes = (item for item in self.items() if isinstance(item, Node))
        edges = (item for item in self.items() if isinstance(item, Edge))
        boxes = (item for item in self.items() if isinstance(item, RectBox))
        for node in nodes:
            node.adjust_radius()
        for edge in edges:
            edge.adjust_position()
        for box in boxes:
            box.adjust_position()

    def style_labels(self):
        node_label_format = self.settings.node_label_template.replace(
            "NAME", "{name}"
        ).replace("WEIGHT", "{weight}")
        edge_label_format = self.settings.edge_label_template.replace(
            "WEIGHT", "{weight}"
        )
        nodes = (item for item in self.items() if isinstance(item, Node))
        edges = (item for item in self.items() if isinstance(item, Edge))
        for node in nodes:
            text = node_label_format.format(name=node.name, weight=node.weight)
            node.label.setText(text)
        for edge in edges:
            text = edge_label_format.format(weight=edge.weight)
            edge.label.setText(text)

    def get_marks_from_nodes(self):
        weights = set()
        nodes = (item for item in self.items() if isinstance(item, Node))
        for node in nodes:
            weights.add(node.weight)
        if len(weights) < 3:
            return list(sorted(weights))
        weights = sorted(weights)
        med = int(len(weights) / 2)
        return [
            weights[0],
            weights[med],
            weights[-1],
        ]

    def set_marks_from_nodes(self):
        marks = self.get_marks_from_nodes()
        self.settings.scale.marks = marks

    def handle_view_scaled(self, scale):
        self._view_scale = scale
        if self.pivot:
            self.pivot.adjust_scale(scale)
        if self.boundary:
            self.boundary.adjust_scale(scale)
        vertices = (item for item in self.items() if isinstance(item, Vertex))
        for vertex in vertices:
            vertex.adjust_scale(scale)

    def handle_node_movement(self, item: Vertex):
        command = NodeMovementCommand(item)
        self.commandPosted.emit(command)

    def handle_label_movement(self, item: Label):
        command = LabelMovementCommand(item)
        self.commandPosted.emit(command)

    def handle_solo_movement(self, item: SoloMovableItemWithHistory):
        command = SoloMovementCommand(item)
        self.commandPosted.emit(command)

    def handle_bezier_edit(self, item: BezierCurve):
        command = BezierEditCommand(item)
        self.commandPosted.emit(command)

    def handle_boundary_resized(self, item: BoundaryRect):
        command = BoundaryResizedCommand(item)
        self.commandPosted.emit(command)

    def handle_scene_rotation(self):
        command = SceneRotationCommand(self)
        self.commandPosted.emit(command)

    def reset_binder(self):
        self.binder.unbind_all()
        self.binder.bind(self.settings.properties.rotate_scene, self.show_pivot)
        self.binder.bind(self.settings.properties.rotate_scene, self.rotateModeChanged)
        self.binder.bind(self.settings.properties.show_legend, self.show_legend)
        self.binder.bind(self.settings.properties.show_scale, self.show_scale)

        self.binder.bind(
            self.settings.fields.properties.show_groups, self.update_boxes_visible
        )
        self.binder.bind(
            self.settings.fields.properties.show_isolated, self.update_boxes_visible
        )

    def clear(self):
        super().clear()
        self.boundary = None
        self.legend = None
        self.scale = None
        self.pivot = None
        self.reset_binder()

        self.settings.rotate_scene = False

        self.root = None

        self.cleared.emit()


class GraphicsView(QtWidgets.QGraphicsView):
    scaled = QtCore.Signal(float)
    rotating = QtCore.Signal(bool)

    def __init__(self, scene=None, opengl=False, parent=None):
        super().__init__(parent)

        self.locked_center = None
        self.zoom_factor = 1.10
        self.zoom_maximum = 4.0
        self.zoom_minimum = 0.1
        self.rotate_mode = False
        self.rotating = False

        self.setScene(scene)

        self.setRenderHints(QtGui.QPainter.TextAntialiasing)
        self.setRenderHints(QtGui.QPainter.Antialiasing)
        self.setDragMode(QtWidgets.QGraphicsView.NoDrag)
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOn)
        self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOn)
        self.setViewportUpdateMode(QtWidgets.QGraphicsView.FullViewportUpdate)
        self.setTransformationAnchor(QtWidgets.QGraphicsView.AnchorUnderMouse)
        # self.setMouseTracking(True)

        if opengl:
            self.enable_opengl()

    def setScene(self, scene):
        super().setScene(scene)
        scene.boundaryPlaced.connect(self.initializeSceneRect)
        scene.rotateModeChanged.connect(self.handle_rotate_mode_changed)
        self.scaled.connect(scene.handle_view_scaled)
        self.adjustSceneRect()
        self.lock_center()

    def initializeSceneRect(self):
        self.adjustSceneRect()

        rect = self.scene().boundary.rect()
        m = max(rect.width(), rect.height())
        m /= 10
        rect.adjust(-m, -m, m, m)
        self.fitInView(rect, QtCore.Qt.KeepAspectRatio)

        scale = self.transform().m11()
        self.scaled.emit(scale)

    def adjustSceneRect(self):
        if not self.scene().boundary:
            return
        rect = self.scene().boundary.rect()
        rect.adjust(
            -2 * rect.width(),
            -2 * rect.height(),
            +2 * rect.width(),
            +2 * rect.height(),
        )
        self.setSceneRect(rect)

    def setScale(self, scale):
        current_scale = self.transform().m11()
        zoom = scale / current_scale
        self.zoom(zoom)

    def zoom(self, zoom):
        scale = self.transform().m11()

        if scale * zoom < self.zoom_minimum:
            zoom = self.zoom_minimum / scale
        if scale * zoom > self.zoom_maximum:
            zoom = self.zoom_maximum / scale

        self.scale(zoom, zoom)

        scale = self.transform().m11()
        self.scaled.emit(scale)

    def zoomIn(self):
        self.zoom(self.zoom_factor)

    def zoomOut(self):
        self.zoom(1 / self.zoom_factor)

    def event(self, event):
        if event.type() == QtCore.QEvent.NativeGesture:
            return self.nativeGestureEvent(event)
        return super().event(event)

    def nativeGestureEvent(self, event):
        if event.gestureType() == QtCore.Qt.NativeGestureType.ZoomNativeGesture:
            self.nativeZoomEvent(event)
            return True
        return False

    def nativeZoomEvent(self, event):
        zoom = 1 + event.value()
        self.zoom(zoom)

    def wheelEvent(self, event):
        if event.modifiers() & QtCore.Qt.KeyboardModifier.ControlModifier:
            return self.wheelZoomEvent(event)
        return self.wheelPanEvent(event)

    def wheelZoomEvent(self, event):
        zoom_in = bool(event.angleDelta().y() > 0)
        zoom = self.zoom_factor if zoom_in else 1 / self.zoom_factor
        self.zoom(zoom)

    def wheelPanEvent(self, event):
        xx = self.horizontalScrollBar().value()
        self.horizontalScrollBar().setValue(xx - event.angleDelta().x())
        yy = self.verticalScrollBar().value()
        self.verticalScrollBar().setValue(yy - event.angleDelta().y())

    def mousePressEvent(self, event):
        pos = self.mapToScene(event.pos())
        item = self.scene().getItemAtPosByTypeExcluded(
            pos, BoundaryRect, BoundaryOutline, RectBox
        )
        if event.button() == QtCore.Qt.LeftButton:
            if self.rotate_mode:
                self.rotating = True
                pos = self.mapToScene(event.pos())
                pivot = self.scene().getItemAtPosByType(pos, PivotHandle)
                if pivot:
                    self.viewport().setCursor(QtCore.Qt.ArrowCursor)
                else:
                    self.viewport().setCursor(QtCore.Qt.ClosedHandCursor)
            elif not item:
                self.setDragMode(QtWidgets.QGraphicsView.ScrollHandDrag)

        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            if self.rotate_mode:
                self.rotating = False
                self.viewport().setCursor(QtCore.Qt.OpenHandCursor)
            else:
                self.viewport().setCursor(QtCore.Qt.ArrowCursor)
            self.setDragMode(QtWidgets.QGraphicsView.NoDrag)
            self.adjustSceneRect()
            self.lock_center()

        super().mouseReleaseEvent(event)

    def mouseMoveEvent(self, event):
        super().mouseMoveEvent(event)

        if self.rotate_mode:
            pos = self.mapToScene(event.pos())
            pivot = self.scene().getItemAtPosByType(pos, PivotHandle)
            grabber = self.scene().mouseGrabberItem()
            if grabber or pivot:
                self.viewport().setCursor(QtCore.Qt.ArrowCursor)
            elif self.rotating:
                self.viewport().setCursor(QtCore.Qt.ClosedHandCursor)
            else:
                self.viewport().setCursor(QtCore.Qt.OpenHandCursor)

    def resizeEvent(self, event):
        if not event.oldSize().isValid():
            return

        if self.locked_center:
            self.centerOn(self.locked_center)

    def showEvent(self, event):
        super().showEvent(event)
        self.lock_center()

    def lock_center(self):
        self.locked_center = self.mapToScene(self.viewport().rect().center())

    def handle_rotate_mode_changed(self, value):
        self.rotate_mode = value
        if value:
            self.viewport().setCursor(QtCore.Qt.OpenHandCursor)
        else:
            self.viewport().setCursor(QtCore.Qt.ArrowCursor)

    def enable_opengl(self):
        format = QtGui.QSurfaceFormat()
        format.setVersion(3, 3)
        format.setProfile(QtGui.QSurfaceFormat.CoreProfile)
        format.setRenderableType(QtGui.QSurfaceFormat.OpenGL)
        format.setDepthBufferSize(24)
        format.setStencilBufferSize(8)
        format.setSamples(8)

        glwidget = QtOpenGLWidgets.QOpenGLWidget()
        glwidget.setFormat(format)
        self.setViewport(glwidget)
        self.setViewportUpdateMode(QtWidgets.QGraphicsView.FullViewportUpdate)

    @contextmanager
    def prepare_export(self, file: str):
        """Make sure the scene is clean and ready for a snapshot"""

        self.check_file_busy(file)

        selection = []
        beziers_with_controls = []
        hovered_items = []

        try:
            white = QtCore.Qt.white
            self.scene().setBackgroundBrush(white)

            selection = list(self.scene().selectedItems())
            for item in selection:
                item.setSelected(False)

            beziers_with_controls = [
                item
                for item in self.scene().items()
                if isinstance(item, BezierCurve) and item.h1
            ]
            for bezier in beziers_with_controls:
                bezier.remove_controls()

            hovered_items = [
                item
                for item in self.scene().items()
                if isinstance(item, HoverableItem) and item.is_hovered()
            ]
            for item in hovered_items:
                item.set_hovered(False)

            if self.scene().settings.rotate_scene:
                self.scene().pivot.setVisible(False)

            if self.scene().boundary:
                self.scene().boundary.setVisible(False)

            yield

        finally:
            if self.scene().boundary:
                self.scene().boundary.setVisible(True)

            if self.scene().settings.rotate_scene:
                self.scene().pivot.setVisible(True)

            for item in hovered_items:
                item.set_hovered(True)

            for bezier in beziers_with_controls:
                bezier.add_controls()

            for item in selection:
                item.setSelected(True)

            mid = QtWidgets.QApplication.instance().palette().mid()
            self.scene().setBackgroundBrush(mid)

    def get_render_rects(self) -> tuple[QtCore.QRect, QtCore.QRect]:
        """Return a tuple of rects for rendering: (target, source)"""
        if self.scene().boundary:
            source = self.scene().boundary.rect()
        else:
            source = self.viewport().rect()

        scale = self.transform().m11()

        source = self.mapFromScene(source).boundingRect()
        target = QtCore.QRect(0, 0, source.width() / scale, source.height() / scale)

        return (target, source)

    def check_file_busy(self, file: str):
        try:
            with open(file, "ab") as _:
                pass
        except Exception as exception:
            raise Exception(
                f"Unable to open file: {repr(file)}. Is it being used by another program?"
            ) from exception

    def check_painter_begin(self, ok: bool, file: str):
        if not ok:
            raise Exception(f"Unable to paint file: {repr(file)}")

    def export_svg(self, file: str):
        with self.prepare_export(file):
            target, source = self.get_render_rects()

            generator = QtSvg.QSvgGenerator()
            generator.setFileName(file)
            generator.setSize(QtCore.QSize(target.width(), target.height()))
            generator.setViewBox(target)

            painter = QtGui.QPainter()
            ok = painter.begin(generator)
            self.check_painter_begin(ok, file)
            self.render(painter, target, source)
            painter.end()

    def export_pdf(self, file: str):
        with self.prepare_export(file):
            target, source = self.get_render_rects()
            size = QtCore.QSizeF(target.width(), target.height())
            page_size = QtGui.QPageSize(size, QtGui.QPageSize.Unit.Point)

            writer = QtGui.QPdfWriter(file)
            writer.setPageSize(page_size)

            painter = QtGui.QPainter()
            ok = painter.begin(writer)
            self.check_painter_begin(ok, file)
            self.render(painter, QtCore.QRect(), source)
            painter.end()

    def export_png(self, file: str):
        with self.prepare_export(file):
            target, source = self.get_render_rects()

            pixmap = QtGui.QPixmap(target.width(), target.height())
            pixmap.fill(QtCore.Qt.white)

            painter = QtGui.QPainter()
            ok = painter.begin(pixmap)
            self.check_painter_begin(ok, file)
            painter.setRenderHint(QtGui.QPainter.Antialiasing)
            self.render(painter, target, source)
            painter.end()

            self.scene().boundary.setVisible(True)
            pixmap.save(file)
