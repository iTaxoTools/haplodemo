from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from enum import Enum, auto
from sys import stdout


@dataclass
class Partition:
    key: str
    map: dict[str, str]


@dataclass
class Division:
    key: str
    color: str


class LayoutType(Enum):
    ModifiedSpring = auto()
    Spring = auto()


class HaploTreeNode:
    """Copied from the Fitchi repository.

    Simplified datatype for the Haplotype genealogy graph produced by Fitchi.
    The tree hierarchy is contained in `self.parent` and `self.children`.
    The distance between a node and its parent is `self.mutations`.
    """

    def __init__(self, id):
        self.id = id
        self.children = list[HaploTreeNode]()
        self.parent = None
        self.mutations = 0
        self.pops = Counter()
        self.members = list[str]()

    def add_child(self, node: HaploTreeNode, mutations: int = 0):
        self.children.append(node)
        node.mutations = mutations
        node.parent = self

    def add_pops(self, pops: list[str] | dict[str, int]):
        self.pops.update(pops)

    def add_members(self, members: iter[str]):
        self.members.extend([member for member in members])

    def get_size(self):
        if self.pops:
            return self.pops.total()
        if self.members:
            return len(self.members)

    def __str__(self):
        total = self.pops.total()
        per_pop_strings = (f'{v} \u00D7 {k}' for k, v in self.pops.items())
        all_pops_string = ' + '.join(per_pop_strings)
        return f"<{self.id}: {total} = {all_pops_string}>"

    def print(self, level=0, length=5, file=stdout):
        mutations_string = str(self.mutations).center(length, '\u2500')
        decoration = ' ' * (length + 1) * (level - 1) + f"\u2514{mutations_string}" if level else ''
        print(f"{decoration}{str(self)}", file=file)
        for child in self.children:
            child.print(level + 1, length, file)


@dataclass
class HaploGraphNode:
    id: str
    pops: Counter[str] = field(default_factory=Counter)
    members: list[str] = field(default_factory=list)

    def get_size(self):
        if self.pops:
            return self.pops.total()
        if self.members:
            return len(self.members)


@dataclass
class HaploGraphEdge:
    node_a: int
    node_b: int
    mutations: int


@dataclass
class HaploGraph:
    nodes: list[HaploGraphNode]
    edges: list[HaploGraphEdge]
