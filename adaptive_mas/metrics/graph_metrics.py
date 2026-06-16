import networkx as nx
from ..dag.dag import DAG
import numpy as np

DEFAULT_NODE_COST = 0.1


class GraphMetrics:
    """Calculates various metrics for the DAG."""

    DEFAULT_NODE_COST = DEFAULT_NODE_COST

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

    @staticmethod
    def node_cost(dag: DAG, node_id: str, default_cost: float = DEFAULT_NODE_COST) -> float:
        """Return the execution cost for one node.

        Synthetic benchmark graphs store execution cost in ``node.data["cost"]``.
        If a node has no explicit cost, the default mirrors the mock-agent sleep
        duration used by the executors.
        """
        node = dag.get_node(node_id)
        if node is None:
            return default_cost
        value = node.data.get("cost")
        return float(value) if value is not None else default_cost

    @staticmethod
    def node_costs(dag: DAG, default_cost: float = DEFAULT_NODE_COST) -> dict:
        """Return a mapping of node id to execution cost."""
        return {
            node_id: GraphMetrics.node_cost(dag, node_id, default_cost)
            for node_id in dag.nodes
        }

    @staticmethod
    def total_node_cost(dag: DAG, default_cost: float = DEFAULT_NODE_COST) -> float:
        """Return the sum of all node execution costs."""
        return sum(GraphMetrics.node_costs(dag, default_cost).values())

    @staticmethod
    def average_node_cost(dag: DAG, default_cost: float = DEFAULT_NODE_COST) -> float:
        """Return the average node execution cost, or 0.0 for an empty DAG."""
        if not dag.nodes:
            return 0.0
        return GraphMetrics.total_node_cost(dag, default_cost) / len(dag.nodes)

    @staticmethod
    def max_node_cost(dag: DAG, default_cost: float = DEFAULT_NODE_COST) -> float:
        """Return the largest node execution cost, or 0.0 for an empty DAG."""
        costs = GraphMetrics.node_costs(dag, default_cost).values()
        return max(costs, default=0.0)

    @staticmethod
    def cost_variance(dag: DAG, default_cost: float = DEFAULT_NODE_COST) -> float:
        """Return population variance of node execution costs.

        A single-node or empty graph has no spread, so this returns 0.0.
        """
        costs = list(GraphMetrics.node_costs(dag, default_cost).values())
        if len(costs) <= 1:
            return 0.0
        mean = sum(costs) / len(costs)
        return sum((cost - mean) ** 2 for cost in costs) / len(costs)

    @staticmethod
    def weighted_critical_path_length(dag: DAG, default_cost: float = DEFAULT_NODE_COST) -> float:
        """Return the maximum summed node cost over any DAG path.

        The implementation uses dynamic programming over topological order and
        is valid for any acyclic graph. Empty graphs return 0.0.
        """
        if not dag.graph.nodes:
            return 0.0
        longest = {}
        for node in dag.topological_sort():
            predecessors = dag.get_predecessors(node)
            node_cost = GraphMetrics.node_cost(dag, node, default_cost)
            if predecessors:
                longest[node] = max(longest[pred] for pred in predecessors) + node_cost
            else:
                longest[node] = node_cost
        return max(longest.values(), default=0.0)

    @staticmethod
    def weighted_parallel_width(dag: DAG, default_cost: float = DEFAULT_NODE_COST) -> float:
        """Return the maximum total node cost present in any topological level."""
        levels = GraphMetrics.node_levels(dag)
        if not levels:
            return 0.0
        level_costs = {}
        for node, level in levels.items():
            level_costs[level] = level_costs.get(level, 0.0) + GraphMetrics.node_cost(
                dag, node, default_cost
            )
        return max(level_costs.values(), default=0.0)
# Minor edit: updated file timestamp for Git tracking
