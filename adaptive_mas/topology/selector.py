from enum import Enum
from typing import List, Dict, Any
import networkx as nx
from ..dag.dag import DAG


class TopologyType(Enum):
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    HIERARCHICAL = "hierarchical"
    HYBRID = "hybrid"


class TopologySelector:
    """Selects and applies topology strategies to the DAG."""

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
