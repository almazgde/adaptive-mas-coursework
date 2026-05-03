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

Future stages will include experiments, logging, and real LLM integration.