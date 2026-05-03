from enum import Enum
from typing import List, Dict, Any
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
        """Select and return the topology configuration."""
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
        """Sequential execution: nodes executed one after another."""
        order = dag.topological_sort()
        return {
            "type": "sequential",
            "execution_order": order,
            "parallel_groups": [[node] for node in order]
        }

    @staticmethod
    def _parallel_topology(dag: DAG) -> Dict[str, Any]:
        """Parallel execution: all independent nodes executed simultaneously."""
        levels = {}
        for node in dag.topological_sort():
            pred_levels = [levels[pred] for pred in dag.graph.predecessors(node)]
            levels[node] = max(pred_levels) + 1 if pred_levels else 1
        max_level = max(levels.values())
        parallel_groups = [[] for _ in range(max_level)]
        for node, level in levels.items():
            parallel_groups[level - 1].append(node)
        return {
            "type": "parallel",
            "execution_order": dag.topological_sort(),
            "parallel_groups": parallel_groups
        }

    @staticmethod
    def _hierarchical_topology(dag: DAG) -> Dict[str, Any]:
        """Hierarchical: organize nodes in a tree-like structure."""
        # Simplified: group by levels
        return TopologySelector._parallel_topology(dag)

    @staticmethod
    def _hybrid_topology(dag: DAG) -> Dict[str, Any]:
        """Hybrid: combination of sequential and parallel."""
        # For now, same as parallel
        return TopologySelector._parallel_topology(dag)