# Adaptive MAS Coursework

Research prototype for adaptive orchestration of multi-agent LLM-style systems represented as task dependency DAGs.

The project focuses on orchestration mechanics rather than a production agent framework. It uses mock agents and synthetic benchmark graphs to compare topology strategies by latency, cost, quality, robustness, and reproducibility.

## Features

- DAG abstraction for task dependencies using NetworkX.
- Structural graph metrics: depth, density, parallel width, max degree, critical path length.
- Weighted graph metrics: node cost, total/average/max cost, cost variance, weighted critical path, weighted parallel width.
- Static topologies: `sequential`, `parallel`, `hierarchical`, `hybrid`.
- Adaptive selectors:
  - `rule_based_adaptive`: structural heuristic.
  - `cost_aware_adaptive`: estimates latency, coordination overhead, critical path penalty, and worker utilization before choosing a topology.
  - `learned_adaptive`: dependency-free nearest-neighbor baseline trained from synthetic benchmark data.
- Async execution layer with per-node traces.
- Gantt-style execution timeline visualization.
- Synthetic benchmark runner with CSV and summary outputs.
- Heuristic quality evaluation for mock traces.
- Failure simulation and recovery: exceptions, timeouts, empty results, retries, fallback, skipped descendants.
- Unified CLI and JSON experiment configs.
- Lightweight `unittest` suite with reproducibility checks.

## Architecture

| Module | Purpose |
|---|---|
| `adaptive_mas/dag` | `Node`, `Edge`, and `DAG` models |
| `adaptive_mas/metrics` | structural and weighted DAG metrics |
| `adaptive_mas/topology` | topology materialization and adaptive selection |
| `adaptive_mas/agents` | mock Planner/Researcher/Critic/Synthesizer agents |
| `adaptive_mas/execution` | executors, traces, failure simulation, recovery |
| `adaptive_mas/evaluation` | quality and robustness evaluators |
| `experiments/benchmarks` | synthetic graph factory and benchmark runner |
| `configs` | JSON experiment configurations |
| `results` | generated CSV, traces, plots, and timelines |

## Installation

```bash
pip install -r requirements.txt
```

No API keys or internet access are required for local execution after dependencies are installed.

## Demo

Run all demo scenarios:

```bash
python demo.py
```

Run through the unified CLI:

```bash
python run.py demo --scenario wide_sparse
```

Run demo with failure simulation:

```bash
python demo.py --failure-enabled --failure-probability 0.2 --max-retries 1 --fallback-enabled --failure-seed 7
```

Demo outputs:

- `results/execution_trace.json`
- `results/scenario_<name>_<topology>_trace.json`
- `logs/execution_metrics.json`

## Benchmarks

Run the benchmark suite:

```bash
python run_benchmarks.py
```

Or use the unified CLI:

```bash
python run.py benchmark --runs 50 --graph layered --selector cost_aware
```

Train the learned selector:

```bash
python run.py train-selector --runs 100 --output results/learned_selector_model.json
```

Use the learned selector in a benchmark:

```bash
python run.py benchmark --selector learned_adaptive --model results/learned_selector_model.json
```

Run the final comparison with all strategies, including learned adaptive:

```bash
python run.py benchmark --selector all --model results/learned_selector_model.json --runs 10
```

Run with failure simulation:

```bash
python run.py benchmark --runs 10 --graph layered --selector cost_aware --failure-enabled --failure-probability 0.1 --timeout-probability 0.05 --max-retries 1 --fallback-enabled --random-seed 7
```

Benchmark outputs:

- `results/benchmark_results.csv`
- `results/benchmark_summary.csv`
- `results/experiment_config_used.json` when launched through `run.py`

The benchmark compares static topologies, rule-based adaptive selection, cost-aware adaptive selection, and learned adaptive selection when a model file is supplied. It reports latency, cost, weighted graph metrics, quality metrics, robustness metrics, selected topology, objective score, and learned model path.

