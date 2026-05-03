import networkx as nx
from typing import Dict, Any
from ..dag.dag import DAG


class GraphMetrics:
    """Calculates various metrics for the DAG."""

    @staticmethod
    def graph_depth(dag: DAG) -> int:
        """Calculate the depth of the graph (longest path length)."""
        if not dag.graph.nodes:
            return 0
        return nx.dag_longest_path_length(dag.graph)

    @staticmethod
    def critical_path_length(dag: DAG) -> int:
        """Calculate the critical path length (same as depth for DAG)."""
        return GraphMetrics.graph_depth(dag)

    @staticmethod
    def graph_density(dag: DAG) -> float:
        """Calculate the density of the graph."""
        n = len(dag.graph.nodes)
        if n <= 1:
            return 0.0
        m = len(dag.graph.edges)
        return 2 * m / (n * (n - 1))

    @staticmethod
    def parallel_width(dag: DAG) -> int:
        """Calculate the parallel width (maximum number of nodes at any level)."""
        if not dag.graph.nodes:
            return 0
        levels = {}
        for node in nx.topological_sort(dag.graph):
            pred_levels = [levels[pred] for pred in dag.graph.predecessors(node)]
            levels[node] = max(pred_levels) + 1 if pred_levels else 1
        return max(levels.values()) if levels else 0