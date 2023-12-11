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

from typing import Callable

from itaxotools.common.utility import override

from .bezier import BezierCurve
from .boxes import RectBox
from .edges import Edge
from .labels import Label
from .protocols import HighlightableItem


class Vertex(HighlightableItem, QtWidgets.QGraphicsEllipseItem):
    def __init__(self, x: float, y: float, r: float = 0, name: str = None):
        super().__init__(-r, -r, r * 2, r * 2)

        self.name = name
        self.parent = None
        self.boxes: list[RectBox] = []
        self.children: list[Vertex] = []
        self.siblings: list[Vertex] = []
        self.beziers: dict[Vertex, BezierCurve] = {}
        self.edges: dict[Vertex, Edge] = {}

        self.weight = r
        self.radius = r

        self.locked_pos = None
        self.locked_event_pos = None
        self.locked_angle = None
        self.locked_center = None

        self.snap_angle_threshold = 8.0
        self.snap_angles = [45 * x for x in range(9)]

        self.snap_axis_threshold = 20.0
        self.snap_axis_threshold_base = 20.0
        self.snap_axis_threshold_factor = 10.0
        self.snap_axis_xs = []
        self.snap_axis_ys = []

        self._snapping_setting = None
        self._rotational_setting = None
        self._recursive_setting = None
        self._click_deselects = False
        self.in_scene_rotation = False
        self._pen_high_increment = 4
        self._pen_width = 2
        self._pen = QtGui.QPen(QtCore.Qt.black, 2)
        self._debug = False

        self.update_z_value()

        self.setCursor(QtCore.Qt.ArrowCursor)
        self.setFlag(QtWidgets.QGraphicsItem.ItemIsMovable, True)
        self.setFlag(QtWidgets.QGraphicsItem.ItemIsSelectable, True)
        self.setFlag(QtWidgets.QGraphicsItem.ItemSendsGeometryChanges, True)
        self.setAcceptedMouseButtons(QtCore.Qt.LeftButton)
        self.setPen(QtCore.Qt.NoPen)
        self.setBrush(self.pen().color())
        self.setPos(x, y)

    @override
    def paint(self, painter, options, widget=None):
        painter.setPen(QtCore.Qt.NoPen)
        center = QtCore.QPoint(0, 0)

        radius = self._pen_width * 1.5 + 1
        radius_high = radius + self._pen_high_increment

        center = QtCore.QPointF(0, 0)
        # Unless we use QPointF, bubble size isn't right
        self.paintBubble(painter, center, radius, radius_high)

        if self._debug:
            painter.setPen(QtCore.Qt.green)
            painter.drawRect(self.rect())
            painter.drawLine(-4, 0, 4, 0)
            painter.drawLine(0, -4, 0, 4)

    def paintBubble(self, painter, point, r=2.5, h=6):
        # Replicates Edge.paintBubble(), but can also be selected
        painter.setPen(QtCore.Qt.NoPen)
        if self.isSelected():
            painter.save()
            painter.setPen(self._pen)
            painter.setBrush(self.highlight_color())
            painter.drawEllipse(point, h + r / 2, h + r / 2)
            painter.restore()
        elif self.is_highlighted():
            painter.save()
            painter.setBrush(self.highlight_color())
            painter.drawEllipse(point, h, h)
            painter.restore()
        painter.setBrush(QtCore.Qt.black)
        painter.drawEllipse(point, r, r)

    @override
    def boundingRect(self):
        # Hack to prevent drag n draw glitch
        return self.rect().adjusted(-50, -50, 50, 50)

    @override
    def shape(self):
        path = QtGui.QPainterPath()
        x = self._pen_width + self._pen_high_increment * 1.4
        path.addEllipse(self.rect().adjusted(-x, -x, x, x))
        return path

    @override
    def itemChange(self, change, value):
        self.parentItem()
        if change == QtWidgets.QGraphicsItem.ItemPositionHasChanged:
            # should we be using signals instead?
            for bezier in self.beziers.values():
                bezier.adjust_position()
            for edge in self.edges.values():
                edge.adjust_position()
            for box in self.boxes:
                box.adjust_position()
        return super().itemChange(change, value)

    @override
    def hoverEnterEvent(self, event):
        super().hoverEnterEvent(event)
        self.set_hovered(True)

    @override
    def hoverLeaveEvent(self, event):
        super().hoverLeaveEvent(event)
        self.set_hovered(False)

    @override
    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self._click_deselects = self.isSelected()
            center = self.parent.scenePos() if self.parent else None
            for edge in self.edges.values():
                edge.lock_label_position()
            self.lockPosition(event, center)
            if self.isMovementRecursive():
                self.mapNodeEdgeRecursive(
                    type(self).lockPosition,
                    [event, center],
                    {},
                    Edge.lock_label_position,
                    [],
                    {},
                )

        super().mousePressEvent(event)

    @override
    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        if event.button() == QtCore.Qt.LeftButton:
            if self.isSelected() and self._click_deselects:
                self.setSelected(False)
            if self.locked_pos != self.pos():
                self.post_node_movement()

    @override
    def mouseMoveEvent(self, event):
        self._click_deselects = False
        if self.isMovementRotational():
            return self.moveRotationally(event)
        return self.moveOrthogonally(event)

    @override
    def mouseDoubleClickEvent(self, event):
        super().mouseDoubleClickEvent(event)
        self._click_deselects = False

    def update_z_value(self, hover=False):
        weight = self.weight
        if hover:
            weight -= 1
        z = 1 / (weight + 2)
        self.setZValue(z)

    def addChild(self, item, edge):
        item.parent = self
        item.edges[self] = edge
        self.edges[item] = edge
        self.children.append(item)
        edge.adjust_position()

    def addSibling(self, item, edge):
        item.edges[self] = edge
        self.edges[item] = edge
        self.siblings.append(item)
        item.siblings.append(self)
        edge.adjust_position()

    def set_hovered(self, value):
        if self.parent and any(
            (self.isMovementRotational(), self.isMovementRecursive())
        ):
            edge = self.edges[self.parent]
            edge.set_hovered(value)
        self.update_z_value(value)
        super().set_hovered(value)

    def set_snapping_setting(self, value):
        self._snapping_setting = value

    def set_rotational_setting(self, value):
        self._rotational_setting = value

    def set_recursive_setting(self, value):
        self._recursive_setting = value

    def set_pen_width(self, value):
        r = value
        self._pen_width = value
        self._pen = QtGui.QPen(QtCore.Qt.black, value)
        self.prepareGeometryChange()
        self.setRect(-r, -r, 2 * r, 2 * r)

    def isMovementRotational(self):
        if not self._rotational_setting:
            return False
        return isinstance(self.parent, Vertex)

    def isMovementRecursive(self):
        if self.in_scene_rotation:
            return False
        return self._recursive_setting

    def isMovementSnapping(self):
        if self.in_scene_rotation:
            return False
        return self._snapping_setting

    def _mapRecursive(
        self,
        siblings,
        parents,
        visited_nodes,
        visited_edges,
        node_func,
        node_args,
        node_kwargs,
        edge_func,
        edge_args,
        edge_kwargs,
    ):
        if self in visited_nodes:
            return
        visited_nodes.add(self)

        if node_func:
            node_func(self, *node_args, **node_kwargs)

        nodes = list(self.children)
        if siblings:
            nodes += list(self.siblings)
        if parents and self.parent is not None:
            nodes += [self.parent]

        for node in nodes:
            node._mapRecursive(
                True,
                parents,
                visited_nodes,
                visited_edges,
                node_func,
                node_args,
                node_kwargs,
                edge_func,
                edge_args,
                edge_kwargs,
            )

            edge = self.edges[node]
            if edge_func and edge not in visited_edges:
                edge_func(edge, *edge_args, **edge_kwargs)
            visited_edges.add(edge)

    def mapNodeRecursive(self, func, *args, **kwargs):
        self._mapRecursive(
            False, False, set(), set(), func, args, kwargs, None, None, None
        )

    def mapNodeEdgeRecursive(
        self,
        node_func,
        node_args,
        node_kwargs,
        edge_func,
        edge_args,
        edge_kwargs,
    ):
        self._mapRecursive(
            False,
            False,
            set(),
            set(),
            node_func,
            node_args,
            node_kwargs,
            edge_func,
            edge_args,
            edge_kwargs,
        )

    def lockPosition(self, event, center=None):
        self.locked_event_pos = event.scenePos()
        self.locked_pos = self.pos()
        for bezier in self.beziers.values():
            bezier.lock_control_points()

        if center is not None:
            line = QtCore.QLineF(center, event.scenePos())
            self.locked_angle = line.angle()
            self.locked_center = center

        if not self.isMovementRotational():
            self.snap_axis_xs = []
            self.snap_axis_ys = []
            if self.parent:
                self.snap_axis_xs += [self.parent.pos().x()]
                self.snap_axis_ys += [self.parent.pos().y()]
            if self.children and not self.isMovementRecursive():
                positions = [item.pos() for item in self.children]
                self.snap_axis_xs += [pos.x() for pos in positions]
                self.snap_axis_ys += [pos.y() for pos in positions]
            if self.siblings:
                positions = [item.pos() for item in self.siblings]
                self.snap_axis_xs += [pos.x() for pos in positions]
                self.snap_axis_ys += [pos.y() for pos in positions]

    def applyTranspose(self, diff):
        self.setPos(self.locked_pos + diff)

        for bezier in self.beziers.values():
            locked_bezier_pos = bezier.get_control_point_lock_for_node(self)
            bezier.set_control_point_for_node(self, locked_bezier_pos + diff)
            bezier.adjust_position()

    def applyTransform(self, transform):
        pos = transform.map(self.locked_pos)
        self.setPos(pos)

        for bezier in self.beziers.values():
            locked_bezier_pos = bezier.get_control_point_lock_for_node(self)
            new_bezier_pos = transform.map(locked_bezier_pos)
            bezier.set_control_point_for_node(self, new_bezier_pos)
            bezier.adjust_position()

    def moveOrthogonally(self, event):
        epos = event.scenePos()
        diff = epos - self.locked_event_pos

        if self.isMovementSnapping() and self.snap_axis_xs and self.snap_axis_ys:
            new_pos = self.locked_pos + diff

            diff_xs = [x - new_pos.x() for x in self.snap_axis_xs]
            diff_ys = [y - new_pos.y() for y in self.snap_axis_ys]

            abs_diff_xs = [abs(x) for x in diff_xs]
            abs_diff_ys = [abs(y) for y in diff_ys]

            min_abs_diff_x = min(abs_diff_xs)
            min_abs_diff_y = min(abs_diff_ys)

            if min_abs_diff_x < self.snap_axis_threshold:
                index_of_min_diff_x = abs_diff_xs.index(min_abs_diff_x)
                diff_x = diff_xs[index_of_min_diff_x]
                diff.setX(diff.x() + diff_x)

            if min_abs_diff_y < self.snap_axis_threshold:
                index_of_min_diff_y = abs_diff_ys.index(min_abs_diff_y)
                diff_y = diff_ys[index_of_min_diff_y]
                diff.setY(diff.y() + diff_y)

        if self.isMovementRecursive():
            return self.mapNodeRecursive(type(self).applyTranspose, diff)
        return self.applyTranspose(diff)

    def moveRotationally(self, event):
        epos = event.scenePos()
        line = QtCore.QLineF(self.locked_center, epos)
        angle = self.locked_angle - line.angle()
        center = self.locked_center

        transform = QtGui.QTransform()
        transform.translate(center.x(), center.y())
        transform.rotate(angle)
        transform.translate(-center.x(), -center.y())

        if self.isMovementSnapping():
            new_pos = transform.map(self.locked_pos)
            absolute_line = QtCore.QLineF(self.locked_center, new_pos)
            absolute_angle = absolute_line.angle()

            snap_diffs = [
                absolute_angle - snap_angle for snap_angle in self.snap_angles
            ]
            snap_abs_diffs = [abs(snap_diff) for snap_diff in snap_diffs]
            min_abs_diff = min(snap_abs_diffs)

            if min_abs_diff < self.snap_angle_threshold:
                index_of_min_diff = snap_abs_diffs.index(min_abs_diff)
                snap_diff = snap_diffs[index_of_min_diff]
                transform.translate(center.x(), center.y())
                transform.rotate(snap_diff)
                transform.translate(-center.x(), -center.y())

        if self.isMovementRecursive():
            return self.mapNodeRecursive(type(self).applyTransform, transform)
        return self.applyTransform(transform)

    def adjust_scale(self, scale=1.0):
        if not scale:
            return
        self.snap_axis_threshold = (
            self.snap_axis_threshold_base + self.snap_axis_threshold_factor / scale
        )

    def post_node_movement(self):
        if not self.scene():
            return
        self.scene().handle_node_movement(self)


