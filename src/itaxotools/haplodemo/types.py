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
        self.members = set[str]()

    def add_child(self, node: HaploTreeNode, mutations: int = 0):
        self.children.append(node)
        node.mutations = mutations
        node.parent = self

    def add_pops(self, pops: list[str] | dict[str, int]):
        self.pops.update(pops)

    def add_members(self, members: iter[str]):
        self.members.update([member for member in members])

    def get_size(self):
        if self.pops:
            return self.pops.total()
        if self.members:
            return len(self.members)
        return 0

    def __str__(self):
        total = self.pops.total()
        per_pop_strings = (f"{v} \u00D7 {k}" for k, v in self.pops.items())
        all_pops_string = " + ".join(per_pop_strings)
        members_string = ", ".join(self.members)
        return f"<{self.id}: {total} = {all_pops_string}; {members_string}>"

    def print(self, level=0, length=5, file=stdout):
        mutations_string = str(self.mutations).center(length, "\u2500")
        decoration = (
            " " * (length + 1) * (level - 1) + f"\u2514{mutations_string}"
            if level
            else ""
        )
        print(f"{decoration}{str(self)}", file=file)
        for child in self.children:
            child.print(level + 1, length, file)


@dataclass
class HaploGraphNode:
    id: str
    pops: Counter[str] = field(default_factory=Counter)
    members: set[str] = field(default_factory=set)

    def get_size(self):
        if self.pops:
            return self.pops.total()
        if self.members:
            return len(self.members)
        return 0


@dataclass
class HaploGraphEdge:
    node_a: int
    node_b: int
    mutations: int


@dataclass
class HaploGraph:
    nodes: list[HaploGraphNode]
    edges: list[HaploGraphEdge]


class MemberItem:
    def __init__(self, name, parent=None):
        self.name = name
        self.parent = parent
        self.children = []
        self.index = 0

        if parent is not None:
            parent.add_child(self)

    def add_child(self, item: MemberItem):
        item.index = len(self.children)
        self.children.append(item)

    def __repr__(self):
        parent_str = self.parent.name if self.parent else None
        children_str = ", ".join(repr(child.name) for child in self.children)
        children_str = children_str or "None"
        return f"{type(self).__name__} <name='{self.name}', parent='{parent_str}', index={self.index}, children={children_str}>"
