from random import randint

import matplotlib.pyplot as plt
import networkx as nx
import numpy as np

from itaxotools.haplodemo.layout import modified_spring_layout

np.set_printoptions(linewidth=np.inf)
np.set_printoptions(threshold=np.inf)


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