## Visualizations

Generate benchmark plots:

```bash
python visualize_results.py
```

Build a Gantt-style timeline from an execution trace:

```bash
python visualize_execution_timeline.py results/execution_trace.json
```

Or through the CLI:

```bash
python run.py visualize --trace results/execution_trace.json
```

Timeline images are saved as:

```text
results/timeline_<trace>_<topology>.png
```

Benchmark plots are saved in `results/`, including:

- `latency_comparison.png`
- `topology_efficiency.png`
- `adaptive_vs_static.png`
- `critical_path_impact.png`
- `graph_<graph_type>.png`

## Experiment Configs

Run a JSON-configured experiment:

```bash
python run.py experiment --config configs/experiment_default.json
```

Override config values from the command line:

```bash
python run.py experiment --config configs/experiment_default.json --runs 5 --graph layered --selector cost_aware --output-dir results/experiment_layered
```

The config supports:

- `graph_types`
- `node_count`
- `runs`
- `worker_count`
- `selector_mode`
- `enabled_topologies`
- `output_dir`
- `random_seed`
- `failure_simulation`
- `quality_evaluation`
- `timeline_visualization`

## Quality And Robustness

Quality evaluation is heuristic and deterministic. It does not call an LLM judge. Metrics:

- `completeness_score`
- `consistency_score`
- `synthesis_score`
- `dependency_coverage_score`
- `overall_quality_score`

Robustness metrics:

- `success_rate`
- `failed_node_count`
- `skipped_node_count`
- `retry_count_total`
- `fallback_count`
- `recovery_success_rate`
- `wasted_work_estimate`

If a node fails without fallback, descendants are marked `skipped` and are not executed. This simple policy is used to keep dependency semantics explicit.

## How To Reproduce Experiments

Recommended deterministic smoke run:

```bash
python run.py experiment --config configs/experiment_default.json --runs 1 --node-count 8 --graph layered --selector cost_aware --output-dir results/repro_smoke --random-seed 11
```

Expected output files:

- `results/repro_smoke/benchmark_results.csv`
- `results/repro_smoke/benchmark_summary.csv`
- `results/repro_smoke/experiment_config_used.json`

No fixed numeric superiority claim is assumed. The benchmark is intended to compare strategies under the configured synthetic model.

## Learned Adaptive Selector

`learned_adaptive` is a lightweight nearest-neighbor selector, not a full ML model. It uses graph features extracted from the same DAG metrics used elsewhere in the project:

- `node_count`
- `edge_count`
- `graph_depth`
- `density`
- `parallel_width`
- `max_degree`
- `total_node_cost`
- `average_node_cost`
- `max_node_cost`
- `weighted_critical_path`
- `weighted_parallel_width`

Training data is generated from synthetic benchmark graphs. For each training graph, all static topologies are scored and the best label is saved. The objective is:

```text
objective_score = estimated_latency_with_overhead + 0.05 * execution_cost
```

The model JSON stores feature names, training samples, objective description, and selector version. If `learned_adaptive` is requested without a model file, the CLI reports a clear error instead of silently falling back.

## Testing

Run all tests:

```bash
$env:PYTHONDONTWRITEBYTECODE='1'; python -m unittest discover -s tests
```

Run one test module:

```bash
$env:PYTHONDONTWRITEBYTECODE='1'; python -m unittest tests.test_benchmark_runner
```

See [TESTING.md](TESTING.md) for details. The suite covers DAG operations, metrics, selectors, executors, traces, quality evaluation, failure simulation, benchmark CSV generation, CLI smoke tests, and reproducibility checks.

## Limitations

- Agents are mocks and do not call real LLM APIs.
- Quality evaluation is a heuristic trace-based model, not a semantic evaluator.
- Failure simulation is synthetic and probabilistic.
- The cost-aware selector uses a simple readable cost model, not a learned policy.
- Results should be interpreted as controlled orchestration experiments, not as measurements of a production LLM backend.
