import csv
import math
import statistics
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

from adaptive_mas.dag import DAG
from adaptive_mas.metrics import GraphMetrics
from adaptive_mas.topology import TopologySelector, TopologyType

from .synthetic_graphs import SyntheticGraphFactory


RESULTS_DIR = Path("results")
CSV_PATH = RESULTS_DIR / "benchmark_results.csv"
SUMMARY_PATH = RESULTS_DIR / "benchmark_summary.csv"


@dataclass
class BenchmarkResult:
    run_id: int
    strategy_group: str
    requested_topology: str
    topology: str
    graph_type: str
    node_count: int
    edge_count: int
    graph_depth: int
    critical_path_length: int
    execution_latency: float
    critical_path_latency: float
    execution_cost: float
    parallel_efficiency: float
    coordination_overhead: float
    executor_utilization: float


class BenchmarkRunner:
    """Runs synthetic orchestration benchmarks and exports CSV results."""

    GRAPH_TYPES = [
        "wide_sparse",
        "deep_dependency",
        "layered",
        "centralized_coordinator",
    ]
    STATIC_TOPOLOGIES = [
        TopologyType.SEQUENTIAL,
        TopologyType.PARALLEL,
        TopologyType.HIERARCHICAL,
        TopologyType.HYBRID,
    ]

    def __init__(self, runs: int = 15, node_count: int = 32):
        self.runs = runs
        self.node_count = node_count
        RESULTS_DIR.mkdir(exist_ok=True)

    def run_all(self) -> List[BenchmarkResult]:
        results: List[BenchmarkResult] = []
        for graph_type in self.GRAPH_TYPES:
            for run_id in range(1, self.runs + 1):
                dag = SyntheticGraphFactory.create(graph_type, self.node_count, seed=run_id)
                for topology in self.STATIC_TOPOLOGIES:
                    results.append(self._run_single(dag, graph_type, run_id, "static", topology, topology.value))

                adaptive_type = TopologySelector.select_adaptive_topology_type(dag)
                results.append(self._run_single(dag, graph_type, run_id, "adaptive", adaptive_type, "adaptive"))

        self.write_results(results)
        self.write_summary(results)
        return results

    def _run_single(
        self,
        dag: DAG,
        graph_type: str,
        run_id: int,
        strategy_group: str,
        topology: TopologyType,
        requested_topology: str,
    ) -> BenchmarkResult:
        profile = self._topology_profile(topology, len(dag.nodes))
        node_costs = {node_id: dag.get_node(node_id).data["cost"] for node_id in dag.nodes}
        base_work = sum(node_costs.values())
        schedule_latency, waves, worker_time = self._schedule(dag, node_costs, profile["workers"])
        coordination_overhead = self._coordination_overhead(topology, dag, waves, profile)
        execution_latency = schedule_latency + coordination_overhead
        critical_path_latency = self._weighted_critical_path(dag, node_costs) + (
            GraphMetrics.critical_path_length(dag) * profile["critical_path_tax"]
        )
        execution_cost = base_work + coordination_overhead * profile["cost_multiplier"]
        worker_capacity = max(execution_latency * profile["workers"], 0.000001)
        executor_utilization = min(1.0, worker_time / worker_capacity)
        parallel_efficiency = min(1.0, critical_path_latency / execution_latency) if execution_latency > 0 else 0.0

        return BenchmarkResult(
            run_id=run_id,
            strategy_group=strategy_group,
            requested_topology=requested_topology,
            topology=topology.value,
            graph_type=graph_type,
            node_count=len(dag.nodes),
            edge_count=len(dag.edges),
            graph_depth=GraphMetrics.graph_depth(dag),
            critical_path_length=GraphMetrics.critical_path_length(dag),
            execution_latency=round(execution_latency, 6),
            critical_path_latency=round(critical_path_latency, 6),
            execution_cost=round(execution_cost, 6),
            parallel_efficiency=round(parallel_efficiency, 6),
            coordination_overhead=round(coordination_overhead, 6),
            executor_utilization=round(executor_utilization, 6),
        )

    def write_results(self, results: Iterable[BenchmarkResult]) -> None:
        rows = [asdict(result) for result in results]
        with open(CSV_PATH, "w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)

    def write_summary(self, results: Iterable[BenchmarkResult]) -> None:
        grouped: Dict[Tuple[str, str, str], List[BenchmarkResult]] = {}
        for result in results:
            key = (result.graph_type, result.strategy_group, result.requested_topology)
            grouped.setdefault(key, []).append(result)

        rows = []
        for (graph_type, strategy_group, requested_topology), items in sorted(grouped.items()):
            latencies = [item.execution_latency for item in items]
            rows.append(
                {
                    "graph_type": graph_type,
                    "strategy_group": strategy_group,
                    "requested_topology": requested_topology,
                    "selected_topology": self._mode(item.topology for item in items),
                    "runs": len(items),
                    "average_latency": round(statistics.mean(latencies), 6),
                    "std_latency": round(statistics.stdev(latencies), 6) if len(latencies) > 1 else 0.0,
                    "average_cost": round(statistics.mean(item.execution_cost for item in items), 6),
                    "average_parallel_efficiency": round(
                        statistics.mean(item.parallel_efficiency for item in items), 6
                    ),
                    "average_coordination_overhead": round(
                        statistics.mean(item.coordination_overhead for item in items), 6
                    ),
                    "average_executor_utilization": round(
                        statistics.mean(item.executor_utilization for item in items), 6
                    ),
                }
            )

        with open(SUMMARY_PATH, "w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)

    def _schedule(self, dag: DAG, node_costs: Dict[str, float], workers: int) -> Tuple[float, int, float]:
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

    def _weighted_critical_path(self, dag: DAG, node_costs: Dict[str, float]) -> float:
        longest: Dict[str, float] = {}
        for node in dag.topological_sort():
            predecessors = dag.get_predecessors(node)
            if predecessors:
                longest[node] = max(longest[pred] for pred in predecessors) + node_costs[node]
            else:
                longest[node] = node_costs[node]
        return max(longest.values(), default=0.0)

    def _coordination_overhead(self, topology: TopologyType, dag: DAG, waves: int, profile: Dict[str, float]) -> float:
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

    def _topology_profile(self, topology: TopologyType, node_count: int) -> Dict[str, float]:
        if topology == TopologyType.SEQUENTIAL:
            return {
                "workers": 1,
                "wave_tax": 0.002,
                "edge_tax": 0.0005,
                "critical_path_tax": 0.001,
                "cost_multiplier": 0.6,
            }
        if topology == TopologyType.PARALLEL:
            return {
                "workers": min(8, node_count),
                "wave_tax": 0.006,
                "edge_tax": 0.0015,
                "critical_path_tax": 0.004,
                "cost_multiplier": 1.4,
            }
        if topology == TopologyType.HIERARCHICAL:
            return {
                "workers": min(6, node_count),
                "wave_tax": 0.011,
                "edge_tax": 0.0017,
                "critical_path_tax": 0.003,
                "cost_multiplier": 1.1,
            }
        return {
            "workers": min(6, node_count),
            "wave_tax": 0.009,
            "edge_tax": 0.0014,
            "critical_path_tax": 0.002,
            "cost_multiplier": 0.95,
        }

    def _mode(self, values: Iterable[str]) -> str:
        counts: Dict[str, int] = {}
        for value in values:
            counts[value] = counts.get(value, 0) + 1
        return max(counts, key=counts.get)


def main() -> None:
    # Запуск с увеличенной сложностью: 32 узла, 15 повторов
    runner = BenchmarkRunner(runs=15, node_count=32)
    results = runner.run_all()
    print(f"Wrote {len(results)} benchmark runs to {CSV_PATH}")
    print(f"Wrote summary to {SUMMARY_PATH}")
    print(f"Graph complexity: {runner.node_count} nodes, {runner.runs} runs per scenario")


if __name__ == "__main__":
    main()
