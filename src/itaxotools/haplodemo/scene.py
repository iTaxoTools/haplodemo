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

from PySide6 import QtCore, QtGui, QtOpenGLWidgets, QtSvg, QtWidgets

from collections import defaultdict
from contextlib import contextmanager
from dataclasses import dataclass

import networkx as nx
from itaxotools.common.bindings import (
    Binder, Instance, Property, PropertyObject)

from .items.bezier import BezierCurve
from .items.boundary import BoundaryEdgeHandle, BoundaryRect
from .items.legend import Legend
from .items.nodes import Edge, EdgeStyle, Label, Node, Vertex
from .items.scale import Scale
from .layout import modified_spring_layout
from .palettes import Palette
from .types import HaploNode, LayoutType


@dataclass
class Division:
    key: str
    color: str


class DivisionListModel(QtCore.QAbstractListModel):
    colorMapChanged = QtCore.Signal(object)

    def __init__(self, names=[], palette=Palette.Spring(), parent=None):
        super().__init__(parent)
        self._palette = palette
        self._default_color = palette.default
        self._divisions = list()
        self.set_divisions_from_keys(names)
        self.set_palette(palette)

        self.dataChanged.connect(self.handle_data_changed)
        self.modelReset.connect(self.handle_data_changed)

    def set_divisions_from_keys(self, keys):
        self.beginResetModel()
        palette = self._palette
        self._divisions = [Division(keys[i], palette[i]) for i in range(len(keys))]
        self.endResetModel()

    def set_palette(self, palette):
        self.beginResetModel()
        self._default_color = palette.default
        for index, division in enumerate(self._divisions):
            division.color = palette[index]
        self.endResetModel()

    def get_color_map(self):
        map = {d.key: d.color for d in self._divisions}
        return defaultdict(lambda: self._default_color, map)

    def handle_data_changed(self, *args, **kwargs):
        self.colorMapChanged.emit(self.get_color_map())

    def rowCount(self, parent=QtCore.QModelIndex()):
        return len(self._divisions)

    def data(self, index, role=QtCore.Qt.DisplayRole):
        if not index.isValid() or not (0 <= index.row() < self.rowCount()):
            return None

        key = self._divisions[index.row()].key
        color = self._divisions[index.row()].color

        if role == QtCore.Qt.DisplayRole:
            return key
        elif role == QtCore.Qt.EditRole:
            return color
        elif role == QtCore.Qt.DecorationRole:
            color = QtGui.QColor(color)
            pixmap = QtGui.QPixmap(16, 16)
            pixmap.fill(color)
            return QtGui.QIcon(pixmap)

        return None

    def setData(self, index, value, role=QtCore.Qt.EditRole):
        if not index.isValid() or not (0 <= index.row() < self.rowCount()):
            return False

        if role == QtCore.Qt.EditRole:
            color = value.strip()
            if not color.startswith('#'):
                color = '#' + color

            if not QtGui.QColor.isValidColor(color):
                return False

            self._divisions[index.row()].color = color
            self.dataChanged.emit(index, index)
            return True

        return False

    def flags(self, index):
        return QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable

    def all(self):
        return list(self._divisions)


class NodeSizeSettings(PropertyObject):
    a = Property(float, 10)
    b = Property(float, 2)
    c = Property(float, 0.2)
    d = Property(float, 1)
    e = Property(float, 0)
    f = Property(float, 5)

    def get_all_values(self):
        return [property.value for property in self.properties]


class ScaleSettings(PropertyObject):
    marks = Property(list, [5, 10, 20])


