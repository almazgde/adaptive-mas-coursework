import networkx as nx
from typing import List, Dict, Any
from .node import Node
from .edge import Edge


class DAG:
    """Directed Acyclic Graph abstraction for task dependencies."""

    def __init__(self):
        self.graph = nx.DiGraph()
        self.nodes: Dict[str, Node] = {}
        self.edges: List[Edge] = []

    def add_node(self, node: Node):
        """Add a node to the DAG."""
        self.nodes[node.node_id] = node
        self.graph.add_node(node.node_id, **node.data)

    def add_edge(self, edge: Edge):
        """Add an edge to the DAG."""
        self.edges.append(edge)
        self.graph.add_edge(edge.from_node, edge.to_node, **edge.data)

    def get_node(self, node_id: str) -> Node:
        """Get a node by ID."""
        return self.nodes.get(node_id)

    def get_successors(self, node_id: str) -> List[str]:
        """Get successor nodes."""
        return list(self.graph.successors(node_id))

    def get_predecessors(self, node_id: str) -> List[str]:
        """Get predecessor nodes."""
        return list(self.graph.predecessors(node_id))

    def is_acyclic(self) -> bool:
        """Check if the graph is acyclic."""
        return nx.is_directed_acyclic_graph(self.graph)

    def topological_sort(self) -> List[str]:
        """Return nodes in topological order."""
        return list(nx.topological_sort(self.graph))