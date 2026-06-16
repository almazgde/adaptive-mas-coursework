import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from adaptive_mas.execution import FailureSimulationConfig
from adaptive_mas.topology import AdaptiveTopologyMode, LearnedTopologySelector, TopologyType
from experiments.benchmarks.runner import BenchmarkRunner
from experiments.benchmarks.synthetic_graphs import SyntheticGraphFactory


DEFAULT_CONFIG: Dict[str, Any] = {
    "graph_types": ["wide_sparse", "deep_dependency", "layered", "centralized_coordinator"],
    "node_count": 32,
    "runs": 15,
    "worker_count": None,
    "selector_mode": "all",
    "enabled_topologies": ["sequential", "parallel", "hierarchical", "hybrid"],
    "output_dir": "results",
    "random_seed": None,
    "quality_evaluation": True,
    "timeline_visualization": False,
    "learned_model_path": None,
    "failure_simulation": {
        "failure_enabled": False,
        "failure_probability": 0.0,
        "timeout_probability": 0.0,
        "empty_result_probability": 0.0,
        "max_retries": 0,
        "timeout_seconds": 1.0,
        "fallback_enabled": False,
    },
}


VALID_SELECTOR_MODES = {
    "all",
    "rule_based",
    "rule_based_adaptive",
    "cost_aware",
    "cost_aware_adaptive",
    "learned",
    "learned_adaptive",
}
VALID_TOPOLOGIES = {topology.value: topology for topology in TopologyType}


