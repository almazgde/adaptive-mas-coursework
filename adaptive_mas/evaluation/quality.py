from dataclasses import asdict, dataclass, is_dataclass
from typing import Any, Dict, Iterable, List, Optional, Set

from adaptive_mas.dag import DAG


@dataclass
class QualityMetrics:
    completeness_score: float
    consistency_score: float
    synthesis_score: float
    dependency_coverage_score: float
    overall_quality_score: float

    def to_dict(self) -> Dict[str, float]:
        return asdict(self)


class QualityEvaluator:
    """Deterministic heuristic quality evaluator for mock DAG executions.

    This is not an LLM judge. It estimates result quality from execution trace
    structure: whether expected DAG nodes ran, whether dependencies were
    respected, whether node outputs are present, and whether the run contains a
    synthesis/aggregate step. The scores are lightweight proxies that make the
    benchmark compare quality alongside latency and cost without external APIs.
    """

    @staticmethod
    def evaluate(trace: Any, dag: Optional[DAG] = None) -> QualityMetrics:
        trace_data = QualityEvaluator._trace_to_dict(trace)
        node_traces = trace_data.get("node_traces") or []
        expected_nodes = QualityEvaluator._expected_nodes(trace_data, dag)
        executed_nodes = {
            item.get("node_id")
            for item in node_traces
            if item.get("node_id") in expected_nodes
            and item.get("status", "success") not in {"failed", "timeout", "skipped"}
        }

        completeness = QualityEvaluator._completeness_score(expected_nodes, executed_nodes)
        consistency = QualityEvaluator._consistency_score(node_traces)
        synthesis = QualityEvaluator._synthesis_score(node_traces)
        dependency_coverage = QualityEvaluator._dependency_coverage_score(node_traces, dag)

        overall = (
            completeness * 0.30
            + consistency * 0.25
            + synthesis * 0.20
            + dependency_coverage * 0.25
        )
        return QualityMetrics(
            completeness_score=QualityEvaluator._clamp(completeness),
            consistency_score=QualityEvaluator._clamp(consistency),
            synthesis_score=QualityEvaluator._clamp(synthesis),
            dependency_coverage_score=QualityEvaluator._clamp(dependency_coverage),
            overall_quality_score=QualityEvaluator._clamp(overall),
        )

    @staticmethod
    def _trace_to_dict(trace: Any) -> Dict[str, Any]:
        if trace is None:
            return {}
        if isinstance(trace, dict):
            return trace
        if is_dataclass(trace):
            return asdict(trace)
        return dict(getattr(trace, "__dict__", {}))

    @staticmethod
    def _expected_nodes(trace: Dict[str, Any], dag: Optional[DAG]) -> Set[str]:
        if dag is not None:
            return set(dag.nodes.keys())
        topology_order = trace.get("topology_config", {}).get("execution_order")
        if topology_order:
            return set(topology_order)
        return {item.get("node_id") for item in trace.get("node_traces", []) if item.get("node_id")}

    @staticmethod
    def _completeness_score(expected_nodes: Set[str], executed_nodes: Set[str]) -> float:
        if not expected_nodes:
            return 1.0
        return len(executed_nodes) / len(expected_nodes)

    @staticmethod
    def _consistency_score(node_traces: List[Dict[str, Any]]) -> float:
        if not node_traces:
            return 0.0
        valid = 0
        for item in node_traces:
            result = item.get("result")
            status = item.get("status", "success")
            failed = status in {"failed", "timeout", "skipped"} or item.get("error") or item.get("failed")
            empty_result = result in (None, "", {}, [])
            if not failed and not empty_result:
                valid += 0.75 if status == "fallback" or item.get("used_fallback") else 1.0
        return valid / len(node_traces)

    @staticmethod
    def _synthesis_score(node_traces: List[Dict[str, Any]]) -> float:
        if not node_traces:
            return 0.0
        return 1.0 if any(QualityEvaluator._looks_like_synthesis(item) for item in node_traces) else 0.0

    @staticmethod
    def _dependency_coverage_score(node_traces: List[Dict[str, Any]], dag: Optional[DAG]) -> float:
        if dag is None or not dag.edges:
            return 1.0 if node_traces else 0.0

        positions = QualityEvaluator._execution_positions(node_traces)
        covered = 0
        total = 0
        for edge in dag.edges:
            total += 1
            if edge.from_node in positions and edge.to_node in positions:
                if positions[edge.from_node] <= positions[edge.to_node]:
                    covered += 1
        return covered / total if total else 1.0

    @staticmethod
    def _execution_positions(node_traces: Iterable[Dict[str, Any]]) -> Dict[str, float]:
        positions = {}
        for fallback_order, item in enumerate(node_traces):
            node_id = item.get("node_id")
            if not node_id:
                continue
            if "start_time" in item:
                positions[node_id] = float(item["start_time"])
            else:
                positions[node_id] = float(item.get("order", fallback_order))
        return positions

    @staticmethod
    def _looks_like_synthesis(node_trace: Dict[str, Any]) -> bool:
        text_parts = [
            node_trace.get("node_id", ""),
            node_trace.get("task", ""),
            node_trace.get("agent", ""),
        ]
        result = node_trace.get("result")
        if isinstance(result, dict):
            text_parts.extend(str(key) for key in result.keys())
            text_parts.extend(str(value) for value in result.values())
        haystack = " ".join(str(part).lower() for part in text_parts)
        return "synth" in haystack or "aggregate" in haystack

    @staticmethod
    def _clamp(value: float) -> float:
        return round(max(0.0, min(1.0, value)), 6)
