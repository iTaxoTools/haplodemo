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

from PySide6 import QtGui

from collections import Counter

from .items.types import EdgeStyle
from .scene import GraphicsScene
from .settings import Settings
from .types import HaploGraph, HaploGraphEdge, HaploGraphNode, HaploTreeNode
from .visualizer import Visualizer


class DemoLoader:
    def __init__(
        self, scene: GraphicsScene, settings: Settings, visualizer: Visualizer
    ):
        self.scene = scene
        self.settings = settings
        self.visualizer = visualizer

    @staticmethod
    def get_font(family: str, size: int):
        font = QtGui.QFont(family)
        font.setPixelSize(size)
        return font

    def load_demo_simple(self):
        self.settings.reset()
        self.settings.node_sizes.set_all_values(5, 0, 1.0, 0)
        self.settings.show_legend = True
        self.settings.show_scale = True
        self.settings.scale.marks = [5, 40]
        self.settings.font = self.get_font("Arial", 16)

        self.visualizer.clear()
        self.visualizer.set_divisions(["X", "Y", "Z"])
        self.add_demo_nodes_simple()
        self.scene.set_boundary_to_contents()

    def add_demo_nodes_simple(self):
        visualizer = self.visualizer
        scene = self.scene

        radius_for_weight = self.settings.node_sizes.radius_for_weight

        node1 = visualizer.create_node(
            85, 70, 35, "Alphanumerical", {"X": 4, "Y": 3, "Z": 2}, radius_for_weight
        )
        scene.addItem(node1)

        node2 = visualizer.create_node(
            node1.pos().x() + 95,
            node1.pos().y() - 30,
            20,
            "Beta",
            {"X": 4, "Z": 2},
            radius_for_weight,
        )
        visualizer.add_child_edge(node1, node2, 2)

        node3 = visualizer.create_node(
            node1.pos().x() + 115,
            node1.pos().y() + 60,
            25,
            "C",
            {"Y": 6, "Z": 2},
            radius_for_weight,
        )
        edge = visualizer.add_child_edge(node1, node3, 3)
        edge.set_style(EdgeStyle.Bars)

        node4 = visualizer.create_node(
            node3.pos().x() + 60,
            node3.pos().y() - 30,
            15,
            "D",
            {"Y": 1},
            radius_for_weight,
        )
        visualizer.add_child_edge(node3, node4, 1)

        vertex1 = visualizer.create_vertex(node3.pos().x() - 60, node3.pos().y() + 60)
        visualizer.add_child_edge(node3, vertex1, 2)

        node5 = visualizer.create_node(
            vertex1.pos().x() - 80,
            vertex1.pos().y() + 40,
            30,
            "Error",
            {"?": 1},
            radius_for_weight,
        )
        edge = visualizer.add_child_edge(vertex1, node5, 4)
        edge.set_style(EdgeStyle.DotsWithText)

        node6 = visualizer.create_node(
            vertex1.pos().x() + 60,
            vertex1.pos().y() + 20,
            20,
            "R",
            {"Z": 1},
            radius_for_weight,
        )
        visualizer.add_child_edge(vertex1, node6, 1)

        node7 = visualizer.create_node(
            vertex1.pos().x() + 100,
            vertex1.pos().y() + 80,
            10,
            "S",
            {"Z": 1},
            radius_for_weight,
        )
        visualizer.add_sibling_edge(node6, node7, 2)

        node8 = visualizer.create_node(
            vertex1.pos().x() + 20,
            vertex1.pos().y() + 80,
            40,
            "T",
            {"Y": 1},
            radius_for_weight,
        )
        visualizer.add_sibling_edge(node6, node8, 1)
        visualizer.add_sibling_edge(node7, node8, 1)

        node9 = visualizer.create_node(
            node7.pos().x() + 20,
            node7.pos().y() - 40,
            5,
            "x",
            {"Z": 1},
            radius_for_weight,
        )
        visualizer.add_child_edge(node7, node9, 1)

    def load_demo_many(self):
        self.settings.reset()
        self.settings.node_sizes.set_all_values(30, 0, 0, 0)

        self.visualizer.clear()
        self.visualizer.set_divisions(["X", "Y"])
        self.add_demo_nodes_many(8, 32)
        self.scene.set_boundary_to_contents()

    def add_demo_nodes_many(self, dx, dy):
        visualizer = self.visualizer
        scene = self.scene

        radius_for_weight = self.settings.node_sizes.radius_for_weight

        for x in range(dx):
            nodex = visualizer.create_node(
                20, 80 * x, 15, f"x{x}", {"X": 1}, radius_for_weight
            )
            scene.addItem(nodex)

            for y in range(dy):
                nodey = visualizer.create_node(
                    nodex.pos().x() + 80 + 80 * y,
                    nodex.pos().y() + 40,
                    15,
                    f"y{y}",
                    {"Y": 1},
                    radius_for_weight,
                )
                visualizer.add_child_edge(nodex, nodey)

    def load_demo_tiny_tree(self):
        self.settings.reset()
        self.settings.node_sizes.set_all_values(20, 1.0, 0, 0)
        self.settings.show_legend = True
        self.settings.show_scale = True
        self.settings.edge_length = 40
        self.settings.node_label_template = "WEIGHT"
        self.settings.font = self.get_font("Arial", 24)

        tree = self.get_tiny_tree()
        self.visualizer.visualize_tree(tree)

    def get_tiny_tree(self) -> HaploTreeNode:
        root = HaploTreeNode("root")
        root.add_pops(["A"] * 3 + ["B"] * 5)

        a = HaploTreeNode("a")
        a.add_pops(["A"] * 1)
        root.add_child(a, 1)

        b = HaploTreeNode("b")
        b.add_pops(["B"] * 3)
        root.add_child(b, 4)

        c = HaploTreeNode("c")
        c.add_pops(["B"] * 1)
        b.add_child(c, 1)

        d = HaploTreeNode("d")
        d.add_pops(["C"] * 1)
        b.add_child(d, 2)

        return root

    def load_demo_members_tree(self):
        self.settings.reset()
        self.settings.node_sizes.set_all_values(40, 0.5, 0, 0)
        self.settings.show_legend = True
        self.settings.show_scale = True
        self.settings.edge_length = 40
        self.settings.node_label_template = "NAME/WEIGHT"
        self.settings.font = self.get_font("Arial", 24)

        tree = self.get_members_tree()
        self.visualizer.visualize_tree(tree)

        partitions = self.get_members_partitions()

        self.visualizer.set_partitions(partitions.items())
        self.visualizer.visualize_haploweb()

    def get_members_tree(self) -> HaploTreeNode:
        a = HaploTreeNode("a")
        a.add_members(["x", "y", "z", "r", "s", "t"])

        b = HaploTreeNode("b")
        b.add_members(["x", "y", "s"])
        a.add_child(b, 1)

        x = HaploTreeNode("x")
        a.add_child(x, 2)

        c = HaploTreeNode("c")
        c.add_members(["k", "l", "m"])
        x.add_child(c, 2)

        d = HaploTreeNode("d")
        d.add_members(["m", "n"])
        c.add_child(d, 1)

        e = HaploTreeNode("e")
        e.add_members(["n"])
        c.add_child(e, 2)

        f = HaploTreeNode("f")
        f.add_members(["o"])
        a.add_child(f, 3)

        return a

    def get_members_partitions(self) -> dict[str, dict[str, str]]:
        return {
            "Few": {
                "x": "A",
                "y": "A",
                "z": "A",
                "r": "A",
                "s": "A",
                "t": "A",
                "k": "E",
                "l": "E",
                "m": "E",
                "n": "E",
                "o": "A",
            },
            "Many": {
                "x": "A",
                "y": "A",
                "z": "A",
                "r": "B",
                "s": "B",
                "t": "C",
                "k": "D",
                "l": "D",
                "m": "E",
                "n": "E",
                "o": "C",
            },
        }

    def load_demo_long_tree(self):
        self.settings.reset()
        self.settings.node_sizes.set_all_values(30, 0, 0.1, 0)
        self.settings.show_legend = True
        self.settings.show_scale = True
        self.settings.edge_length = 40
        self.settings.pen_width_nodes = 2
        self.settings.pen_width_edges = 4
        self.settings.node_label_template = "WEIGHT"
        self.settings.font = self.get_font("Arial", 24)

        tree = self.get_long_tree()
        self.visualizer.visualize_tree(tree)

    def get_long_tree(self) -> HaploTreeNode:
        root = HaploTreeNode("root")
        root.add_pops(
            {
                "Asia": 9,
                "Africa": 3,
                "Europe": 3,
                "North America": 2,
                "South America": 1,
                "Australia": 1,
            }
        )

        asia_1 = HaploTreeNode("asia_1")
        root.add_child(asia_1, 1)
        asia_1.add_pops(
            {
                "Asia": 35,
                "Europe": 2,
            }
        )

        asia_11 = HaploTreeNode("asia_11")
        asia_1.add_child(asia_11, 1)
        asia_11.add_pops(
            {
                "Asia": 6,
            }
        )

        asia_111 = HaploTreeNode("asia_111")
        asia_11.add_child(asia_111, 1)
        asia_111.add_pops(
            {
                "Asia": 2,
            }
        )

        asia_1111 = HaploTreeNode("asia_1111")
        asia_111.add_child(asia_1111, 2)
        asia_1111.add_pops(
            {
                "Asia": 6,
                "Africa": 2,
            }
        )

        asia_11111 = HaploTreeNode("asia_11111")
        asia_1111.add_child(asia_11111, 5)
        asia_11111.add_pops(
            {
                "Asia": 1,
            }
        )

        asia_11112 = HaploTreeNode("asia_11112")
        asia_1111.add_child(asia_11112, 1)
        asia_11112.add_pops(
            {
                "Africa": 1,
            }
        )
        asia_12 = HaploTreeNode("asia_12")
        asia_1.add_child(asia_12, 1)
        asia_12.add_pops(
            {
                "Asia": 1,
                "Europe": 1,
            }
        )

        asia_13 = HaploTreeNode("asia_13")
        asia_1.add_child(asia_13, 1)
        asia_13.add_pops(
            {
                "Asia": 1,
            }
        )

        asia_2 = HaploTreeNode("asia_2")
        root.add_child(asia_2, 1)
        asia_2.add_pops(
            {
                "Asia": 14,
                "Africa": 1,
                "Europe": 2,
            }
        )

        europe_1 = HaploTreeNode("europe_1")
        root.add_child(europe_1, 1)
        europe_1.add_pops(
            {
                "Asia": 3,
                "Africa": 1,
                "Europe": 26,
                "North America": 3,
                "South America": 1,
            }
        )

        europe_11 = HaploTreeNode("europe_11")
        europe_1.add_child(europe_11, 1)
        europe_11.add_pops(
            {
                "Asia": 1,
                "Europe": 1,
            }
        )

        europe_111 = HaploTreeNode("europe_111")
        europe_11.add_child(europe_111, 7)
        europe_111.add_pops(
            {
                "Europe": 6,
            }
        )

        europe_1111 = HaploTreeNode("europe_1111")
        europe_111.add_child(europe_1111, 1)
        europe_1111.add_pops(
            {
                "Europe": 1,
                "North America": 1,
            }
        )

        europe_1112 = HaploTreeNode("europe_1112")
        europe_111.add_child(europe_1112, 3)
        europe_1112.add_pops(
            {
                "North America": 7,
            }
        )

        europe_2 = HaploTreeNode("europe_2")
        root.add_child(europe_2, 3)
        europe_2.add_pops(
            {
                "Africa": 1,
                "Europe": 57,
                "North America": 31,
                "South America": 9,
                "Australia": 2,
            }
        )

        america_1 = HaploTreeNode("america_1")
        europe_2.add_child(america_1, 1)
        america_1.add_pops(
            {
                "Africa": 3,
                "Europe": 4,
                "North America": 24,
                "South America": 91,
            }
        )

        america_2 = HaploTreeNode("america_2")
        europe_2.add_child(america_2, 2)
        america_2.add_pops(
            {
                "Africa": 3,
                "Europe": 4,
                "North America": 13,
                "South America": 56,
                "Australia": 4,
            }
        )

        australia_1 = HaploTreeNode("australia_1")
        root.add_child(australia_1, 22)
        australia_1.add_pops(
            {
                "Australia": 4,
            }
        )

        return root

    def load_demo_heavy_tree(self):
        self.settings.reset()
        self.settings.node_sizes.set_all_values(20, 0, 0, 2.0)
        self.settings.show_legend = True
        self.settings.show_scale = True
        self.settings.edge_length = 40
        self.settings.node_label_template = "WEIGHT"

        tree = self.get_heavy_tree()
        self.visualizer.visualize_tree(tree)

    def get_heavy_tree(self) -> HaploTreeNode:
        a = HaploTreeNode("a")
        a.add_pops(["A"] * 4002 + ["B"] * 3046)

        for i in range(17):
            ac = HaploTreeNode(f"a{i}")
            ac.add_pops(["A"])
            a.add_child(ac, 1)

        b = HaploTreeNode("b")
        a.add_child(b, 1)
        b.add_pops(["A"] * 13 + ["B"] * 257)

        for i in range(11):
            bc = HaploTreeNode(f"b{i}")
            bc.add_pops(["B"])
            b.add_child(bc, 1)

        c = HaploTreeNode("c")
        a.add_child(c, 5)
        c.add_pops(["A"] * 52)

        return a

    def load_demo_cycled_graph(self):
        self.settings.reset()
        self.settings.node_sizes.set_all_values(10, 0, 0, 1.5)
        self.settings.show_legend = True
        self.settings.show_scale = True
        self.settings.edge_length = 20
        self.settings.node_label_template = "WEIGHT"

        graph = self.get_cycled_graph()
        self.visualizer.visualize_graph(graph)

    def get_cycled_graph(self) -> HaploGraph:
        return HaploGraph(
            [
                HaploGraphNode(
                    id="a1",
                    pops=Counter("A" * 10),
                    members=[f"a1_{x}" for x in range(10)],
                ),
                HaploGraphNode(
                    id="b1",
                    pops=Counter("B"),
                    members=["b1_0"],
                ),
                HaploGraphNode(
                    id="b2",
                    pops=Counter("BB"),
                    members=[f"b2_{x}" for x in range(2)],
                ),
                HaploGraphNode(
                    id="ab",
                    pops=Counter("AAB"),
                    members=[f"ab_{x}" for x in range(3)],
                ),
            ],
            [
                HaploGraphEdge(0, 1, 1),
                HaploGraphEdge(0, 2, 1),
                HaploGraphEdge(1, 2, 1),
                HaploGraphEdge(0, 3, 2),
            ],
        )

    def load_demo_fields(self):
        self.settings.reset()
        self.settings.node_sizes.set_all_values(20, 0.5, 0, 0)
        self.settings.scale.marks = [1, 10]
        self.settings.font = self.get_font("Arial", 16)
        self.settings.node_label_template = "WEIGHT"

        self.visualizer.clear()
        self.visualizer.set_divisions(["X", "Y", "Z"])
        self.add_demo_nodes_fields()
        self.scene.set_boundary_to_contents()
        self.scene.style_labels()

    def add_demo_nodes_fields(self):
        visualizer = self.visualizer
        scene = self.scene

        radius_for_weight = self.settings.node_sizes.radius_for_weight

        node1 = visualizer.create_node(
            0, 150, 7, "Node1", {"X": 4, "Y": 3}, radius_for_weight
        )
        scene.addItem(node1)

        node2 = visualizer.create_node(200, 0, 4, "Node2", {"X": 4}, radius_for_weight)
        visualizer.add_child_edge(node1, node2, 2)

        node3 = visualizer.create_node(0, 0, 2, "Node3", {"X": 2}, radius_for_weight)
        visualizer.add_child_edge(node2, node3, 1)

        node4 = visualizer.create_node(400, 0, 3, "Node4", {"X": 3}, radius_for_weight)
        visualizer.add_child_edge(node2, node4, 1)

        node5 = visualizer.create_node(0, 400, 6, "Node5", {"Z": 4}, radius_for_weight)
        visualizer.add_child_edge(node1, node5, 3)

        node6 = visualizer.create_node(
            200, 250, 1, "Node6", {"Y": 1}, radius_for_weight
        )
        visualizer.add_child_edge(node1, node6, 1)

        node7 = visualizer.create_node(
            400, 250, 3, "Node7", {"Y": 1}, radius_for_weight
        )
        visualizer.add_child_edge(node6, node7, 3)

        node8 = visualizer.create_node(
            200, 400, 1, "Node8", {"Y": 1}, radius_for_weight
        )
        visualizer.add_child_edge(node6, node8, 1)

        node9 = visualizer.create_node(
            400, 400, 1, "Node9", {"Y": 1}, radius_for_weight
        )
        visualizer.add_child_edge(node7, node9, 1)

        convex = visualizer.create_rect_box([node1, node3])

        convex = visualizer.create_rect_box([node2, node4])

        convex = visualizer.create_rect_box([node5])
        convex.setColor("#ff3")

        convex = visualizer.create_rect_box([node6, node7, node8, node9])

        bezier = visualizer.create_bezier(node1, node3)
        bezier.bump(1.0)

        bezier = visualizer.create_bezier(node2, node4)
        bezier.bump(-0.5)

        bezier = visualizer.create_bezier(node6, node8)
        bezier.bump(0.5)
        bezier = visualizer.create_bezier(node7, node8)
        bezier.bump(0.5)
        bezier = visualizer.create_bezier(node7, node9)
        bezier.bump(0.5)
