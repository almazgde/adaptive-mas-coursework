import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

from adaptive_mas.dag import DAG
from adaptive_mas.metrics import GraphMetrics
from .selector import TopologySelector, TopologyType


SELECTOR_VERSION = "learned-nearest-neighbor-v1"
OBJECTIVE_DESCRIPTION = "objective_score = estimated_latency_with_overhead + 0.05 * execution_cost"


FEATURE_NAMES = [
    "node_count",
    "edge_count",
    "graph_depth",
    "density",
    "parallel_width",
    "max_degree",
    "total_node_cost",
    "average_node_cost",
    "max_node_cost",
    "weighted_critical_path",
    "weighted_parallel_width",
]


@dataclass
class LearnedSelectorPrediction:
    topology: TopologyType
    objective_score: float
    nearest_distance: float


class LearnedTopologySelector:
    """Dependency-free nearest-neighbor learned topology selector.

    The model is a lightweight scientific baseline rather than a full ML stack:
    each training sample stores graph features and the best static topology under
    the documented objective. Prediction normalizes features by training-set
    ranges and returns the label of the nearest sample.
    """

    def __init__(self, samples: List[Dict], feature_names: Optional[List[str]] = None):
        if not samples:
            raise ValueError("Learned selector model has no training samples.")
        self.samples = samples
        self.feature_names = feature_names or list(FEATURE_NAMES)
        self._ranges = self._feature_ranges()

    @staticmethod
    def extract_features(dag: DAG) -> Dict[str, float]:
        return {
            "node_count": float(len(dag.nodes)),
            "edge_count": float(len(dag.edges)),
            "graph_depth": float(GraphMetrics.graph_depth(dag)),
            "density": float(GraphMetrics.graph_density(dag)),
            "parallel_width": float(GraphMetrics.parallel_width(dag)),
            "max_degree": float(GraphMetrics.max_degree(dag)),
            "total_node_cost": float(GraphMetrics.total_node_cost(dag)),
            "average_node_cost": float(GraphMetrics.average_node_cost(dag)),
            "max_node_cost": float(GraphMetrics.max_node_cost(dag)),
            "weighted_critical_path": float(GraphMetrics.weighted_critical_path_length(dag)),
            "weighted_parallel_width": float(GraphMetrics.weighted_parallel_width(dag)),
        }

    @classmethod
    def train(
        cls,
        graph_types: List[str],
        runs: int,
        node_count: int,
    ) -> "LearnedTopologySelector":
        from experiments.benchmarks.synthetic_graphs import SyntheticGraphFactory

        samples = []
        for graph_type in graph_types:
            for seed in range(1, runs + 1):
                dag = SyntheticGraphFactory.create(graph_type, node_count=node_count, seed=seed)
                best_topology, best_score = cls._best_static_topology(dag)
                samples.append(
                    {
                        "graph_type": graph_type,
                        "seed": seed,
                        "features": cls.extract_features(dag),
                        "label": best_topology.value,
                        "objective_score": round(best_score, 6),
                    }
                )
        return cls(samples)

    @classmethod
    def load(cls, path: Path) -> "LearnedTopologySelector":
        if not path.exists():
            raise FileNotFoundError(f"Learned selector model not found: {path}")
        with open(path, encoding="utf-8") as handle:
            payload = json.load(handle)
        samples = payload.get("training_samples") or payload.get("prototypes") or []
        feature_names = payload.get("feature_names") or FEATURE_NAMES
        return cls(samples=samples, feature_names=feature_names)

    def save(self, path: Path) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "selector_version": SELECTOR_VERSION,
            "feature_names": self.feature_names,
            "objective_score_description": OBJECTIVE_DESCRIPTION,
            "training_samples": self.samples,
        }
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2)
        return path

    def predict(self, dag: DAG) -> LearnedSelectorPrediction:
        features = self.extract_features(dag)
        nearest = min(
            self.samples,
            key=lambda sample: self._distance(features, sample["features"]),
        )
        return LearnedSelectorPrediction(
            topology=TopologyType(nearest["label"]),
            objective_score=float(nearest["objective_score"]),
            nearest_distance=round(self._distance(features, nearest["features"]), 6),
        )

    def _distance(self, left: Dict[str, float], right: Dict[str, float]) -> float:
        total = 0.0
        for name in self.feature_names:
            low, high = self._ranges[name]
            scale = high - low
            if math.isclose(scale, 0.0):
                scale = 1.0
            total += ((float(left[name]) - float(right[name])) / scale) ** 2
        return math.sqrt(total)

    def _feature_ranges(self) -> Dict[str, tuple]:
        ranges = {}
        for name in self.feature_names:
            values = [float(sample["features"][name]) for sample in self.samples]
            ranges[name] = (min(values), max(values))
        return ranges

    @staticmethod
    def _best_static_topology(dag: DAG) -> tuple:
        estimates = TopologySelector.estimate_topology_costs(dag)
        best_topology = min(
            estimates,
            key=lambda topology: LearnedTopologySelector.objective_score(estimates[topology], dag),
        )
        return best_topology, LearnedTopologySelector.objective_score(estimates[best_topology], dag)

    @staticmethod
    def objective_score(estimate: Dict[str, float], dag: DAG) -> float:
        estimated_latency = float(estimate["expected_latency"]) + float(estimate["coordination_overhead"])
        return estimated_latency + 0.05 * GraphMetrics.total_node_cost(dag)