class Settings(PropertyObject):
    palette = Property(Palette, Palette.Spring())
    divisions = Property(DivisionListModel, Instance)
    highlight_color = Property(QtGui.QColor, QtCore.Qt.magenta)
    font = Property(QtGui.QFont, None)
    rotational_movement = Property(bool, True)
    recursive_movement = Property(bool, True)
    label_movement = Property(bool, False)

    show_legend = Property(bool, False)
    show_scale = Property(bool, False)

    layout = Property(LayoutType, LayoutType.ModifiedSpring)
    layout_scale = Property(float, 3)
    edge_length = Property(float, 100)

    node_sizes = Property(NodeSizeSettings, Instance)
    scale = Property(ScaleSettings, Instance)

    pen_width_nodes = Property(float, 1)
    pen_width_edges = Property(float, 2)

    node_label_template = Property(str, 'NAME')
    edge_label_template = Property(str, '(WEIGHT)')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.binder = Binder()
        self.binder.bind(self.properties.palette, self.divisions.set_palette)
        self.binder.bind(self.properties.palette, self.properties.highlight_color, lambda x: x.highlight)


class GraphicsScene(QtWidgets.QGraphicsScene):
    boundaryPlaced = QtCore.Signal()

    def __init__(self, settings, parent=None):
        super().__init__(parent)
        mid = QtWidgets.QApplication.instance().palette().mid()
        self.setBackgroundBrush(mid)

        self.settings = settings
        self.graph = None

        self.boundary_margin = 16
        self.hovered_item = None
        self.boundary = None
        self.legend = None
        self.scale = None

        self.binder = Binder()
        self.binder.bind(settings.properties.show_legend, self.show_legend)
        self.binder.bind(settings.properties.show_scale, self.show_scale)

    def event(self, event):
        if event.type() == QtCore.QEvent.GraphicsSceneLeave:
            self.mouseLeaveEvent(event)
        return super().event(event)

    def mouseLeaveEvent(self, event):
        if self.hovered_item:
            hover = QtWidgets.QGraphicsSceneHoverEvent()
            # hover.type = lambda: event.type()
            self.hovered_item.hoverLeaveEvent(hover)
            self.hovered_item = None

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            item = self.getItemAtPos(event.scenePos(), ignore_edges=True)
            if item and not isinstance(item, Legend) and not isinstance(item, Scale):
                item.mousePressEvent(event)
                item.grabMouse()
                event.accept()
            else:
                super().mousePressEvent(event)
        self.mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            item = self.mouseGrabberItem()
            if item:
                item.mouseReleaseEvent(event)
                item.ungrabMouse()
                event.accept()
        self.mouseMoveEvent(event)

    def mouseDoubleClickEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            item = self.getItemAtPos(event.scenePos())
            if item:
                item.mouseDoubleClickEvent(event)
                item.mouseReleaseEvent(event)
                event.accept()

    def mouseMoveEvent(self, event):
        if self.mouseGrabberItem() or event.buttons():
            super().mouseMoveEvent(event)
            return

        event.accept()

        hover = self._hoverEventFromMouseEvent(event)
        item = self.getItemAtPos(event.scenePos())

        if self.hovered_item:
            if item == self.hovered_item:
                item.hoverMoveEvent(hover)
                return
            self.hovered_item.hoverLeaveEvent(hover)

        self.hovered_item = item
        if item:
            item.hoverEnterEvent(hover)
        else:
            super().mouseMoveEvent(event)

    def _hoverEventFromMouseEvent(self, mouse):
        hover = QtWidgets.QGraphicsSceneHoverEvent()
        # hover.widget = lambda: mouse.widget()
        hover.setPos(mouse.pos())
        hover.setScenePos(mouse.scenePos())
        hover.setScreenPos(mouse.screenPos())
        hover.setLastPos(mouse.lastPos())
        hover.setLastScenePos(mouse.lastScenePos())
        hover.setLastScreenPos(mouse.lastScreenPos())
        hover.setModifiers(mouse.modifiers())
        hover.setAccepted(mouse.isAccepted())
        return hover

    def getItemAtPos(
            self, pos,
            ignore_edges=False,
            ignore_labels=None,
            ignore_boundary_handles=True,
            ignore_legend=False,
            ignore_scale=False,
    ):
        if ignore_labels is None:
            ignore_labels = not self.settings.label_movement

        point = QtGui.QVector2D(pos.x(), pos.y())
        closest_edge_item = None
        closest_edge_distance = float('inf')
        for item in super().items(pos):
            if isinstance(item, Scale) and not ignore_legend:
                return item
            if isinstance(item, Legend) and not ignore_scale:
                return item
            if isinstance(item, Vertex):
                return item
            if isinstance(item, Label):
                if not ignore_labels:
                    return item
            if isinstance(item, Edge) and not ignore_edges:
                line = item.line()
                p1 = item.mapToScene(line.p1())
                p1 = QtGui.QVector2D(p1.x(), p1.y())
                unit = line.unitVector()
                unit = QtGui.QVector2D(unit.dx(), unit.dy())
                distance = point.distanceToLine(p1, unit)
                if distance < closest_edge_distance:
                    closest_edge_distance = distance
                    closest_edge_item = item
            if isinstance(item, BoundaryEdgeHandle) and not ignore_boundary_handles:
                return item
        if closest_edge_item:
            return closest_edge_item
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

    def set_boundary_to_contents(self):
        bounds = QtCore.QRectF()
        for item in self.items():
            if not isinstance(item, Node):
                continue
            rect = QtCore.QRectF(item.rect())
            rect.translate(item.pos())
            bounds = bounds.united(rect)

        bounds.adjust(
            - self.boundary_margin,
            - self.boundary_margin,
            self.boundary_margin,
            self.boundary_margin,
        )

        self.set_boundary_rect(
            bounds.x(),
            bounds.y(),
            bounds.width(),
            bounds.height(),
        )

    def show_legend(self, value=True):
        if not self.legend:
            self.legend = Legend(self.settings.divisions.all())
            self.addItem(self.legend)
            self.binder.bind(self.settings.divisions.colorMapChanged, self.legend.update_colors)
            self.binder.bind(self.settings.properties.highlight_color, self.legend.set_highlight_color)
            self.binder.bind(self.settings.properties.pen_width_nodes, self.legend.set_pen_width)
            self.binder.bind(self.settings.properties.font, self.legend.set_label_font)
        self.legend.setVisible(value)
        self.position_legend()

    def show_scale(self, value=True):
        if not self.scale:
            self.scale = Scale(self.settings)
            self.addItem(self.scale)
            self.binder.bind(self.settings.scale.properties.marks, self.scale.set_marks)
            self.binder.bind(self.settings.properties.highlight_color, self.scale.set_highlight_color)
            self.binder.bind(self.settings.properties.pen_width_nodes, self.scale.set_pen_width)
            self.binder.bind(self.settings.properties.font, self.scale.set_label_font)
            for property in self.settings.node_sizes.properties:
                self.binder.bind(property, self.scale.update_radii)
        self.scale.setVisible(value)
        self.position_scale()

    def position_legend(self):
        if not self.boundary:
            return
        bounds = self.boundary.rect()
        width = self.legend.rect().width()
        margin = self.legend.margin
        self.legend.setPos(
            bounds.x() + bounds.width() - width - margin,
            bounds.y() + margin)

    def position_scale(self):
        if not self.boundary:
            return
        bounds = self.boundary.rect()
        scale = self.scale.get_extended_rect()
        margin = self.legend.margin
        self.scale.setPos(
            bounds.x() + bounds.width() - scale.width() - margin,
            bounds.y() + bounds.height() - scale.height() - margin)

    def addBezier(self):
        item = BezierCurve(QtCore.QPointF(0, 0), QtCore.QPointF(200, 0))
        self.addItem(item)
        item.setPos(60, 160)

    def addNodes(self):
        node1 = self.create_node(85, 70, 35, 'Alphanumerical', {'X': 4, 'Y': 3, 'Z': 2})
        self.addItem(node1)

        node2 = self.create_node(node1.pos().x() + 95, node1.pos().y() - 30, 20, 'Beta', {'X': 4, 'Z': 2})
        self.add_child_edge(node1, node2, 2)

        node3 = self.create_node(node1.pos().x() + 115, node1.pos().y() + 60, 25, 'C', {'Y': 6, 'Z': 2})
        self.add_child_edge(node1, node3, 3)

        node4 = self.create_node(node3.pos().x() + 60, node3.pos().y() - 30, 15, 'D', {'Y': 1})
        self.add_child_edge(node3, node4, 1)

        vertex1 = self.create_vertex(node3.pos().x() - 60, node3.pos().y() + 60)
        self.add_child_edge(node3, vertex1, 2)

        node5 = self.create_node(vertex1.pos().x() - 80, vertex1.pos().y() + 40, 30, 'Error', {'?': 1})
        self.add_child_edge(vertex1, node5, 4)

        node6 = self.create_node(vertex1.pos().x() + 60, vertex1.pos().y() + 20, 20, 'R', {'Z': 1})
        self.add_child_edge(vertex1, node6, 1)

        node7 = self.create_node(vertex1.pos().x() + 100, vertex1.pos().y() + 80, 10, 'S', {'Z': 1})
        self.add_sibling_edge(node6, node7, 2)

        node8 = self.create_node(vertex1.pos().x() + 20, vertex1.pos().y() + 80, 40, 'T', {'Y': 1})
        self.add_sibling_edge(node6, node8, 1)
        self.add_sibling_edge(node7, node8, 1)

        node9 = self.create_node(node7.pos().x() + 20, node7.pos().y() - 40, 5, 'x', {'Z': 1})
        self.add_child_edge(node7, node9, 1)

    def addManyNodes(self, dx, dy):
        for x in range(dx):
            nodex = self.create_node(20, 80 * x, 15, f'x{x}', {'X': 1})
            self.addItem(nodex)

            for y in range(dy):
                nodey = self.create_node(nodex.pos().x() + 80 + 40 * y, nodex.pos().y() + 40, 15, f'y{y}', {'Y': 1})
                self.add_child_edge(nodex, nodey)

    def style_edges(self, style_default=EdgeStyle.Bubbles, cutoff=3):
        if not cutoff:
            cutoff = float('inf')
        style_cutoff = {
            EdgeStyle.Bubbles: EdgeStyle.DotsWithText,
            EdgeStyle.Bars: EdgeStyle.Collapsed,
            EdgeStyle.Plain: EdgeStyle.PlainWithText,
        }[style_default]
        edges = (item for item in self.items() if isinstance(item, Edge))

        for edge in edges:
            style = style_default if edge.segments <= cutoff else style_cutoff
            edge.set_style(style)

    def style_nodes(self):
        args = self.settings.node_sizes.get_all_values()
        nodes = (item for item in self.items() if isinstance(item, Node))
        edges = (item for item in self.items() if isinstance(item, Edge))
        for node in nodes:
            node.adjust_radius(*args)
        for edge in edges:
            edge.adjustPosition()

    def style_labels(self, node_label_template, edge_label_template):
        node_label_format = node_label_template.replace('NAME', '{name}').replace('WEIGHT', '{weight}')
        edge_label_format = edge_label_template.replace('WEIGHT', '{weight}')
        nodes = (item for item in self.items() if isinstance(item, Node))
        edges = (item for item in self.items() if isinstance(item, Edge))
        for node in nodes:
            text = node_label_format.format(name=node.name, weight=node.weight)
            node.label.setText(text)
        for edge in edges:
            text = edge_label_format.format(weight=edge.weight)
            edge.label.setText(text)

    def add_nodes_from_tree(self, tree: HaploNode):
        self.graph = nx.Graph()
        self.clear()

        self._add_nodes_from_tree_recursive(None, tree)
        self.style_nodes()
        self.layout_nodes()
        self.set_boundary_to_contents()

    def _add_nodes_from_tree_recursive(self, parent_id: str, node: HaploNode):
        x, y = 0, 0
        id = node.id
        size = node.pops.total()
        args = self.settings.node_sizes.get_all_values()
        radius = Node.radius_from_size(size, *args)
        radius /= self.settings.edge_length

        if size > 0:
            item = self.create_node(x, y, size, id, dict(node.pops))
        else:
            item = self.create_vertex(x, y)
        self.graph.add_node(id, radius=radius, item=item)

        if parent_id:
            parent_item = self.graph.nodes[parent_id]['item']
            parent_radius = self.graph.nodes[parent_id]['radius']
            length = node.mutations + parent_radius + radius
            item = self.add_child_edge(parent_item, item, node.mutations)
            self.graph.add_edge(parent_id, id, length=length)
        else:
            self.addItem(item)

        for child in node.children:
            self._add_nodes_from_tree_recursive(id, child)

    def create_vertex(self, *args, **kwargs):
        item = Vertex(*args, **kwargs)
        self.binder.bind(self.settings.properties.rotational_movement, item.set_rotational_setting)
        self.binder.bind(self.settings.properties.recursive_movement, item.set_recursive_setting)
        self.binder.bind(self.settings.properties.highlight_color, item.set_highlight_color)
        self.binder.bind(self.settings.properties.pen_width_edges, item.set_pen_width)
        return item

    def create_node(self, *args, **kwargs):
        item = Node(*args, **kwargs)
        item.update_colors(self.settings.divisions.get_color_map())
        self.binder.bind(self.settings.divisions.colorMapChanged, item.update_colors)
        self.binder.bind(self.settings.properties.rotational_movement, item.set_rotational_setting)
        self.binder.bind(self.settings.properties.recursive_movement, item.set_recursive_setting)
        self.binder.bind(self.settings.properties.label_movement, item.label.set_locked, lambda x: not x)
        self.binder.bind(self.settings.properties.highlight_color, item.label.set_highlight_color)
        self.binder.bind(self.settings.properties.highlight_color, item.set_highlight_color)
        self.binder.bind(self.settings.properties.pen_width_nodes, item.set_pen_width)
        self.binder.bind(self.settings.properties.font, item.set_label_font)
        return item

    def create_edge(self, *args, **kwargs):
        item = Edge(*args, **kwargs)
        self.binder.bind(self.settings.properties.highlight_color, item.set_highlight_color)
        self.binder.bind(self.settings.properties.label_movement, item.label.set_locked, lambda x: not x)
        self.binder.bind(self.settings.properties.highlight_color, item.label.set_highlight_color)
        self.binder.bind(self.settings.properties.pen_width_edges, item.set_pen_width)
        self.binder.bind(self.settings.properties.font, item.set_label_font)
        return item

    def add_child_edge(self, parent, child, segments=1):
        edge = self.create_edge(parent, child, segments)
        parent.addChild(child, edge)
        self.addItem(edge)
        self.addItem(child)
        return edge

    def add_sibling_edge(self, vertex, sibling, segments=1):
        edge = self.create_edge(vertex, sibling, segments)
        vertex.addSibling(sibling, edge)
        self.addItem(edge)
        if not sibling.scene():
            self.addItem(sibling)
        return edge

    def layout_nodes(self):
        match self.settings.layout:
            case LayoutType.Spring:
                graph = nx.Graph()
                for node, data in self.graph.nodes(data=True):
                    graph.add_node(node, **data)
                for u, v, data in self.graph.edges(data=True):
                    weight = 1 / data['length']
                    graph.add_edge(u, v, weight=weight, **data)
                pos = nx.spring_layout(graph, weight='weight', scale=self.settings.layout_scale)
                del graph
            case LayoutType.ModifiedSpring:
                pos = modified_spring_layout(self.graph, scale=None)
            case _:
                return

        for id, attrs in self.graph.nodes.items():
            x, y = pos[id]
            x *= self.settings.edge_length
            y *= self.settings.edge_length
            item = attrs['item']
            item.setPos(x, y)
            item.update()

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

    def clear(self):
        super().clear()
        self.boundary = None
        self.legend = None
        self.scale = None

        self.binder.unbind_all()
        self.binder.bind(self.settings.properties.show_legend, self.show_legend)
        self.binder.bind(self.settings.properties.show_scale, self.show_scale)


