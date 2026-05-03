# Adaptive MAS Coursework

Research prototype for adaptive orchestration of multi-agent LLM systems based on task dependency graphs.

## Project Goal

Investigate the impact of topology selection strategies on latency, execution cost, and quality in multi-agent LLM systems.

## Architecture Overview

This is a lightweight research prototype focusing on orchestration topology, not a generic AI-agent framework.

### Components

- **DAG Abstraction**: Node and edge models for representing task dependencies using NetworkX.
- **Graph Metrics**: Calculations for depth, critical path, density, and parallel width.
- **Topology Selector**: Strategies for sequential, parallel, hierarchical, and hybrid execution.
- **Mock Agents**: Simulated agents (Planner, Researcher, Critic, Synthesizer) for testing.

## Installation

```bash
pip install -r requirements.txt
```

## Usage

```python
from adaptive_mas.dag import DAG, Node, Edge
from adaptive_mas.metrics import GraphMetrics
from adaptive_mas.topology import TopologySelector, TopologyType

# Create DAG
dag = DAG()
dag.add_node(Node("1", "plan"))
dag.add_node(Node("2", "research"))
dag.add_edge(Edge("1", "2"))

# Calculate metrics
depth = GraphMetrics.graph_depth(dag)

# Select topology
topology = TopologySelector.select_topology(dag, TopologyType.PARALLEL)
```

## Stage 1: Architectural Foundation

This implementation covers Stage 1 with:
- Python project structure
- DAG abstraction
- Graph metrics
- Topology selector
- Mock agents
- Basic documentation

## Stage 2: Execution Layer

This prototype now supports:
- Sequential, parallel, hierarchical, and hybrid executors
- Async execution with `asyncio` and layer-based scheduling
- Execution tracing with per-node timestamps and durations
- Execution logging to `results/execution_trace.json` and `logs/execution_metrics.json`
- Timing metrics including total latency, critical path latency, and parallel efficiency
- Demo scenarios for wide sparse, deep dependency, layered, and coordinator graphs

## Demo

Run the demo scenarios:

```bash
python demo.py
```

Generated files:
- `results/execution_trace.json`
- `results/scenario_<name>_<topology>_trace.json`
- `logs/execution_metrics.json`

## Stage 3: Experimental Research Framework

Stage 3 adds a synthetic benchmark framework for comparing static and adaptive orchestration strategies without real LLM APIs.

Run the benchmark suite:

```bash
python run_benchmarks.py
```

Generate plots:

```bash
python visualize_results.py
```

Generated files:
- `results/benchmark_results.csv`
- `results/benchmark_summary.csv`
- `results/latency_comparison.png`
- `results/topology_efficiency.png`
- `results/adaptive_vs_static.png`
- `results/critical_path_impact.png`
- `results/graph_<graph_type>.png`

The benchmark suite includes wide sparse, deep dependency, layered, and centralized coordinator task graphs. Each graph is run 10 times against static sequential, parallel, hierarchical, and hybrid strategies, plus an adaptive strategy selected from DAG metrics.
