from enum import Enum
import math
from typing import List, Dict, Any, Tuple
import networkx as nx
from ..dag.dag import DAG
from ..metrics.graph_metrics import GraphMetrics


class TopologyType(Enum):
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    HIERARCHICAL = "hierarchical"
    HYBRID = "hybrid"


class AdaptiveTopologyMode(Enum):
    RULE_BASED = "rule_based_adaptive"
    COST_AWARE = "cost_aware_adaptive"
    LEARNED = "learned_adaptive"


class TopologySelector:
    """Selects and applies topology strategies to the DAG."""

    DEFAULT_NODE_COST = GraphMetrics.DEFAULT_NODE_COST

    @staticmethod
    def select_topology(dag: DAG, topology_type: TopologyType) -> Dict[str, Any]:
        if topology_type == TopologyType.SEQUENTIAL:
            return TopologySelector._sequential_topology(dag)
        elif topology_type == TopologyType.PARALLEL:
            return TopologySelector._parallel_topology(dag)
        elif topology_type == TopologyType.HIERARCHICAL:
            return TopologySelector._hierarchical_topology(dag)
        elif topology_type == TopologyType.HYBRID:
            return TopologySelector._hybrid_topology(dag)
        else:
            raise ValueError(f"Unknown topology type: {topology_type}")

    @staticmethod
    def select_adaptive_topology_type(dag: DAG) -> TopologyType:
        """Choose a topology from graph metrics for adaptive orchestration."""
        return TopologySelector.select_rule_based_adaptive_topology_type(dag)

    @staticmethod
    def select_rule_based_adaptive_topology_type(dag: DAG) -> TopologyType:
        """Choose a topology using structural DAG heuristics.

        This preserves the original adaptive selector behavior: depth, width,
        density and maximum degree determine the selected topology.
        """
        node_count = len(dag.graph.nodes)
        if node_count <= 1:
            return TopologyType.SEQUENTIAL

        depth = GraphMetrics.graph_depth(dag)
        width = GraphMetrics.parallel_width(dag)
        density = GraphMetrics.graph_density(dag)
        max_degree = GraphMetrics.max_degree(dag)
        depth_ratio = depth / node_count
        width_ratio = width / node_count

        if depth_ratio >= 0.65:
            return TopologyType.SEQUENTIAL
        if max_degree >= max(4, node_count // 3) and depth_ratio < 0.55:
            return TopologyType.HIERARCHICAL
        if width_ratio >= 0.45 and density <= 0.25:
            return TopologyType.PARALLEL
        return TopologyType.HYBRID

    @staticmethod
    def select_cost_aware_adaptive_topology_type(dag: DAG) -> TopologyType:
        """Choose the topology with the lowest estimated execution score."""
        estimates = TopologySelector.estimate_topology_costs(dag)
        return min(estimates, key=lambda topology: estimates[topology]["score"])

    @staticmethod
    def select_adaptive_topology(
        dag: DAG,
        mode: AdaptiveTopologyMode = AdaptiveTopologyMode.RULE_BASED,
    ) -> Dict[str, Any]:
        """Select and materialize a topology dynamically.

        The default mode is rule-based to keep the existing public behavior.
        Use ``AdaptiveTopologyMode.COST_AWARE`` to select from estimated latency
        and coordination costs.
        """
        if isinstance(mode, str):
            mode = AdaptiveTopologyMode(mode)
        if mode == AdaptiveTopologyMode.COST_AWARE:
            topology_type = TopologySelector.select_cost_aware_adaptive_topology_type(dag)
        else:
            topology_type = TopologySelector.select_rule_based_adaptive_topology_type(dag)
        topology = TopologySelector.select_topology(dag, topology_type)
        topology["adaptive"] = True
        topology["adaptive_mode"] = mode.value
        return topology

    @staticmethod
    def estimate_topology_costs(dag: DAG) -> Dict[TopologyType, Dict[str, float]]:
        """Estimate latency-related costs for every supported topology.

        The model is intentionally lightweight and readable. For each candidate
        topology it schedules DAG nodes with a small worker profile, then scores:

            score = expected_latency + coordination_overhead + critical_path_penalty

        ``expected_latency`` is the simulated makespan for node costs, where
        ``node.data["cost"]`` is used when available and ``DEFAULT_NODE_COST``
        mirrors the 0.1s mock-agent sleep otherwise. ``coordination_overhead``
        is a topology-specific tax for waves, edges and contention. The critical
        path penalty keeps the selector conservative when a graph is inherently
        sequential and parallel coordination cannot reduce the critical path.
        """
        node_costs = GraphMetrics.node_costs(dag)
        critical_path_latency = GraphMetrics.weighted_critical_path_length(dag)
        weighted_parallel_width = GraphMetrics.weighted_parallel_width(dag)
        estimates: Dict[TopologyType, Dict[str, float]] = {}

        for topology in TopologyType:
            profile = TopologySelector._topology_profile(topology, len(dag.nodes))
            expected_latency, waves, worker_time = TopologySelector._schedule(
                dag, node_costs, profile["workers"]
            )
            coordination_overhead = TopologySelector._coordination_overhead(
                topology, dag, waves, profile
            )
            critical_path_impact = critical_path_latency + (
                GraphMetrics.critical_path_length(dag) * profile["critical_path_tax"]
            )
            critical_path_penalty = max(0.0, critical_path_impact - expected_latency) * 0.25
            worker_capacity = max(expected_latency * profile["workers"], 0.000001)
            worker_utilization = min(1.0, worker_time / worker_capacity)
            parallel_efficiency = min(
                1.0, critical_path_impact / max(expected_latency + coordination_overhead, 0.000001)
            )
            score = expected_latency + coordination_overhead + critical_path_penalty
            estimates[topology] = {
                "expected_latency": round(expected_latency, 6),
                "coordination_overhead": round(coordination_overhead, 6),
                "critical_path_impact": round(critical_path_impact, 6),
                "critical_path_penalty": round(critical_path_penalty, 6),
                "weighted_parallel_width": round(weighted_parallel_width, 6),
                "worker_utilization": round(worker_utilization, 6),
                "parallel_efficiency": round(parallel_efficiency, 6),
                "score": round(score, 6),
            }

        return estimates

    @staticmethod
    def _sequential_topology(dag: DAG) -> Dict[str, Any]:
        order = dag.topological_sort()
        return {
            "type": "sequential",
            "execution_order": order,
            "parallel_groups": [[node] for node in order],
        }

    @staticmethod
    def _parallel_topology(dag: DAG) -> Dict[str, Any]:
        levels = {}
        for node in dag.topological_sort():
            pred_levels = [levels[pred] for pred in dag.graph.predecessors(node)]
            levels[node] = max(pred_levels) + 1 if pred_levels else 1

        max_level = max(levels.values(), default=0)
        parallel_groups = [[] for _ in range(max_level)]
        for node, level in levels.items():
            parallel_groups[level - 1].append(node)

        return {
            "type": "parallel",
            "execution_order": dag.topological_sort(),
            "parallel_groups": parallel_groups,
            "levels": levels,
        }

    @staticmethod
    def _schedule(dag: DAG, node_costs: Dict[str, float], workers: int) -> Tuple[float, int, float]:
        remaining = set(dag.nodes.keys())
        indegree = {node: dag.graph.in_degree(node) for node in remaining}
        active: List[Tuple[float, str]] = []
        now = 0.0
        waves = 0
        worker_time = 0.0

        while remaining or active:
            ready = sorted(node for node in remaining if indegree[node] == 0)
            slots = max(0, workers - len(active))
            if ready and slots > 0:
                waves += 1
            for node in ready[:slots]:
                remaining.remove(node)
                duration = node_costs[node]
                active.append((now + duration, node))
                worker_time += duration

            if not active:
                raise RuntimeError("DAG contains a cycle or unresolved dependency.")

            next_finish = min(finish for finish, _node in active)
            now = next_finish
            finished = [item for item in active if math.isclose(item[0], next_finish) or item[0] <= next_finish]
            active = [item for item in active if item not in finished]
            for _finish, node in finished:
                for successor in dag.get_successors(node):
                    indegree[successor] -= 1

        return now, waves, worker_time

    @staticmethod
    def _coordination_overhead(
        topology: TopologyType,
        dag: DAG,
        waves: int,
        profile: Dict[str, float],
    ) -> float:
        depth = GraphMetrics.graph_depth(dag)
        density = GraphMetrics.graph_density(dag)
        width = GraphMetrics.parallel_width(dag)
        max_degree = GraphMetrics.max_degree(dag)
        edge_factor = len(dag.edges) * profile["edge_tax"]
        wave_factor = waves * profile["wave_tax"]
        if topology == TopologyType.HIERARCHICAL:
            hierarchy_bonus = -0.002 * max_degree if max_degree >= max(4, len(dag.nodes) // 3) else 0.0
            return max(0.0, wave_factor + edge_factor + depth * 0.004 + hierarchy_bonus)
        if topology == TopologyType.PARALLEL:
            contention = max(0, width - profile["workers"]) * 0.01
            return wave_factor + edge_factor + density * 0.08 + contention
        if topology == TopologyType.HYBRID:
            return wave_factor + edge_factor + depth * 0.003 + width * 0.002
        return wave_factor + edge_factor

    @staticmethod
    def _topology_profile(topology: TopologyType, node_count: int) -> Dict[str, float]:
        if topology == TopologyType.SEQUENTIAL:
            return {
                "workers": 1,
                "wave_tax": 0.002,
                "edge_tax": 0.0005,
                "critical_path_tax": 0.001,
            }
        if topology == TopologyType.PARALLEL:
            return {
                "workers": min(8, node_count),
                "wave_tax": 0.006,
                "edge_tax": 0.0015,
                "critical_path_tax": 0.004,
            }
        if topology == TopologyType.HIERARCHICAL:
            return {
                "workers": min(6, node_count),
                "wave_tax": 0.011,
                "edge_tax": 0.0017,
                "critical_path_tax": 0.003,
            }
        return {
            "workers": min(6, node_count),
            "wave_tax": 0.009,
            "edge_tax": 0.0014,
            "critical_path_tax": 0.002,
        }

    @staticmethod
    def _hierarchical_topology(dag: DAG) -> Dict[str, Any]:
        if not dag.graph.nodes:
            return {"type": "hierarchical", "execution_order": [], "coordinator": None, "subtask_groups": []}

        candidate = max(dag.graph.nodes, key=lambda node: dag.graph.out_degree(node) + dag.graph.in_degree(node))
        if dag.graph.out_degree(candidate) == 0:
            candidate = dag.topological_sort()[0]

        children = list(dag.graph.successors(candidate))
        subtask_groups: List[List[str]] = []
        assigned = set()
        for child in children:
            group = [child]
            descendants = sorted(nx.descendants(dag.graph, child))
            for descendant in descendants:
                if descendant not in assigned and descendant != candidate:
                    group.append(descendant)
                    assigned.add(descendant)
            subtask_groups.append(group)

        execution_order = [candidate] + [node for group in subtask_groups for node in group]
        return {
            "type": "hierarchical",
            "execution_order": execution_order,
            "coordinator": candidate,
            "subtask_groups": subtask_groups,
        }

    @staticmethod
    def _hybrid_topology(dag: DAG) -> Dict[str, Any]:
        levels = {}
        for node in dag.topological_sort():
            pred_levels = [levels[pred] for pred in dag.graph.predecessors(node)]
            levels[node] = max(pred_levels) + 1 if pred_levels else 1

        max_level = max(levels.values(), default=0)
        layers = [[] for _ in range(max_level)]
        for node, level in levels.items():
            layers[level - 1].append(node)

        return {
            "type": "hybrid",
            "execution_order": dag.topological_sort(),
            "layers": layers,
            "levels": levels,
        }
