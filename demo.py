import argparse
import asyncio
import json
from adaptive_mas.dag import DAG, Node, Edge
from adaptive_mas.evaluation import QualityEvaluator, RobustnessEvaluator
from adaptive_mas.execution import ExecutionManager, FailureSimulationConfig
from adaptive_mas.topology.selector import TopologyType
from adaptive_mas.metrics.graph_metrics import GraphMetrics


def build_wide_sparse_graph() -> DAG:
    dag = DAG()
    dag.add_node(Node("root", "plan root"))
    for i in range(1, 6):
        dag.add_node(Node(f"leaf-{i}", f"research leaf {i}"))
        dag.add_edge(Edge("root", f"leaf-{i}"))
    return dag


def build_deep_dependency_graph() -> DAG:
    dag = DAG()
    previous = "task-0"
    dag.add_node(Node(previous, "plan step 0"))
    for i in range(1, 7):
        current = f"task-{i}"
        dag.add_node(Node(current, f"research step {i}"))
        dag.add_edge(Edge(previous, current))
        previous = current
    return dag


def build_layered_graph() -> DAG:
    dag = DAG()
    layer1 = ["entry-a", "entry-b"]
    layer2 = ["mid-a", "mid-b", "mid-c"]
    layer3 = ["exit-a", "exit-b"]
    for node in layer1 + layer2 + layer3:
        dag.add_node(Node(node, f"research {node}"))
    dag.add_edge(Edge("entry-a", "mid-a"))
    dag.add_edge(Edge("entry-a", "mid-b"))
    dag.add_edge(Edge("entry-b", "mid-b"))
    dag.add_edge(Edge("entry-b", "mid-c"))
    dag.add_edge(Edge("mid-a", "exit-a"))
    dag.add_edge(Edge("mid-b", "exit-a"))
    dag.add_edge(Edge("mid-c", "exit-b"))
    return dag


def build_central_coordinator_graph() -> DAG:
    dag = DAG()
    dag.add_node(Node("coordinator", "plan coordinator"))
    dag.add_node(Node("research-1", "research node 1"))
    dag.add_node(Node("research-2", "research node 2"))
    dag.add_node(Node("critique", "critic node"))
    dag.add_node(Node("synthesize", "synthesize node"))
    dag.add_edge(Edge("coordinator", "research-1"))
    dag.add_edge(Edge("coordinator", "research-2"))
    dag.add_edge(Edge("research-1", "critique"))
    dag.add_edge(Edge("research-2", "synthesize"))
    return dag


def run_scenario(
    name: str,
    dag: DAG,
    topology_type: TopologyType,
    failure_config: FailureSimulationConfig = None,
):
    print(f"--- Scenario: {name} ({topology_type.value}) ---")
    print(f"Nodes: {len(dag.nodes)}")
    print(f"Acyclic: {dag.is_acyclic()}")
    print(f"Graph depth: {GraphMetrics.graph_depth(dag)}")
    print(f"Graph density: {GraphMetrics.graph_density(dag):.3f}")
    print(f"Parallel width: {GraphMetrics.parallel_width(dag)}")
    executor = ExecutionManager.create_executor(dag, topology_type, failure_config=failure_config)
    trace = asyncio.run(executor.execute())
    quality = QualityEvaluator.evaluate(trace, dag)
    robustness = RobustnessEvaluator.evaluate(trace, dag)
    print(f"Topology selected: {trace.topology_type}")
    print(f"Execution order: {trace.execution_order}")
    print(f"Total duration: {trace.duration:.3f}s")
    print(f"Critical path duration: {trace.critical_path_duration:.3f}s")
    print(f"Overall quality score: {quality.overall_quality_score:.3f}")
    print(f"Success rate: {robustness.success_rate:.3f}")
    print(f"Failed nodes: {robustness.failed_node_count}, skipped nodes: {robustness.skipped_node_count}")
    print(f"Retries: {robustness.retry_count_total}, fallbacks: {robustness.fallback_count}")
    print(f"Node traces: {len(trace.node_traces)}")
    print()
    with open(f"results/scenario_{name.replace(' ', '_')}_{topology_type.value}_trace.json", "w", encoding="utf-8") as handle:
        payload = trace.__dict__.copy()
        payload["quality_metrics"] = quality.to_dict()
        payload["robustness_metrics"] = robustness.to_dict()
        json.dump(payload, handle, indent=2)


def main():
    parser = argparse.ArgumentParser(description="Run demo DAG scenarios.")
    parser.add_argument("--failure-enabled", action="store_true", help="Enable lightweight failure simulation.")
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
    scenarios = [
        ("wide_sparse", build_wide_sparse_graph(), TopologyType.PARALLEL),
        ("deep_dependency", build_deep_dependency_graph(), TopologyType.SEQUENTIAL),
        ("layered", build_layered_graph(), TopologyType.HYBRID),
        ("central_coordinator", build_central_coordinator_graph(), TopologyType.HIERARCHICAL),
    ]
    for name, dag, topology in scenarios:
        run_scenario(name, dag, topology, failure_config)


if __name__ == "__main__":
    main()
