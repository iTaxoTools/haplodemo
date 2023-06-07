import matplotlib.pyplot as plt
import networkx as nx

# Create a graph with weighted edges
G = nx.Graph()
G.add_edge(1,2,weight=3)
G.add_edge(2,3,weight=4)
G.add_edge(3,4,weight=1)
G.add_edge(4,5,weight=2)
G.add_edge(5,1,weight=5)

G.add_edge(5,11,weight=1)
G.add_edge(5,12,weight=2)
G.add_edge(12,21,weight=2)
G.add_edge(12,22,weight=2)
G.add_edge(12,23,weight=2)
G.add_edge(12,23,weight=0.20)
# Set the position of the nodes using the spring layout
pos = nx.spring_layout(G, weight='weight')

# Draw the graph with the node labels and edge labels
nx.draw_networkx_nodes(G, pos)
nx.draw_networkx_edges(G, pos)
nx.draw_networkx_labels(G, pos, font_size=12, font_family="sans-serif")
nx.draw_networkx_edge_labels(G, pos, edge_labels={}, font_size=10, font_family="sans-serif")

# Set the axis limits and turn off the axis labels
plt.xlim(-1.2,1.2)
plt.ylim(-1.2,1.2)
plt.axis('off')

# Show the plot
plt.show()
