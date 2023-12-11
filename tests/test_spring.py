import networkx as nx
import numpy as np

from itaxotools.haplodemo.layout import modified_spring_layout


def get_simple_graph():
    G = nx.Graph()

    G.add_edge(1, 2, length=1.0)
    G.add_edge(2, 3, length=1.0)
    G.add_edge(3, 4, length=1.0)
    G.add_edge(4, 5, length=2.0)

    G.add_edge(5, 6, length=3.0)
    G.add_edge(6, 7, length=3.0)
    G.add_edge(7, 5, length=3.0)
    G.add_edge(5, 8, length=2.0)

    return G


def check_distance(pos, a, b, target, threshold=0.01):
    distance = np.linalg.norm(pos[a] - pos[b])
    return distance - target < threshold


def test_simple_spring():
    G = get_simple_graph()
    pos = modified_spring_layout(G, scale=None)

    assert len(pos) == 8

    assert check_distance(pos, 1, 2, 1.0)
    assert check_distance(pos, 2, 3, 1.0)
    assert check_distance(pos, 3, 4, 1.0)
    assert check_distance(pos, 4, 5, 2.0)

    assert check_distance(pos, 5, 6, 3.0)
    assert check_distance(pos, 6, 7, 3.0)
    assert check_distance(pos, 7, 5, 3.0)
    assert check_distance(pos, 5, 8, 2.0)