class GraphicsView(QtWidgets.QGraphicsView):
    scaled = QtCore.Signal(float)

    def __init__(self, scene=None, opengl=False, parent=None):
        super().__init__(parent)

        self.locked_center = None
        self.zoom_factor = 1.10
        self.zoom_maximum = 4.0
        self.zoom_minimum = 0.1

        self.setScene(scene)

        self.setRenderHints(QtGui.QPainter.TextAntialiasing)
        self.setRenderHints(QtGui.QPainter.Antialiasing)
        self.setDragMode(QtWidgets.QGraphicsView.NoDrag)
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOn)
        self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOn)
        self.setViewportUpdateMode(QtWidgets.QGraphicsView.FullViewportUpdate)
        self.setTransformationAnchor(QtWidgets.QGraphicsView.AnchorUnderMouse)

        if opengl:
            self.enable_opengl()

    def setScene(self, scene):
        super().setScene(scene)
        scene.boundaryPlaced.connect(self.initializeSceneRect)
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
            - 2 * rect.width(),
            - 2 * rect.height(),
            + 2 * rect.width(),
            + 2 * rect.height(),
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
        item = self.scene().getItemAtPos(pos, ignore_boundary_handles=False)
        if not item and event.button() == QtCore.Qt.LeftButton:
            self.setDragMode(QtWidgets.QGraphicsView.ScrollHandDrag)

        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self.setDragMode(QtWidgets.QGraphicsView.NoDrag)
            self.adjustSceneRect()
            self.lock_center()

        super().mouseReleaseEvent(event)

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
    def prepare_export(self):
        """Make sure the scene is clean and ready for a snapshot"""
        event = QtWidgets.QGraphicsSceneEvent(QtCore.QEvent.GraphicsSceneLeave)
        self.scene().mouseLeaveEvent(event)

        white = QtCore.Qt.white
        self.scene().setBackgroundBrush(white)

        if self.scene().boundary:
            self.scene().boundary.setVisible(False)

        yield

        if self.scene().boundary:
            self.scene().boundary.setVisible(True)

        mid = QtWidgets.QApplication.instance().palette().mid()
        self.scene().setBackgroundBrush(mid)

    def get_render_rects(self) -> tuple[QtCore.QRect, QtCore.QRect]:
        """Return a tuple of rects for rendering: (target, source)"""
        if self.scene().boundary:
            source = self.scene().boundary.rect()
        else:
            source = self.viewport().rect()

        source = self.mapFromScene(source).boundingRect()
        target = QtCore.QRect(0, 0, source.width(), source.height())

        return (target, source)

    def export_svg(self, file: str):
        with self.prepare_export():

            target, source = self.get_render_rects()

            generator = QtSvg.QSvgGenerator()
            generator.setFileName(file)
            generator.setSize(QtCore.QSize(target.width(), target.height()))
            generator.setViewBox(target)

            painter = QtGui.QPainter()
            painter.begin(generator)
            self.render(painter, target, source)
            painter.end()

    def export_pdf(self, file: str):
        with self.prepare_export():

            target, source = self.get_render_rects()
            size = QtCore.QSizeF(target.width(), target.height())
            page_size = QtGui.QPageSize(size, QtGui.QPageSize.Unit.Point)

            writer = QtGui.QPdfWriter(file)
            writer.setPageSize(page_size)

            painter = QtGui.QPainter()
            painter.begin(writer)
            self.render(painter, QtCore.QRect(), source)
            painter.end()

    def export_png(self, file: str):
        with self.prepare_export():

            target, source = self.get_render_rects()

            # Double PNG canvas
            target.setWidth(target.width() * 2)
            target.setHeight(target.height() * 2)

            pixmap = QtGui.QPixmap(target.width(), target.height())
            pixmap.fill(QtCore.Qt.white)

            painter = QtGui.QPainter()
            painter.begin(pixmap)
            painter.setRenderHint(QtGui.QPainter.Antialiasing)
            self.render(painter, target, source)
            painter.end()

            self.scene().boundary.setVisible(True)
            pixmap.save(file)
