import argparse
import csv
import math
import random
import statistics
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

from adaptive_mas.dag import DAG
from adaptive_mas.evaluation import QualityEvaluator, RobustnessEvaluator
from adaptive_mas.execution import FailureSimulationConfig
from adaptive_mas.metrics import GraphMetrics
from adaptive_mas.topology import AdaptiveTopologyMode, LearnedTopologySelector, TopologySelector, TopologyType

from .synthetic_graphs import SyntheticGraphFactory


RESULTS_DIR = Path("results")
CSV_PATH = RESULTS_DIR / "benchmark_results.csv"
SUMMARY_PATH = RESULTS_DIR / "benchmark_summary.csv"


@dataclass
class BenchmarkResult:
    run_id: int
    strategy_group: str
    strategy: str
    selector_mode: str
    adaptive_mode: str
    requested_topology: str
    topology: str
    selected_topology: str
    learned_model_used: str
    objective_score: float
    graph_type: str
    node_count: int
    edge_count: int
    graph_depth: int
    critical_path_length: int
    total_node_cost: float
    avg_node_cost: float
    max_node_cost: float
    cost_variance: float
    weighted_critical_path: float
    weighted_parallel_width: float
    execution_latency: float
    latency: float
    critical_path_latency: float
    execution_cost: float
    cost: float
    parallel_efficiency: float
    coordination_overhead: float
    executor_utilization: float
    completeness_score: float
    consistency_score: float
    synthesis_score: float
    dependency_coverage_score: float
    overall_quality_score: float
    failure_enabled: bool
    success_rate: float
    failed_node_count: int
    skipped_node_count: int
    retry_count_total: int
    fallback_count: int
    recovery_success_rate: float
    wasted_work_estimate: float


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
    ADAPTIVE_MODES = [
        AdaptiveTopologyMode.RULE_BASED,
        AdaptiveTopologyMode.COST_AWARE,
    ]

    def __init__(
        self,
        runs: int = 15,
        node_count: int = 32,
        failure_config: Optional[FailureSimulationConfig] = None,
        graph_types: Optional[List[str]] = None,
        static_topologies: Optional[List[TopologyType]] = None,
        adaptive_modes: Optional[List[AdaptiveTopologyMode]] = None,
        output_dir: Path = RESULTS_DIR,
        quality_enabled: bool = True,
        worker_count: Optional[int] = None,
        learned_model_path: Optional[Path] = None,
    ):
        self.runs = runs
        self.node_count = node_count
        self.failure_config = failure_config or FailureSimulationConfig()
        self.graph_types = graph_types or list(self.GRAPH_TYPES)
        self.static_topologies = static_topologies if static_topologies is not None else list(self.STATIC_TOPOLOGIES)
        self.adaptive_modes = adaptive_modes if adaptive_modes is not None else list(self.ADAPTIVE_MODES)
        self.results_dir = Path(output_dir)
        self.csv_path = self.results_dir / "benchmark_results.csv"
        self.summary_path = self.results_dir / "benchmark_summary.csv"
        self.quality_enabled = quality_enabled
        self.worker_count = worker_count
        self.learned_model_path = Path(learned_model_path) if learned_model_path else None
        self.learned_selector = LearnedTopologySelector.load(self.learned_model_path) if self.learned_model_path else None
        self.results_dir.mkdir(exist_ok=True)

    def run_all(self) -> List[BenchmarkResult]:
        results: List[BenchmarkResult] = []
        for graph_type in self.graph_types:
            for run_id in range(1, self.runs + 1):
                dag = SyntheticGraphFactory.create(graph_type, self.node_count, seed=run_id)
                for topology in self.static_topologies:
                    static_estimate = TopologySelector.estimate_topology_costs(dag)[topology]
                    results.append(
                        self._run_single(
                            dag,
                            graph_type,
                            run_id,
                            "static",
                            "static",
                            topology,
                            topology.value,
                            objective_score=LearnedTopologySelector.objective_score(static_estimate, dag),
                        )
                    )

                for adaptive_mode in self.adaptive_modes:
                    if adaptive_mode == AdaptiveTopologyMode.LEARNED:
                        if self.learned_selector is None:
                            raise FileNotFoundError("learned_adaptive requires --model / learned_model_path.")
                        prediction = self.learned_selector.predict(dag)
                        adaptive_type = prediction.topology
                        objective_score = prediction.objective_score
                    elif adaptive_mode == AdaptiveTopologyMode.COST_AWARE:
                        adaptive_type = TopologySelector.select_cost_aware_adaptive_topology_type(dag)
                        objective_score = TopologySelector.estimate_topology_costs(dag)[adaptive_type]["score"]
                    else:
                        adaptive_type = TopologySelector.select_rule_based_adaptive_topology_type(dag)
                        objective_score = 0.0
                    results.append(
                        self._run_single(
                            dag,
                            graph_type,
                            run_id,
                            "adaptive",
                            adaptive_mode.value,
                            adaptive_type,
                            adaptive_mode.value,
                            objective_score=objective_score,
                        )
                    )

        self.write_results(results)
        self.write_summary(results)
        return results

    def _run_single(
        self,
        dag: DAG,
        graph_type: str,
        run_id: int,
        strategy_group: str,
        adaptive_mode: str,
        topology: TopologyType,
        requested_topology: str,
        objective_score: float = 0.0,
    ) -> BenchmarkResult:
        profile = self._topology_profile(topology, len(dag.nodes))
        if self.worker_count is not None:
            profile["workers"] = max(1, min(self.worker_count, len(dag.nodes)))
        node_costs = GraphMetrics.node_costs(dag)
        base_work = GraphMetrics.total_node_cost(dag)
        weighted_critical_path = GraphMetrics.weighted_critical_path_length(dag)
        schedule_latency, waves, worker_time = self._schedule(dag, node_costs, profile["workers"])
        coordination_overhead = self._coordination_overhead(topology, dag, waves, profile)
        execution_latency = schedule_latency + coordination_overhead
        critical_path_latency = weighted_critical_path + (
            GraphMetrics.critical_path_length(dag) * profile["critical_path_tax"]
        )
        execution_cost = base_work + coordination_overhead * profile["cost_multiplier"]
        worker_capacity = max(execution_latency * profile["workers"], 0.000001)
        executor_utilization = min(1.0, worker_time / worker_capacity)
        parallel_efficiency = min(1.0, critical_path_latency / execution_latency) if execution_latency > 0 else 0.0
        simulated_trace = self._simulated_trace(
            dag,
            topology,
            execution_latency,
            critical_path_latency,
            run_id,
        )
        quality = QualityEvaluator.evaluate(simulated_trace, dag) if self.quality_enabled else None
        robustness = RobustnessEvaluator.evaluate(simulated_trace, dag)

        return BenchmarkResult(
            run_id=run_id,
            strategy_group=strategy_group,
            strategy=requested_topology,
            selector_mode=adaptive_mode,
            adaptive_mode=adaptive_mode,
            requested_topology=requested_topology,
            topology=topology.value,
            selected_topology=topology.value,
            learned_model_used=str(self.learned_model_path) if adaptive_mode == AdaptiveTopologyMode.LEARNED.value else "",
            objective_score=round(objective_score, 6),
            graph_type=graph_type,
            node_count=len(dag.nodes),
            edge_count=len(dag.edges),
            graph_depth=GraphMetrics.graph_depth(dag),
            critical_path_length=GraphMetrics.critical_path_length(dag),
            total_node_cost=round(base_work, 6),
            avg_node_cost=round(GraphMetrics.average_node_cost(dag), 6),
            max_node_cost=round(GraphMetrics.max_node_cost(dag), 6),
            cost_variance=round(GraphMetrics.cost_variance(dag), 6),
            weighted_critical_path=round(weighted_critical_path, 6),
            weighted_parallel_width=round(GraphMetrics.weighted_parallel_width(dag), 6),
            execution_latency=round(execution_latency, 6),
            latency=round(execution_latency, 6),
            critical_path_latency=round(critical_path_latency, 6),
            execution_cost=round(execution_cost, 6),
            cost=round(execution_cost, 6),
            parallel_efficiency=round(parallel_efficiency, 6),
            coordination_overhead=round(coordination_overhead, 6),
            executor_utilization=round(executor_utilization, 6),
            completeness_score=quality.completeness_score if quality else 0.0,
            consistency_score=quality.consistency_score if quality else 0.0,
            synthesis_score=quality.synthesis_score if quality else 0.0,
            dependency_coverage_score=quality.dependency_coverage_score if quality else 0.0,
            overall_quality_score=quality.overall_quality_score if quality else 0.0,
            failure_enabled=self.failure_config.failure_enabled,
            success_rate=robustness.success_rate,
            failed_node_count=robustness.failed_node_count,
            skipped_node_count=robustness.skipped_node_count,
            retry_count_total=robustness.retry_count_total,
            fallback_count=robustness.fallback_count,
            recovery_success_rate=robustness.recovery_success_rate,
            wasted_work_estimate=robustness.wasted_work_estimate,
        )

    def write_results(self, results: Iterable[BenchmarkResult]) -> None:
        rows = [asdict(result) for result in results]
        with open(self.csv_path, "w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)

    def write_summary(self, results: Iterable[BenchmarkResult]) -> None:
        grouped: Dict[Tuple[str, str, str, str], List[BenchmarkResult]] = {}
        for result in results:
            key = (
                result.graph_type,
                result.strategy_group,
                result.adaptive_mode,
                result.requested_topology,
            )
            grouped.setdefault(key, []).append(result)

        rows = []
        for (graph_type, strategy_group, adaptive_mode, requested_topology), items in sorted(grouped.items()):
            latencies = [item.execution_latency for item in items]
            rows.append(
                {
                    "graph_type": graph_type,
                    "strategy_group": strategy_group,
                    "adaptive_mode": adaptive_mode,
                    "requested_topology": requested_topology,
                    "selected_topology": self._mode(item.topology for item in items),
                    "runs": len(items),
                    "average_latency": round(statistics.mean(latencies), 6),
                    "std_latency": round(statistics.stdev(latencies), 6) if len(latencies) > 1 else 0.0,
                    "average_cost": round(statistics.mean(item.execution_cost for item in items), 6),
                    "average_total_node_cost": round(
                        statistics.mean(item.total_node_cost for item in items), 6
                    ),
                    "average_weighted_critical_path": round(
                        statistics.mean(item.weighted_critical_path for item in items), 6
                    ),
                    "average_weighted_parallel_width": round(
                        statistics.mean(item.weighted_parallel_width for item in items), 6
                    ),
                    "average_parallel_efficiency": round(
                        statistics.mean(item.parallel_efficiency for item in items), 6
                    ),
                    "average_coordination_overhead": round(
                        statistics.mean(item.coordination_overhead for item in items), 6
                    ),
                    "average_executor_utilization": round(
                        statistics.mean(item.executor_utilization for item in items), 6
                    ),
                    "average_completeness_score": round(
                        statistics.mean(item.completeness_score for item in items), 6
                    ),
                    "average_consistency_score": round(
                        statistics.mean(item.consistency_score for item in items), 6
                    ),
                    "average_synthesis_score": round(
                        statistics.mean(item.synthesis_score for item in items), 6
                    ),
                    "average_dependency_coverage_score": round(
                        statistics.mean(item.dependency_coverage_score for item in items), 6
                    ),
                    "average_overall_quality_score": round(
                        statistics.mean(item.overall_quality_score for item in items), 6
                    ),
                    "failure_enabled": any(item.failure_enabled for item in items),
                    "average_success_rate": round(statistics.mean(item.success_rate for item in items), 6),
                    "average_failed_node_count": round(
                        statistics.mean(item.failed_node_count for item in items), 6
                    ),
                    "average_skipped_node_count": round(
                        statistics.mean(item.skipped_node_count for item in items), 6
                    ),
                    "average_retry_count_total": round(
                        statistics.mean(item.retry_count_total for item in items), 6
                    ),
                    "average_fallback_count": round(
                        statistics.mean(item.fallback_count for item in items), 6
                    ),
                    "average_recovery_success_rate": round(
                        statistics.mean(item.recovery_success_rate for item in items), 6
                    ),
                    "average_wasted_work_estimate": round(
                        statistics.mean(item.wasted_work_estimate for item in items), 6
                    ),
                }
            )

        with open(self.summary_path, "w", newline="", encoding="utf-8") as handle:
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

    def _simulated_trace(
        self,
        dag: DAG,
        topology: TopologyType,
        execution_latency: float,
        critical_path_latency: float,
        run_id: int,
    ) -> Dict[str, object]:
        topology_config = TopologySelector.select_topology(dag, topology)
        node_traces = []
        rng = random.Random((self.failure_config.random_seed or 0) + run_id)
        blocked_nodes = set()
        for order, node_id in enumerate(dag.topological_sort()):
            node = dag.get_node(node_id)
            task = node.task if node else node_id
            agent = self._agent_name_for_task(task)
            if any(predecessor in blocked_nodes for predecessor in dag.get_predecessors(node_id)):
                status = "skipped"
                retry_count = 0
                used_fallback = False
                result = {}
                error_message = "predecessor_failed"
                blocked_nodes.add(node_id)
            else:
                status, retry_count, used_fallback, result, error_message = self._simulate_node_result(
                    rng, node_id, agent
                )
                if status in {"failed", "timeout"}:
                    blocked_nodes.add(node_id)
            node_traces.append(
                {
                    "node_id": node_id,
                    "task": task,
                    "agent": agent,
                    "order": order,
                    "status": status,
                    "retry_count": retry_count,
                    "error_message": error_message,
                    "used_fallback": used_fallback,
                    "start_time": float(order),
                    "end_time": float(order + 1),
                    "duration": 1.0,
                    "topology": topology.value,
                    "result": result,
                }
            )
        return {
            "topology_type": topology.value,
            "topology_config": topology_config,
            "execution_order": [item["node_id"] for item in node_traces],
            "duration": execution_latency,
            "critical_path_duration": critical_path_latency,
            "node_traces": node_traces,
        }

    def _simulate_node_result(self, rng: random.Random, node_id: str, agent: str):
        if not self.failure_config.failure_enabled:
            return "success", 0, False, {"status": "ok", "agent": agent}, None

        retry_count = 0
        status = "success"
        error_message = None
        for attempt in range(self.failure_config.max_retries + 1):
            status, error_message = self._simulate_attempt(rng)
            if status == "success":
                result = {"status": "ok", "agent": agent}
                return "success", retry_count, False, result, None
            if status == "empty":
                return "success", retry_count, False, {}, None
            if attempt < self.failure_config.max_retries:
                retry_count += 1

        if self.failure_config.fallback_enabled:
            return (
                "fallback",
                retry_count,
                True,
                {"fallback": True, "node_id": node_id, "agent": agent, "reason": error_message},
                error_message,
            )
        return status, retry_count, False, {}, error_message

    def _simulate_attempt(self, rng: random.Random) -> Tuple[str, Optional[str]]:
        if rng.random() < self.failure_config.failure_probability:
            return "failed", "Simulated agent exception"
        if rng.random() < self.failure_config.timeout_probability:
            return "timeout", f"Timed out after {self.failure_config.timeout_seconds}s"
        if rng.random() < self.failure_config.empty_result_probability:
            return "empty", None
        return "success", None

    def _agent_name_for_task(self, task: str) -> str:
        task_lower = task.lower()
        if "synth" in task_lower or "aggregate" in task_lower:
            return "SynthesizerAgent"
        if "critic" in task_lower or "assess" in task_lower:
            return "CriticAgent"
        if "research" in task_lower:
            return "ResearcherAgent"
        return "PlannerAgent"

    def _mode(self, values: Iterable[str]) -> str:
        counts: Dict[str, int] = {}
        for value in values:
            counts[value] = counts.get(value, 0) + 1
        return max(counts, key=counts.get)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run synthetic topology benchmarks.")
    parser.add_argument("--runs", type=int, default=15)
    parser.add_argument("--node-count", type=int, default=32)
    parser.add_argument("--failure-enabled", action="store_true", help="Enable failure simulation in benchmark traces.")
    parser.add_argument("--failure-probability", type=float, default=0.0)
    parser.add_argument("--timeout-probability", type=float, default=0.0)
    parser.add_argument("--empty-result-probability", type=float, default=0.0)
    parser.add_argument("--max-retries", type=int, default=0)
    parser.add_argument("--timeout-seconds", type=float, default=1.0)
    parser.add_argument("--fallback-enabled", action="store_true")
    parser.add_argument("--failure-seed", type=int, default=None)
    args = parser.parse_args()
    failure_config = FailureSimulationConfig(
        failure_enabled=args.failure_enabled,
        failure_probability=args.failure_probability,
        timeout_probability=args.timeout_probability,
        empty_result_probability=args.empty_result_probability,
        max_retries=args.max_retries,
        timeout_seconds=args.timeout_seconds,
        fallback_enabled=args.fallback_enabled,
        random_seed=args.failure_seed,
    )
    runner = BenchmarkRunner(runs=args.runs, node_count=args.node_count, failure_config=failure_config)
    results = runner.run_all()
    print(f"Wrote {len(results)} benchmark runs to {runner.csv_path}")
    print(f"Wrote summary to {runner.summary_path}")
    print(f"Graph complexity: {runner.node_count} nodes, {runner.runs} runs per scenario")
    print(f"Failure simulation enabled: {runner.failure_config.failure_enabled}")


if __name__ == "__main__":
    main()
