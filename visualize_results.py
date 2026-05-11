import csv
from collections import defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import networkx as nx

from experiments.benchmarks.synthetic_graphs import SyntheticGraphFactory


RESULTS_DIR = Path("results")
CSV_PATH = RESULTS_DIR / "benchmark_results.csv"


def load_rows():
    with open(CSV_PATH, newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def grouped_mean(rows, key_fields, value_field):
    grouped = defaultdict(list)
    for row in rows:
        key = tuple(row[field] for field in key_fields)
        grouped[key].append(float(row[value_field]))
    return {key: sum(values) / len(values) for key, values in grouped.items()}


def plot_latency_comparison(rows):
    data = grouped_mean(rows, ["graph_type", "requested_topology"], "execution_latency")
    graph_types = sorted({row["graph_type"] for row in rows})
    preferred_order = [
        "sequential",
        "parallel",
        "hierarchical",
        "hybrid",
        "rule_based_adaptive",
        "cost_aware_adaptive",
    ]
    seen = {row["requested_topology"] for row in rows}
    topologies = [topology for topology in preferred_order if topology in seen]
    x = range(len(graph_types))
    width = 0.75 / max(len(topologies), 1)

    plt.figure(figsize=(12, 6))
    for offset, topology in enumerate(topologies):
        values = [data.get((graph_type, topology), 0.0) for graph_type in graph_types]
        center = (len(topologies) - 1) / 2
        positions = [index + (offset - center) * width for index in x]
        plt.bar(positions, values, width=width, label=topology)
    plt.xticks(list(x), graph_types, rotation=15)
    plt.ylabel("Average execution latency")
    plt.title("Latency comparison by topology")
    plt.legend()
    plt.tight_layout()
    plt.savefig(RESULTS_DIR / "latency_comparison.png", dpi=160)
    plt.close()


def plot_topology_efficiency(rows):
    data = grouped_mean(rows, ["requested_topology"], "parallel_efficiency")
    keys = sorted(data.keys())
    labels = [key[0] for key in keys]
    values = [data[key] for key in keys]
    plt.figure(figsize=(9, 5))
    colors = ["#4c78a8", "#f58518", "#54a24b", "#e45756", "#72b7b2", "#b279a2"]
    plt.bar(labels, values, color=colors[: len(labels)])
    plt.ylabel("Average parallel efficiency")
    plt.title("Topology efficiency")
    plt.ylim(0, 1.05)
    plt.tight_layout()
    plt.savefig(RESULTS_DIR / "topology_efficiency.png", dpi=160)
    plt.close()


def plot_adaptive_vs_static(rows):
    grouped = defaultdict(list)
    for row in rows:
        group = "adaptive" if row["strategy_group"] == "adaptive" else "static"
        grouped[(row["graph_type"], group)].append(float(row["execution_latency"]))

    graph_types = sorted({row["graph_type"] for row in rows})
    x = range(len(graph_types))
    plt.figure(figsize=(10, 5))
    for offset, group in enumerate(["static", "adaptive"]):
        values = [
            sum(grouped[(graph_type, group)]) / len(grouped[(graph_type, group)])
            for graph_type in graph_types
        ]
        positions = [index + (offset - 0.5) * 0.35 for index in x]
        plt.bar(positions, values, width=0.35, label=group)
    plt.xticks(list(x), graph_types, rotation=15)
    plt.ylabel("Average execution latency")
    plt.title("Adaptive vs static orchestration")
    plt.legend()
    plt.tight_layout()
    plt.savefig(RESULTS_DIR / "adaptive_vs_static.png", dpi=160)
    plt.close()


def plot_critical_path_impact(rows):
    plt.figure(figsize=(8, 5))
    for topology in sorted({row["requested_topology"] for row in rows}):
        subset = [row for row in rows if row["requested_topology"] == topology]
        x = [float(row["critical_path_latency"]) for row in subset]
        y = [float(row["execution_latency"]) for row in subset]
        plt.scatter(x, y, label=topology, alpha=0.7)
    plt.xlabel("Critical path latency")
    plt.ylabel("Execution latency")
    plt.title("Critical path impact")
    plt.legend()
    plt.tight_layout()
    plt.savefig(RESULTS_DIR / "critical_path_impact.png", dpi=160)
    plt.close()


def plot_synthetic_graphs():
    graph_types = [
        "wide_sparse",
        "deep_dependency",
        "layered",
        "centralized_coordinator",
    ]
    for graph_type in graph_types:
        dag = SyntheticGraphFactory.create(graph_type, node_count=16, seed=1)
        plt.figure(figsize=(8, 5))
        pos = nx.multipartite_layout(dag.graph, subset_key=_levels_for_layout(dag))
        nx.draw_networkx(
            dag.graph,
            pos=pos,
            node_size=900,
            node_color="#d9ecf2",
            edge_color="#5d6970",
            font_size=8,
            arrows=True,
        )
        plt.title(f"Synthetic graph: {graph_type}")
        plt.axis("off")
        plt.tight_layout()
        plt.savefig(RESULTS_DIR / f"graph_{graph_type}.png", dpi=160)
        plt.close()


def _levels_for_layout(dag):
    levels = {}
    for node in nx.topological_sort(dag.graph):
        predecessors = list(dag.graph.predecessors(node))
        levels[node] = max([levels[pred] for pred in predecessors], default=0) + 1
    subsets = defaultdict(list)
    for node, level in levels.items():
        subsets[level].append(node)
    return dict(subsets)


def main():
    RESULTS_DIR.mkdir(exist_ok=True)
    rows = load_rows()
    plot_latency_comparison(rows)
    plot_topology_efficiency(rows)
    plot_adaptive_vs_static(rows)
    plot_critical_path_impact(rows)
    plot_synthetic_graphs()
    print("Generated benchmark visualizations in results/")


if __name__ == "__main__":
    main()
