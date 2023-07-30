from random import randint

import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
from networkx.drawing.layout import _process_params, rescale_layout
from networkx.utils import np_random_state

np.set_printoptions(linewidth=np.inf)
np.set_printoptions(threshold=np.inf)


@np_random_state(11)
def modified_spring_layout(
    G,
    k=None,
    p=None,
    pos=None,
    fixed=None,
    iterations=5000,
    threshold=1e-4,
    weight="weight",
    scale=1,
    center=None,
    dim=2,
    seed=None,
):
    """Position nodes using a modified Fruchterman-Reingold algorithm.

    Based on `networkx.spring_layout`.

    The algorithm simulates a force-directed representation of the network
    treating edges as springs holding nodes close, while treating nodes
    as repelling objects, sometimes called an anti-gravity force.
    Simulation continues until the positions are close to an equilibrium.

    Modifications
    ----------
    - The springs have idle length equal to the weight of the edge
    - The repelling force gets weaker with every iteration

    Modified parameters
    ----------
    G : NetworkX graph or list of nodes
        A position will be assigned to every node in G.

    k : float (default=None)
        Strength of the spring force between adjacent nodes.

    k : float (default=None)
        Strength of the repelling force between all nodes.

    """

    G, center = _process_params(G, center, dim)

    if fixed is not None:
        raise ValueError('fixed nodes are not supported')

    if pos is not None:
        # Determine size of existing domain to adjust initial positions
        dom_size = max(coord for pos_tup in pos.values() for coord in pos_tup)
        if dom_size == 0:
            dom_size = 1
        pos_arr = seed.rand(len(G), dim) * dom_size + center

        for i, n in enumerate(G):
            if n in pos:
                pos_arr[i] = np.asarray(pos[n])
    else:
        pos_arr = None
        dom_size = 1

    if len(G) == 0:
        return {}
    if len(G) == 1:
        return {nx.utils.arbitrary_element(G.nodes()): center}

    A = nx.to_numpy_array(G, weight=weight)
    pos = _modified_fruchterman_reingold(
        A, k, p, pos_arr, fixed, iterations, threshold, dim, seed
    )

    if fixed is None and scale is not None:
        pos = rescale_layout(pos, scale=scale) + center
    pos = dict(zip(G, pos))
    return pos


@np_random_state(8)
def _modified_fruchterman_reingold(
    A, k=None, p=None, pos=None, fixed=None, iterations=5000, threshold=1e-4, dim=2, seed=None
):
    """Position nodes in adjacency matrix A using modified Fruchterman-Reingold"""

    k = k or 1
    p = p or 10

    # Stencil for adjacent nodes
    B = np.where(A == 0, 0, 1)

    try:
        nnodes, _ = A.shape
    except AttributeError as err:
        msg = "expected adjacency matrix as input"
        raise nx.NetworkXError(msg) from err

    if pos is None:
        # random initial positions
        pos = np.asarray(seed.rand(nnodes, dim), dtype=A.dtype)
    else:
        # make sure positions are of same type as matrix
        pos = pos.astype(A.dtype)

    # the initial "temperature"  is about .1 of domain area (=1x1)
    # this is the largest step allowed in the dynamics.
    # We need to calculate this in case our fixed positions force our domain
    # to be much bigger than 1x1
    t = max(max(pos.T[0]) - min(pos.T[0]), max(pos.T[1]) - min(pos.T[1])) * 0.1
    # simple cooling scheme.
    # linearly step down by dt on each iteration so last iteration is size dt.
    dt = t / (iterations + 1)
    # could use multilevel methods to speed this up significantly
    for iteration in range(iterations):
        # matrix of difference between points
        delta = pos[:, np.newaxis, :] - pos[np.newaxis, :, :]
        # distance between points
        distance = np.linalg.norm(delta, axis=-1)
        # enforce minimum distance of 0.01
        np.clip(distance, 0.01, None, out=distance)
        # repelling coefficient (drops off)
        derivative = (iterations - iteration) / iterations
        repelling = p * (derivative ** 4) / (distance ** 2)
        # springing coefficient (constant)
        springing = (A - B * distance) * k
        # displacement force
        force = repelling + springing
        displacement = np.einsum(
            "ijk,ij->ik", delta, force
        )
        # update positions
        length = np.linalg.norm(displacement, axis=-1)
        length = np.where(length < 0.01, 0.1, length)
        delta_pos = np.einsum("ij,i->ij", displacement, t / length)
        pos += delta_pos
        # cool temperature
        t -= dt
        if (np.linalg.norm(delta_pos) / nnodes) < threshold:
            break
    print(f'Distance [{iteration}]'.center(50, '*'))
    print(distance)
    return pos


def get_simple_graph():
    # Create a graph with weighted edges
    G = nx.Graph()
    G.add_edge(1, 2, weight=1)
    G.add_edge(2, 3, weight=1)
    G.add_edge(3, 4, weight=1)
    G.add_edge(4, 5, weight=2)
    # G.add_edge(5,1,weight=5)

    G.add_edge(5, 6, weight=3)
    G.add_edge(6, 7, weight=3)
    G.add_edge(7, 5, weight=3)
    G.add_edge(5, 8, weight=2)

    return G


def get_random_graph(
    depth = 2,
    min_children = 1,
    max_children = 4,
    min_weight = 2,
    max_weight = 6,
):
    # Create random weighted tree

    def populate_graph(G, parent, depth):
        if depth < 0:
            return

        children = randint(min_children, max_children)

        for i in range(children):
            weight = randint(min_weight, max_weight)
            child = f'{parent}/{i+1}'
            G.add_edge(parent, child, weight=weight)
            populate_graph(G, child, depth - 1)

    G = nx.Graph()
    populate_graph(G, '0', depth)
    return G


# G = get_simple_graph()
G = get_random_graph()

# Set the position of the nodes using the spring layout
pos = modified_spring_layout(G, weight='weight')
# pos = nx.spring_layout(G, weight='weight')
# pos = nx.circular_layout(G)
# pos = nx.kamada_kawai_layout(G)
# pos = nx.planar_layout(G)
# pos = nx.spectral_layout(G)
# pos = nx.shell_layout(G)

# Draw the graph with the node labels and edge labels
nx.draw_networkx_nodes(G, pos)
nx.draw_networkx_edges(G, pos)

nx.draw_networkx_labels(
    G, pos, font_size=12, font_family="sans-serif")

nx.draw_networkx_edge_labels(
    G, pos, font_size=8, font_family="sans-serif",
    edge_labels=nx.get_edge_attributes(G, 'weight'))

# Set the axis limits and turn off the axis labels
plt.axis('equal')

# Show the plot
plt.show()
