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

from PySide6 import QtCore, QtWidgets

from collections import Counter, defaultdict
from itertools import combinations
from typing import Callable

import networkx as nx
import yaml

from itaxotools.common.bindings import Binder
from itaxotools.common.utility import Guard

from .items.bezier import BezierCurve
from .items.boundary import BoundaryRect
from .items.boxes import RectBox
from .items.edges import Edge, EdgeStyle
from .items.legend import Legend
from .items.nodes import Node, Vertex
from .items.scale import Scale
from .layout import modified_spring_layout
from .models import PartitionListModel
from .scene import GraphicsScene
from .settings import Settings
from .types import HaploGraph, HaploTreeNode, LayoutType


class Visualizer(QtCore.QObject):
    """Map haplotype network datatypes to graphics scene items"""

    nodeSelected = QtCore.Signal(str)
    nodeIndexSelected = QtCore.Signal(QtCore.QModelIndex)

    def __init__(self, scene: GraphicsScene, settings: Settings):
        super().__init__()
        self.scene = scene
        self.settings = settings

        self.binder = Binder()

        self.items: dict[str, Vertex] = {}
        self.members: dict[str, set[str]] = defaultdict(set)
        self.member_indices: dict[str, QtCore.QModelIndex] = defaultdict(
            QtCore.QModelIndex
        )
        self.partition: dict[str, str] = defaultdict(str)
        self.graph: HaploGraph = None
        self.tree: HaploTreeNode = None

        self._member_select_guard = Guard()

        self.scene.selectionChanged.connect(self.handle_selection_changed)
        self.settings.properties.partition_index.notify.connect(
            self.handle_partition_selected
        )

        q_app = QtWidgets.QApplication.instance()
        q_app.aboutToQuit.connect(self.handle_about_to_quit)

    def clear(self):
        """If visualizer is used, scene should be cleared through here to
        properly unbind settings from older objects"""
        self.binder.unbind_all()
        self.scene.clear()

        self.settings.divisions.set_divisions_from_keys([])
        self.settings.partitions.set_partitions([])
        self.settings.members.set_dict({})

        self.items = {}
        self.members = defaultdict(set)
        self.partition = defaultdict(str)
        self.graph = None
        self.tree = None

    def update_members_setting(self):
        self.settings.members.set_dict(self.members)
        self.member_indices = self.settings.members.get_index_map()

    def set_divisions(self, divisions: list[str]):
        self.settings.divisions.set_divisions_from_keys(divisions)

    def set_divisions_from_tree(self, tree: HaploTreeNode):
        divisions_set = set()
        self._get_tree_divisions(divisions_set, tree)
        self.set_divisions(list(sorted(divisions_set)))

    def _get_tree_divisions(self, divisions: set, node: HaploTreeNode):
        divisions.update(node.pops.keys())
        for child in node.children:
            self._get_tree_divisions(divisions, child)

    def set_divisions_from_graph(self, haplo_graph: HaploGraph):
        divisions_set = set()
        for node in haplo_graph.nodes:
            divisions_set.update(node.pops.keys())
        self.set_divisions(list(sorted(divisions_set)))

    def set_partitions(self, partitions: iter[tuple[str, dict[str, str]]]):
        self.settings.partitions.set_partitions(partitions)
        self.scene.set_boundary_to_contents()

    def set_partition(self, partition: dict[str, str]):
        self.partition = defaultdict(str, partition)
        divisions_set = {subset for subset in partition.values()}
        self.set_divisions(list(sorted(divisions_set)))
        if self.items:
            self.colorize_nodes()

    def visualize_tree(self, tree: HaploTreeNode):
        self.clear()

        self.set_divisions_from_tree(tree)

        self.graph = nx.Graph()
        self.tree = tree

        radius_for_weight = self.settings.node_sizes.radius_for_weight
        self._visualize_tree_recursive(None, tree, radius_for_weight)
        self.update_members_setting()
        self.layout_nodes()

        self.scene.style_labels()
        self.scene.set_marks_from_nodes()
        self.scene.set_boundary_to_contents()

    def _visualize_tree_recursive(
        self,
        parent_id: str,
        node: HaploTreeNode,
        radius_for_weight: Callable[[int], float],
    ):
        x, y = 0, 0
        id = node.id
        size = node.get_size()

        if size > 0:
            item = self.create_node(x, y, size, id, dict(node.pops), radius_for_weight)
            radius = item.radius / self.settings.edge_length
        else:
            item = self.create_vertex(x, y, id)
            radius = 0

        self.members[id] = node.members
        self.graph.add_node(id, radius=radius)

        if parent_id:
            parent_item = self.items[parent_id]
            parent_radius = self.graph.nodes[parent_id]["radius"]
            length = node.mutations + parent_radius + radius
            item = self.add_child_edge(parent_item, item, node.mutations)
            self.graph.add_edge(parent_id, id, length=length)
        else:
            self.scene.addItem(item)
            self.scene.root = item

        for child in node.children:
            self._visualize_tree_recursive(id, child, radius_for_weight)

    def visualize_graph(self, haplo_graph: HaploGraph):
        self.clear()

        self.set_divisions_from_graph(haplo_graph)

        self.graph = nx.Graph()
        self.tree = None

        x, y = 0, 0
        radius_for_weight = self.settings.node_sizes.radius_for_weight

        for node in haplo_graph.nodes:
            id = node.id
            size = node.get_size()

            if size > 0:
                item = self.create_node(
                    x, y, size, id, dict(node.pops), radius_for_weight
                )
                radius = item.radius / self.settings.edge_length
            else:
                item = self.create_vertex(x, y, id)
                radius = 0

            self.members[id] = node.members
            self.graph.add_node(id, radius=radius)
            self.scene.addItem(item)

            self.scene.root = self.scene.root or item

        for edge in haplo_graph.edges:
            node_a = haplo_graph.nodes[edge.node_a].id
            node_b = haplo_graph.nodes[edge.node_b].id
            item_a = self.items[node_a]
            item_b = self.items[node_b]
            radius_a = self.graph.nodes[node_a]["radius"]
            radius_b = self.graph.nodes[node_b]["radius"]
            length = edge.mutations + radius_a + radius_b
            item = self.add_sibling_edge(item_a, item_b, edge.mutations)
            self.graph.add_edge(node_a, node_b, length=length)

        self.layout_nodes()
        self.update_members_setting()

        self.scene.style_labels()
        self.scene.set_marks_from_nodes()
        self.scene.set_boundary_to_contents()

    def layout_nodes(self):
        match self.settings.layout:
            case LayoutType.Spring:
                graph = nx.Graph()
                for node, data in self.graph.nodes(data=True):
                    graph.add_node(node, **data)
                for u, v, data in self.graph.edges(data=True):
                    weight = 1 / data["length"]
                    graph.add_edge(u, v, weight=weight, **data)
                pos = nx.spring_layout(
                    graph, weight="weight", scale=self.settings.layout_scale
                )
                del graph
            case LayoutType.ModifiedSpring:
                pos = modified_spring_layout(self.graph, scale=None)
            case _:
                return

        for id in self.graph.nodes:
            x, y = pos[id]
            x *= self.settings.edge_length
            y *= self.settings.edge_length
            item = self.items[id]
            item.setPos(x, y)
            item.update()

    def colorize_nodes(self):
        color_map = self.settings.divisions.get_color_map()
        for id, item in self.items.items():
            if not isinstance(item, Node):
                continue
            weights = Counter(self.partition[member] for member in self.members[id])
            item.weights = dict(weights)
            item.update_colors(color_map)

    def visualize_haploweb(self):
        if not self.members:
            return
        edges: dict[tuple[str, str], int] = {}
        for x, y in combinations(self.members, 2):
            common = self.members[x] & self.members[y]
            edges[(x, y)] = len(common)

        groups: list[str] = self._find_groups_from_edges(edges)

        for (x, y), v in edges.items():
            if v > 0:
                bezier = self.create_bezier(self.items[x], self.items[y])
                bezier.bump(0.3)

        for group in groups:
            self.create_rect_box([self.items[x] for x in group])

        grouped_nodes = {name for group in groups for name in group}
        isolated_nodes = set(self.members.keys()) - grouped_nodes

        for name in isolated_nodes:
            if self.members[name]:
                self.create_rect_box([self.items[name]])

    def _find_groups_from_edges(self, edges: dict[tuple[str, str], int]):
        graph = defaultdict(set)
        for (a, b), v in edges.items():
            if v > 0:
                graph[a].add(b)
                graph[b].add(a)

        visited: set[str] = set()
        groups: list[set[str]] = []

        for node in graph:
            if node not in visited:
                group = self._find_group_for_node(graph, node, visited)
                groups.append(group)

        return groups

    def _find_group_for_node(
        self, graph: dict[str, set[str]], node: str, visited: set[str]
    ) -> set[str]:
        group = set()
        self._find_group_for_node_dfs(graph, node, visited, group)
        return group

    def _find_group_for_node_dfs(
        self, graph: dict[str, set[str]], node: str, visited: set[str], group: set[str]
    ):
        visited.add(node)
        group.add(node)
        for child in graph[node]:
            if child not in visited:
                self._find_group_for_node_dfs(graph, child, visited, group)

    def create_vertex(self, x: float, y: float, id: str):
        assert id not in self.items
        item = Vertex(x, y, 0, id)
        self.items[id] = item
        self.binder.bind(
            self.settings.properties.snapping_movement, item.set_snapping_setting
        )
        self.binder.bind(
            self.settings.properties.rotational_movement, item.set_rotational_setting
        )
        self.binder.bind(
            self.settings.properties.recursive_movement, item.set_recursive_setting
        )
        self.binder.bind(
            self.settings.properties.highlight_color, item.set_highlight_color
        )
        self.binder.bind(self.settings.properties.pen_width_edges, item.set_pen_width)
        return item

    def create_node(
        self,
        x: float,
        y: float,
        size: int,
        id: str,
        weights: dict[str, int],
        func: Callable,
    ):
        assert id not in self.items
        item = Node(x, y, size, id, weights, func)
        self.items[id] = item
        item.update_colors(self.settings.divisions.get_color_map())
        self.binder.bind(self.settings.divisions.colorMapChanged, item.update_colors)
        self.binder.bind(
            self.settings.properties.snapping_movement, item.set_snapping_setting
        )
        self.binder.bind(
            self.settings.properties.rotational_movement, item.set_rotational_setting
        )
        self.binder.bind(
            self.settings.properties.recursive_movement, item.set_recursive_setting
        )
        self.binder.bind(
            self.settings.properties.label_movement,
            item.label.set_locked,
            lambda x: not x,
        )
        self.binder.bind(
            self.settings.properties.highlight_color, item.set_highlight_color
        )
        self.binder.bind(self.settings.properties.pen_width_nodes, item.set_pen_width)
        self.binder.bind(self.settings.properties.font, item.set_label_font)
        return item

    def create_edge(self, *args, **kwargs):
        item = Edge(*args, **kwargs)
        self.binder.bind(
            self.settings.properties.highlight_color, item.set_highlight_color
        )
        self.binder.bind(
            self.settings.properties.label_movement,
            item.label.set_locked,
            lambda x: not x,
        )
        self.binder.bind(self.settings.properties.pen_width_edges, item.set_pen_width)
        self.binder.bind(self.settings.properties.font, item.set_label_font)
        return item

    def create_rect_box(self, vertices):
        item = RectBox(vertices)
        for vertex in vertices:
            vertex.boxes.append(item)
        self.scene.addItem(item)
        item.adjust_position()
        return item

    def create_bezier(self, node1, node2):
        item = BezierCurve(node1, node2)
        self.binder.bind(
            self.settings.properties.highlight_color, item.set_highlight_color
        )
        self.binder.bind(self.settings.properties.pen_width_edges, item.set_pen_width)
        node1.beziers[node2] = item
        node2.beziers[node1] = item
        self.scene.addItem(item)
        return item

    def add_child_edge(self, parent, child, segments=1):
        edge = self.create_edge(parent, child, segments)
        parent.addChild(child, edge)
        self.scene.addItem(edge)
        self.scene.addItem(child)
        return edge

    def add_sibling_edge(self, vertex, sibling, segments=1):
        edge = self.create_edge(vertex, sibling, segments)
        vertex.addSibling(sibling, edge)
        self.scene.addItem(edge)
        if not sibling.scene():
            self.scene.addItem(sibling)
        return edge

    def handle_about_to_quit(self):
        self.scene.selectionChanged.disconnect(self.handle_selection_changed)

    def handle_partition_selected(self, index):
        partition = index.data(PartitionListModel.PartitionRole)
        if partition is not None:
            self.set_partition(partition.map)

    def handle_selection_changed(self):
        selection = self.scene.selectedItems()
        selection = [item for item in selection if isinstance(item, Vertex)]

        node = selection[0] if selection else None
        name = node.name if node else ""
        index = self.member_indices[name]

        if not self._member_select_guard:
            self.nodeSelected.emit(node)
            self.nodeIndexSelected.emit(index)

    def select_node_by_name(self, name: str):
        with self._member_select_guard:
            for item in self.scene.selectedItems():
                item.setSelected(False)

            if not name:
                return

            item = self.items[name]
            item.setSelected(True)

    def _dump_vertex_layout(self, item: Node) -> dict:
        return {
            "name": item.name if item.name else "",
            "x": item.x(),
            "y": item.y(),
        }

    def _dump_node_layout(self, item: Node) -> dict:
        return {
            "name": item.name,
            "x": item.x(),
            "y": item.y(),
            "label": {
                "x": item.label.rect.center().x(),
                "y": item.label.rect.center().y(),
            },
        }

    def _dump_edge(self, item: Edge) -> dict:
        return {
            "node_a": item.node1.name,
            "node_b": item.node2.name,
            "style": item.style.value,
            "label": {
                "x": item.label.rect.center().x(),
                "y": item.label.rect.center().y(),
            },
        }

    def _dump_boundary(self, item: BoundaryRect) -> dict:
        return {
            "x": item.rect().x(),
            "y": item.rect().y(),
            "w": item.rect().width(),
            "h": item.rect().height(),
        }

    def _dump_legend(self, item: Legend) -> dict:
        return {
            "x": item.pos().x(),
            "y": item.pos().y(),
        }

    def _dump_scale(self, item: Scale) -> dict:
        return {
            "x": item.x(),
            "y": item.y(),
            "marks": {
                mark: {
                    "x": label.rect.center().x(),
                    "y": label.rect.center().y(),
                }
                for mark, label in zip(item.marks, item.labels)
            },
        }

    def dump_dict(self) -> dict:
        nodes = []
        edges = []
        boundary = None
        legend = None
        scale = None
        for item in self.scene.items():
            if isinstance(item, Node):
                node = self._dump_node_layout(item)
                nodes.append(node)
            elif isinstance(item, Vertex):
                node = self._dump_vertex_layout(item)
                nodes.append(node)
            elif isinstance(item, Edge):
                edge = self._dump_edge(item)
                edges.append(edge)
            elif isinstance(item, BoundaryRect):
                boundary = self._dump_boundary(item)
            elif isinstance(item, Legend):
                legend = self._dump_legend(item)
            elif isinstance(item, Scale):
                scale = self._dump_scale(item)
        return {
            "settings": self.settings.dump(),
            "graph": self.graph,
            "tree": self.tree,
            "members": dict(self.members),
            "layout": {
                "nodes": nodes,
                "edges": edges,
                "boundary": boundary,
                "legend": legend,
                "scale": scale,
            },
        }

    def _load_node_layout(self, data: dict):
        id = data["name"]
        if id not in self.items:
            return
        item = self.items[id]
        item.setPos(QtCore.QPointF(data["x"], data["y"]))
        if "label" not in data:
            return
        pos = data["label"]
        item.label.set_center_pos(pos["x"], pos["y"])

    def _load_edge_layout(self, data: dict):
        id_a = data["node_a"]
        id_b = data["node_b"]
        if id_a not in self.items:
            return
        if id_b not in self.items:
            return
        node_b = self.items[id_b]
        item = self.items[id_a].edges[node_b]
        style = EdgeStyle(data["style"])
        item.set_style(style)
        if "label" not in data:
            return
        pos = data["label"]
        item.label.set_center_pos(pos["x"], pos["y"])

    def _load_boundary(self, data: dict):
        boundary = self.scene.boundary
        if not boundary:
            return
        rect = QtCore.QRect(data["x"], data["y"], data["w"], data["h"])
        boundary.set_rect_and_update(rect)

    def _load_legend(self, data: dict):
        legend = self.scene.legend
        if not legend:
            return
        legend.setPos(QtCore.QPoint(data["x"], data["y"]))

    def _load_scale(self, data: dict):
        scale = self.scene.scale
        if not scale:
            return
        scale.setX(data["x"])
        scale.setY(data["y"])
        assert scale.marks == list(data["marks"].keys())
        for i, pos in enumerate(data["marks"].values()):
            scale.labels[i].set_center_pos(pos["x"], pos["y"])

    def load_dict(self, data: dict):
        self.settings.load(data["settings"])
        self.scene.style_nodes()
        self._load_boundary(data["layout"]["boundary"])
        self._load_legend(data["layout"]["legend"])
        self._load_scale(data["layout"]["scale"])
        for node in data["layout"]["nodes"]:
            self._load_node_layout(node)
        for edge in data["layout"]["edges"]:
            self._load_edge_layout(edge)

    def dump_yaml(self, path: str):
        with open(path, "w") as file:
            yaml.dump(self.dump_dict(), file)

    def load_yaml(self, path: str):
        with open(path, "r") as file:
            self.load_dict(yaml.safe_load(file))