class Node(Vertex):
    def __init__(
        self,
        x: float,
        y: float,
        r: float,
        name: str,
        weights: dict[str, int],
        radius_for_weight: Callable[[int], float] = None,
    ):
        super().__init__(x, y, r, name)
        self.weights = weights
        self.radius_for_weight = radius_for_weight
        self.pies = dict()

        self._pen = QtGui.QPen(QtCore.Qt.black, 2)
        self._pen_high = QtGui.QPen(self.highlight_color(), 4)
        self._pen_selected = QtGui.QPen(self.highlight_color(), 18)
        self._pen_high_increment = 2
        self._pen_width = 2

        self.label = Label(name, self)
        self.adjust_radius()

    @override
    def hoverEnterEvent(self, event):
        super().hoverEnterEvent(event)
        self.label.set_hovered(True)

    @override
    def hoverLeaveEvent(self, event):
        super().hoverLeaveEvent(event)
        self.label.set_hovered(False)

    @override
    def mouseDoubleClickEvent(self, event):
        super().mouseDoubleClickEvent(event)
        self.label.locked_rect = QtCore.QRect(self.label.rect)
        self.label.recenter()
        self.label.post_label_movement()

    @override
    def paint(self, painter, options, widget=None):
        self.paint_node(painter)
        self.paint_pies(painter)
        self.paint_outline(painter)

        if self._debug:
            painter.setPen(QtCore.Qt.green)
            painter.drawRect(self.rect())
            painter.drawLine(-4, 0, 4, 0)
            painter.drawLine(0, -4, 0, 4)

    def paint_node(self, painter):
        painter.save()
        if self.pies:
            painter.setPen(QtCore.Qt.NoPen)
        else:
            painter.setPen(self._pen)
        painter.setBrush(self.brush())
        painter.drawEllipse(self.rect())
        painter.restore()

    def paint_pies(self, painter):
        if not self.pies:
            return
        painter.save()

        painter.setPen(QtCore.Qt.NoPen)
        starting_angle = 16 * 90

        for color, span in self.pies.items():
            painter.setBrush(QtGui.QBrush(color))
            painter.drawPie(self.rect(), starting_angle, span)
            starting_angle += span

        painter.setBrush(QtCore.Qt.NoBrush)
        painter.setPen(self._pen)
        painter.drawEllipse(self.rect())
        painter.restore()

    def paint_outline(self, painter):
        painter.save()
        painter.setBrush(QtCore.Qt.NoBrush)

        if self.isSelected():
            painter.setPen(self._pen_selected)
            painter.drawEllipse(self.rect())
            painter.setPen(self._pen)
            painter.drawEllipse(self.rect())
        elif self.is_highlighted():
            painter.setPen(self._pen_high)
            painter.drawEllipse(self.rect())
        painter.restore()

    def update_colors(self, color_map):
        if not self.weights:
            self.setBrush(QtGui.QBrush(color_map[None]))
            return

        total_weight = sum(weight for weight in self.weights.values())

        weight_items = iter(self.weights.items())
        first_key, _ = next(weight_items)
        first_color = color_map[first_key]
        self.setBrush(QtGui.QBrush(first_color))

        self.pies = dict()
        for key, weight in weight_items:
            color = color_map[key]
            span = int(5760 * weight / total_weight)
            self.pies[color] = span

    @override
    def set_highlight_color(self, value):
        super().set_highlight_color(value)
        self.label.set_highlight_color(value)
        self.update_pens()

    def set_pen_width(self, value):
        self._pen_width = value
        self.update_pens()

    def update_pens(self):
        self._pen = QtGui.QPen(QtCore.Qt.black, self._pen_width)
        self._pen_high = QtGui.QPen(
            self.highlight_color(), self._pen_width + self._pen_high_increment
        )
        self._pen_selected = QtGui.QPen(
            self.highlight_color(), self._pen_width + self._pen_high_increment * 4
        )
        self.update()

    def set_label_font(self, value):
        self.label.set_font(value)

    def adjust_radius(self):
        if self.radius_for_weight:
            r = self.radius_for_weight(self.weight)
        else:
            r = self.weight
        self.radius = r

        self.prepareGeometryChange()
        self.setRect(-r, -r, 2 * r, 2 * r)
