import networkx as nx
from ..dag.dag import DAG


class GraphMetrics:
    """Calculates various metrics for the DAG."""

    @staticmethod
    def graph_depth(dag: DAG) -> int:
        """Calculate the depth of the graph (longest path length)."""
        if not dag.graph.nodes:
            return 0
        return nx.dag_longest_path_length(dag.graph) + 1

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
        levels = GraphMetrics.node_levels(dag)
        if not levels:
            return 0
        level_counts = {}
        for level in levels.values():
            level_counts[level] = level_counts.get(level, 0) + 1
        return max(level_counts.values())

    @staticmethod
    def node_levels(dag: DAG) -> dict:
        """Return a 1-based topological level for each node."""
        if not dag.graph.nodes:
            return {}
        levels = {}
        for node in nx.topological_sort(dag.graph):
            pred_levels = [levels[pred] for pred in dag.graph.predecessors(node)]
            levels[node] = max(pred_levels) + 1 if pred_levels else 1
        return levels

    @staticmethod
    def max_degree(dag: DAG) -> int:
        """Return maximum total degree across nodes."""
        if not dag.graph.nodes:
            return 0
        return max(dag.graph.in_degree(node) + dag.graph.out_degree(node) for node in dag.graph.nodes)
