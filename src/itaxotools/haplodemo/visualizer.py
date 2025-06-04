# -----------------------------------------------------------------------------
# Haplodemo - Visualize, edit and export haplotype networks
# Copyright (C) 2023-2025 Patmanidis Stefanos
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
from pathlib import Path
from typing import Callable

import networkx as nx
import yaml

from itaxotools.common.bindings import Binder
from itaxotools.common.utility import Guard

from ._version import __version__
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
        self.beziers: dict[tuple[str, str], BezierCurve] = {}
        self.weights: dict[str, dict[str, int]] = defaultdict(dict)
        self.members: dict[str, set[str]] = defaultdict(set)
        self.member_indices: dict[str, QtCore.QModelIndex] = defaultdict(
            QtCore.QModelIndex
        )
        self.partition: dict[str, str] = defaultdict(str)
        self.graph: nx.Graph = nx.Graph()
        self.tree: HaploTreeNode = None

        self._member_select_guard = Guard()
        self._node_index_count = 0

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
        self.beziers = {}
        self.weights = defaultdict(dict)
        self.members = defaultdict(set)
        self.partition = defaultdict(str)
        self.graph = nx.Graph()
        self.tree = None

        self._node_index_count = 0

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

    def set_divisions_from_weights(self, weights: dict[str, dict[str, int]] = None):
        weights = weights or self.weights
        divisions_set = {
            key for node_weights in weights.values() for key in node_weights
        }
        divisions_set.discard("?")
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
            item = self.create_node(
                x, y, size, id, dict(node.pops), radius_for_weight, node.members
            )
        else:
            item = self.create_vertex(x, y, id, node.members)

        if parent_id:
            parent_item = self.items[parent_id]
            item = self.add_child_edge(parent_item, item, node.mutations)
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
                    x, y, size, id, dict(node.pops), radius_for_weight, node.members
                )
            else:
                item = self.create_vertex(x, y, id, node.members)

            self.scene.addItem(item)

            self.scene.root = self.scene.root or item

        for edge in haplo_graph.edges:
            id_a = haplo_graph.nodes[edge.node_a].id
            id_b = haplo_graph.nodes[edge.node_b].id
            item_a = self.items[id_a]
            item_b = self.items[id_b]
            item = self.add_sibling_edge(item_a, item_b, edge.mutations)

        self.layout_nodes()
        self.update_members_setting()

        self.scene.style_labels()
        self.scene.set_marks_from_nodes()
        self.scene.set_boundary_to_contents()

    def visualize_network(
        self, graph: nx.Graph = None, weights: dict = None, members: dict = None
    ):
        self.graph = graph or self.graph
        self.weights = weights or self.weights
        self.members = members or self.members

        if not self.settings.divisions.all():
            self.set_divisions_from_weights()

        x, y = 0, 0
        radius_for_weight = self.settings.node_sizes.radius_for_weight

        for id, data in self.graph.nodes(data=True):
            size = data["weight"]
            if size > 0:
                item = self.create_node(
                    x,
                    y,
                    size,
                    id,
                    self.weights[id],
                    radius_for_weight,
                    self.members[id],
                )
            else:
                item = self.create_vertex(x, y, id, self.members[id])
            self.scene.addItem(item)
            self.scene.root = self.scene.root or item

        for u, v, data in self.graph.edges(data=True):
            item_u = self.items[u]
            item_v = self.items[v]
            mutations = data["mutations"]
            item = self.add_sibling_edge(item_u, item_v, mutations)

        self.scene.style_nodes()
        self.scene.style_labels()

    def _mod_radius_for_weight(self, radius: float) -> float:
        radius_for_weight = self.settings.node_sizes.radius_for_weight
        edge_length = self.settings.edge_length
        return radius_for_weight(radius) / edge_length

    def layout_nodes(self):
        match self.settings.layout:
            case LayoutType.Spring:
                graph = nx.Graph()
                for node, data in self.graph.nodes(data=True):
                    radius = self._mod_radius_for_weight(data["weight"])
                    graph.add_node(node, radius=radius)
                for u, v, data in self.graph.edges(data=True):
                    radius_a = graph.nodes[u]["radius"]
                    radius_b = graph.nodes[v]["radius"]
                    length = data["mutations"] + radius_a + radius_b
                    weight = 1 / length
                    graph.add_edge(u, v, weight=weight)
                pos = nx.spring_layout(
                    graph, weight="weight", scale=self.settings.layout_scale
                )
                del graph
            case LayoutType.ModifiedSpring:
                graph = nx.Graph()
                for node, data in self.graph.nodes(data=True):
                    radius = self._mod_radius_for_weight(data["weight"])
                    graph.add_node(node, radius=radius)
                for u, v, data in self.graph.edges(data=True):
                    radius_a = graph.nodes[u]["radius"]
                    radius_b = graph.nodes[v]["radius"]
                    length = data["mutations"] + radius_a + radius_b
                    graph.add_edge(u, v, length=length)
                pos = modified_spring_layout(graph, scale=None)
                del graph
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

        visible = self.settings.fields.show_groups

        for (x, y), v in edges.items():
            if v > 0:
                bezier = self.create_bezier(self.items[x], self.items[y], visible)
                bezier.bump(0.3)

        for group in groups:
            self.create_rect_box([self.items[x] for x in group], visible)

        grouped_nodes = {name for group in groups for name in group}
        isolated_nodes = set(self.members.keys()) - grouped_nodes

        visible = self.settings.fields.show_isolated

        for name in isolated_nodes:
            if self.members[name]:
                self.create_rect_box([self.items[name]], visible)

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

    def create_vertex(
        self,
        x: float,
        y: float,
        id: str,
        members: set[str] = {},
    ):
        assert id not in self.items
        item = Vertex(x, y, 0, id)
        item.index = self.get_next_node_index()
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
        self.graph.add_node(id, weight=0)
        self.members[id] = members
        self.items[id] = item
        return item

    def create_node(
        self,
        x: float,
        y: float,
        weight: int,
        id: str,
        weights: dict[str, int],
        func: Callable,
        members: set[str] = {},
    ):
        assert id not in self.items
        item = Node(x, y, weight, id, weights, func)
        item.index = self.get_next_node_index()
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
        self.graph.add_node(id, weight=weight)
        self.weights[id] = weights
        self.members[id] = members
        self.items[id] = item
        return item

    def get_next_node_index(self):
        self._node_index_count += 1
        return self._node_index_count

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

    def create_rect_box(self, vertices: list[Vertex], visible: bool = True):
        item = RectBox(vertices)
        for vertex in vertices:
            vertex.boxes.append(item)
        self.scene.addItem(item)
        item.adjust_position()
        item.setVisible(visible)
        return item

    def create_bezier(self, node1: Vertex, node2: Vertex, visible: bool = True):
        item = BezierCurve(node1, node2)
        item.setVisible(visible)
        self.binder.bind(
            self.settings.properties.highlight_color, item.set_highlight_color
        )
        self.binder.bind(self.settings.properties.pen_width_edges, item.set_pen_width)
        node1.beziers[node2] = item
        node2.beziers[node1] = item
        self.scene.addItem(item)
        id = tuple(sorted([node1.name, node2.name]))
        self.beziers[id] = item
        return item

    def add_child_edge(self, parent: Vertex, child: Vertex, segments=1):
        edge = self.create_edge(parent, child, segments)
        parent.addChild(child, edge)
        self.scene.addItem(edge)
        self.scene.addItem(child)
        self.graph.add_edge(parent.name, child.name, mutations=segments)
        return edge

    def add_sibling_edge(self, vertex: Vertex, sibling: Vertex, segments=1):
        edge = self.create_edge(vertex, sibling, segments)
        vertex.addSibling(sibling, edge)
        self.scene.addItem(edge)
        if not sibling.scene():
            self.scene.addItem(sibling)
        self.graph.add_edge(vertex.name, sibling.name, mutations=segments)
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

            item = self.items.get(name, None)

            if item is None:
                return

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

    def _dump_bezier(self, item: BezierCurve) -> dict:
        return {
            "node_a": item.node1.name,
            "node_b": item.node2.name,
            "c_a_x": item.c1.x(),
            "c_a_y": item.c1.y(),
            "c_b_x": item.c2.x(),
            "c_b_y": item.c2.y(),
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

    def _dump_graph(self) -> dict:
        return {
            "nodes": [[id, data["weight"]] for id, data in self.graph.nodes(data=True)],
            "edges": [
                [u, v, data["mutations"]] for u, v, data in self.graph.edges(data=True)
            ],
        }

    def _dump_tree(self) -> dict:
        nodes = [item for item in self.items.values() if isinstance(item, Vertex)]
        return {
            node.name: [child.name for child in node.children]
            for node in nodes
            if node.children
        }

    def _dump_root(self) -> str | None:
        if self.scene.root is not None:
            return self.scene.root.name
        return None

    def _dump_members(self) -> dict:
        return {k: list(sorted(v)) for k, v in self.members.items()}

    def _dump_partitions(self) -> dict:
        return {
            partition.key: partition.map for partition in self.settings.partitions.all()
        }

    def dump_dict(self) -> dict:
        nodes = []
        edges = []
        beziers = []
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
            elif isinstance(item, BezierCurve):
                bezier = self._dump_bezier(item)
                beziers.append(bezier)
            elif isinstance(item, BoundaryRect):
                boundary = self._dump_boundary(item)
            elif isinstance(item, Legend):
                legend = self._dump_legend(item)
            elif isinstance(item, Scale):
                scale = self._dump_scale(item)
        return {
            "version": __version__,
            "settings": self.settings.dump(),
            "graph": self._dump_graph(),
            "tree": self._dump_tree(),
            "root": self._dump_root(),
            "weights": dict(self.weights),
            "members": self._dump_members(),
            "partitions": self._dump_partitions(),
            "layout": {
                "nodes": nodes,
                "edges": edges,
                "beziers": beziers,
                "boundary": boundary,
                "legend": legend,
                "scale": scale,
            },
        }

    def _load_graph(self, data: dict[str, dict]):
        self.graph = nx.Graph()
        for id, weight in data["nodes"]:
            self.graph.add_node(id, weight=weight)
        for u, v, mutations in data["edges"]:
            self.graph.add_edge(u, v, mutations=mutations)

    def _load_root(self, root: str | None):
        if root is None:
            return
        self.scene.root = self.items[root]

    def _load_tree(self, data: dict[str, list[str]]):
        for parent, children in data.items():
            parent_item = self.items[parent]
            for child in children:
                child_item = self.items[child]
                parent_item.setSiblingToChild(child_item)

    def _load_weights(self, data: dict[str, dict[str, int]]):
        self.weights = defaultdict(dict, data)

    def _load_members(self, data: dict[str, list[str]]):
        self.members = defaultdict(set, {k: set(v) for k, v in data.items()})
        self.settings.members.set_dict(data)

    def _load_partitions(self, data: dict[str, dict[str, str]]):
        self.set_partitions(((k, v)) for k, v in data.items())

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

    def _load_bezier_layout(self, data: dict):
        id_a = data["node_a"]
        id_b = data["node_b"]
        c_a_x = data["c_a_x"]
        c_a_y = data["c_a_y"]
        c_b_x = data["c_b_x"]
        c_b_y = data["c_b_y"]
        bezier_id = tuple(sorted([id_a, id_b]))
        if id_a not in self.items:
            return
        if id_b not in self.items:
            return
        if bezier_id not in self.beziers:
            return
        bezier = self.beziers[bezier_id]
        node_a = self.items[id_a]
        node_b = self.items[id_b]
        control_a = QtCore.QPointF(c_a_x, c_a_y)
        control_b = QtCore.QPointF(c_b_x, c_b_y)
        bezier.set_control_point_for_node(node_a, control_a)
        bezier.set_control_point_for_node(node_b, control_b)
        bezier.adjust_position()

    def _load_boundary(self, data: dict):
        self.scene.set_boundary_rect(data["x"], data["y"], data["w"], data["h"])

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

    def load_dict(self, data: dict) -> tuple[bool, bool]:
        self.clear()
        self._load_members(data["members"])
        self._load_partitions(data["partitions"])
        self.settings.load(data["settings"])
        self._load_graph(data["graph"])
        self._load_weights(data["weights"])
        self.visualize_network()
        self.visualize_haploweb()
        self._load_root(data["root"])
        self._load_tree(data["tree"])
        self._load_boundary(data["layout"]["boundary"])
        self._load_legend(data["layout"]["legend"])
        self._load_scale(data["layout"]["scale"])
        self.update_members_setting()
        for node in data["layout"]["nodes"]:
            self._load_node_layout(node)
        for edge in data["layout"]["edges"]:
            self._load_edge_layout(edge)
        for bezier in data["layout"]["beziers"]:
            self._load_bezier_layout(bezier)
        if self.partition:
            self.colorize_nodes()
        has_tree = bool(data["tree"])
        has_web = bool(data["layout"]["beziers"])
        return has_tree, has_web

    def dump_yaml(self, path: str):
        with open(path, "w") as file:
            yaml.dump(self.dump_dict(), file)

    def load_yaml(self, path: Path | str) -> tuple[bool, bool]:
        with open(path, "r") as file:
            return self.load_dict(yaml.safe_load(file))