def load_config(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError("Config root must be a JSON object.")
    return merge_dicts(DEFAULT_CONFIG, data)


def merge_dicts(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = merge_dicts(merged[key], value)
        else:
            merged[key] = value
    return merged


def apply_overrides(config: Dict[str, Any], args: argparse.Namespace) -> Dict[str, Any]:
    updated = merge_dicts(DEFAULT_CONFIG, config)
    for key in (
        "runs",
        "node_count",
        "worker_count",
        "output_dir",
        "selector_mode",
        "quality_evaluation",
        "learned_model_path",
    ):
        value = getattr(args, key, None)
        if value is not None:
            updated[key] = value
    if getattr(args, "graph", None):
        updated["graph_types"] = [args.graph]
    if getattr(args, "topology", None):
        updated["enabled_topologies"] = args.topology

    failure = dict(updated.get("failure_simulation", {}))
    failure_args = {
        "failure_enabled": getattr(args, "failure_enabled", None),
        "failure_probability": getattr(args, "failure_probability", None),
        "timeout_probability": getattr(args, "timeout_probability", None),
        "empty_result_probability": getattr(args, "empty_result_probability", None),
        "max_retries": getattr(args, "max_retries", None),
        "timeout_seconds": getattr(args, "timeout_seconds", None),
        "fallback_enabled": getattr(args, "fallback_enabled", None),
    }
    for key, value in failure_args.items():
        if value is not None:
            failure[key] = value
    if getattr(args, "random_seed", None) is not None:
        updated["random_seed"] = args.random_seed
    updated["failure_simulation"] = failure
    return updated


def validate_config(config: Dict[str, Any]) -> None:
    invalid_graphs = [graph for graph in config["graph_types"] if graph not in BenchmarkRunner.GRAPH_TYPES]
    if invalid_graphs:
        raise ValueError(f"Invalid graph type(s): {', '.join(invalid_graphs)}")

    selector_mode = config["selector_mode"]
    if selector_mode not in VALID_SELECTOR_MODES:
        raise ValueError(f"Invalid selector mode: {selector_mode}")
    if selector_mode in {"learned", "learned_adaptive"} and not config.get("learned_model_path"):
        raise ValueError("learned_adaptive requires --model or learned_model_path in config.")

    invalid_topologies = [topology for topology in config["enabled_topologies"] if topology not in VALID_TOPOLOGIES]
    if invalid_topologies:
        raise ValueError(f"Invalid topology type(s): {', '.join(invalid_topologies)}")

    output_dir = Path(config["output_dir"])
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise OSError(f"Output directory cannot be created: {output_dir}") from exc


def run_benchmark_from_config(config: Dict[str, Any]) -> List[Any]:
    validate_config(config)
    output_dir = Path(config["output_dir"])
    failure_config = failure_config_from_dict(config)
    static_topologies = [VALID_TOPOLOGIES[name] for name in config["enabled_topologies"]]
    adaptive_modes = adaptive_modes_for_selector(config["selector_mode"])
    if config["selector_mode"] == "all" and config.get("learned_model_path"):
        adaptive_modes.append(AdaptiveTopologyMode.LEARNED)

    print(f"Graph types: {', '.join(config['graph_types'])}")
    print(f"Runs: {config['runs']}")
    print(f"Selector mode: {config['selector_mode']}")
    print(f"Output directory: {output_dir}")

    runner = BenchmarkRunner(
        runs=int(config["runs"]),
        node_count=int(config["node_count"]),
        failure_config=failure_config,
        graph_types=list(config["graph_types"]),
        static_topologies=static_topologies,
        adaptive_modes=adaptive_modes,
        output_dir=output_dir,
        quality_enabled=bool(config.get("quality_evaluation", True)),
        worker_count=config.get("worker_count"),
        learned_model_path=config.get("learned_model_path"),
    )
    results = runner.run_all()
    save_used_config(config, output_dir)
    print(f"Wrote {len(results)} benchmark runs to {runner.csv_path}")
    print(f"Wrote summary to {runner.summary_path}")
    print(f"Wrote used config to {output_dir / 'experiment_config_used.json'}")
    return results


def failure_config_from_dict(config: Dict[str, Any]) -> FailureSimulationConfig:
    failure = config.get("failure_simulation", {})
    return FailureSimulationConfig(
        failure_enabled=bool(failure.get("failure_enabled", False)),
        failure_probability=float(failure.get("failure_probability", 0.0)),
        timeout_probability=float(failure.get("timeout_probability", 0.0)),
        empty_result_probability=float(failure.get("empty_result_probability", 0.0)),
        max_retries=int(failure.get("max_retries", 0)),
        timeout_seconds=float(failure.get("timeout_seconds", 1.0)),
        fallback_enabled=bool(failure.get("fallback_enabled", False)),
        random_seed=config.get("random_seed"),
    )


def adaptive_modes_for_selector(selector_mode: str) -> List[AdaptiveTopologyMode]:
    if selector_mode in {"rule_based", "rule_based_adaptive"}:
        return [AdaptiveTopologyMode.RULE_BASED]
    if selector_mode in {"cost_aware", "cost_aware_adaptive"}:
        return [AdaptiveTopologyMode.COST_AWARE]
    if selector_mode in {"learned", "learned_adaptive"}:
        return [AdaptiveTopologyMode.LEARNED]
    return [AdaptiveTopologyMode.RULE_BASED, AdaptiveTopologyMode.COST_AWARE]


def train_selector_command(args: argparse.Namespace) -> None:
    graph_types = args.graph_types or BenchmarkRunner.GRAPH_TYPES
    selector = LearnedTopologySelector.train(
        graph_types=list(graph_types),
        runs=args.runs,
        node_count=args.node_count,
    )
    output_path = selector.save(Path(args.output))
    print(f"Trained learned selector with {len(selector.samples)} samples")
    print(f"Wrote model to {output_path}")


def save_used_config(config: Dict[str, Any], output_dir: Path) -> None:
    with open(output_dir / "experiment_config_used.json", "w", encoding="utf-8") as handle:
        json.dump(config, handle, indent=2)


def run_demo_command(args: argparse.Namespace) -> None:
    import demo

    scenarios = {
        "wide_sparse": (demo.build_wide_sparse_graph(), TopologyType.PARALLEL),
        "deep_dependency": (demo.build_deep_dependency_graph(), TopologyType.SEQUENTIAL),
        "layered": (demo.build_layered_graph(), TopologyType.HYBRID),
        "central_coordinator": (demo.build_central_coordinator_graph(), TopologyType.HIERARCHICAL),
    }
    selected = [args.scenario] if args.scenario else list(scenarios)
    failure_config = FailureSimulationConfig(
        failure_enabled=args.failure_enabled,
        failure_probability=args.failure_probability,
        timeout_probability=args.timeout_probability,
        empty_result_probability=args.empty_result_probability,
        max_retries=args.max_retries,
        timeout_seconds=args.timeout_seconds,
        fallback_enabled=args.fallback_enabled,
        random_seed=args.random_seed,
    )
    for name in selected:
        if name not in scenarios:
            raise ValueError(f"Invalid demo scenario: {name}")
        dag, topology = scenarios[name]
        demo.run_scenario(name, dag, topology, failure_config)


def run_visualize_command(args: argparse.Namespace) -> None:
    if args.trace:
        from visualize_execution_timeline import load_trace, output_path_for, plot_timeline

        trace_path = Path(args.trace)
        trace = load_trace(trace_path)
        output_path = Path(args.output) if args.output else output_path_for(trace_path, trace)
        saved_path = plot_timeline(trace, output_path)
        print(f"Wrote execution timeline to {saved_path}")
    else:
        import visualize_results

        visualize_results.main()


def run_experiment_command(args: argparse.Namespace) -> None:
    config = load_config(Path(args.config))
    config = apply_overrides(config, args)
    run_benchmark_from_config(config)
    if config.get("timeline_visualization"):
        trace_path = Path(config["output_dir"]) / "execution_trace.json"
        if trace_path.exists():
            namespace = argparse.Namespace(trace=str(trace_path), output=None)
            run_visualize_command(namespace)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Unified CLI for Adaptive MAS coursework experiments.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    demo_parser = subparsers.add_parser("demo", help="Run demo DAG scenarios.")
    demo_parser.add_argument("--scenario", choices=["wide_sparse", "deep_dependency", "layered", "central_coordinator"])
    demo_parser.add_argument("--random-seed", type=int)
    add_failure_args(demo_parser)
    demo_parser.set_defaults(handler=run_demo_command)

    benchmark_parser = subparsers.add_parser("benchmark", help="Run synthetic benchmarks.")
    add_benchmark_args(benchmark_parser)
    benchmark_parser.set_defaults(handler=lambda args: run_benchmark_from_config(apply_overrides(DEFAULT_CONFIG, args)))

    train_parser = subparsers.add_parser("train-selector", help="Train lightweight learned adaptive selector.")
    train_parser.add_argument("--runs", type=int, default=100)
    train_parser.add_argument("--node-count", type=int, default=32)
    train_parser.add_argument("--graph-types", action="append", choices=BenchmarkRunner.GRAPH_TYPES)
    train_parser.add_argument("--output", default="results/learned_selector_model.json")
    train_parser.set_defaults(handler=train_selector_command)

    visualize_parser = subparsers.add_parser("visualize", help="Generate benchmark plots or a timeline from trace.")
    visualize_parser.add_argument("--trace", help="Execution trace JSON for Gantt timeline.")
    visualize_parser.add_argument("--output", help="Optional output PNG path for timeline.")
    visualize_parser.set_defaults(handler=run_visualize_command)

    experiment_parser = subparsers.add_parser("experiment", help="Run benchmark experiment from JSON config.")
    experiment_parser.add_argument("--config", required=True, help="Path to experiment JSON config.")
    add_benchmark_args(experiment_parser)
    experiment_parser.set_defaults(handler=run_experiment_command)

    return parser


def add_benchmark_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--runs", type=int)
    parser.add_argument("--node-count", type=int)
    parser.add_argument("--worker-count", type=int)
    parser.add_argument("--graph", choices=BenchmarkRunner.GRAPH_TYPES)
    parser.add_argument("--selector", dest="selector_mode", choices=sorted(VALID_SELECTOR_MODES))
    parser.add_argument("--model", dest="learned_model_path")
    parser.add_argument("--topology", action="append", choices=sorted(VALID_TOPOLOGIES))
    parser.add_argument("--output-dir")
    parser.add_argument("--random-seed", type=int)
    parser.add_argument("--quality-evaluation", action=argparse.BooleanOptionalAction)
    add_failure_args(parser)


def add_failure_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--failure-enabled", action="store_true", default=None)
    parser.add_argument("--failure-probability", type=float)
    parser.add_argument("--timeout-probability", type=float)
    parser.add_argument("--empty-result-probability", type=float)
    parser.add_argument("--max-retries", type=int)
    parser.add_argument("--timeout-seconds", type=float)
    parser.add_argument("--fallback-enabled", action="store_true", default=None)


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        args.handler(args)
    except (FileNotFoundError, json.JSONDecodeError, ValueError, OSError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
