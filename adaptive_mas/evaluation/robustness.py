from dataclasses import asdict, dataclass, is_dataclass
from typing import Any, Dict, Optional, Set

from adaptive_mas.dag import DAG


@dataclass
class RobustnessMetrics:
    success_rate: float
    failed_node_count: int
    skipped_node_count: int
    retry_count_total: int
    fallback_count: int
    recovery_success_rate: float
    wasted_work_estimate: float

    def to_dict(self) -> Dict[str, float]:
        return asdict(self)


class RobustnessEvaluator:
    """Computes recovery metrics from execution traces.

    Nodes with ``status=failed`` or ``status=timeout`` are treated as failed.
    Nodes with ``status=skipped`` are descendants blocked by failed upstream
    work. Fallback nodes count as recovered, but still reveal degraded behavior.
    """

    FAILURE_STATUSES = {"failed", "timeout"}

    @staticmethod
    def evaluate(trace: Any, dag: Optional[DAG] = None) -> RobustnessMetrics:
        trace_data = RobustnessEvaluator._trace_to_dict(trace)
        node_traces = trace_data.get("node_traces") or []
        expected_nodes = RobustnessEvaluator._expected_nodes(trace_data, dag)

        expected_node_traces = [
            item for item in node_traces if item.get("node_id") in expected_nodes
        ]
        status_counts = {}
        for item in expected_node_traces:
            status = item.get("status", "success")
            status_counts[status] = status_counts.get(status, 0) + 1

        failed_count = sum(status_counts.get(status, 0) for status in RobustnessEvaluator.FAILURE_STATUSES)
        skipped_count = status_counts.get("skipped", 0)
        fallback_count = status_counts.get("fallback", 0)
        success_count = status_counts.get("success", 0) + fallback_count
        expected_count = len(expected_nodes) if expected_nodes else len(expected_node_traces)
        retry_total = sum(int(item.get("retry_count", 0) or 0) for item in expected_node_traces)

        recovery_events = sum(
            1
            for item in expected_node_traces
            if int(item.get("retry_count", 0) or 0) > 0
            or item.get("used_fallback")
            or item.get("status") in RobustnessEvaluator.FAILURE_STATUSES
        )
        recovered = sum(
            1
            for item in expected_node_traces
            if item.get("status") in {"success", "fallback"}
            and (int(item.get("retry_count", 0) or 0) > 0 or item.get("used_fallback"))
        )
        recovery_success = recovered / recovery_events if recovery_events else 1.0

        return RobustnessMetrics(
            success_rate=RobustnessEvaluator._clamp(success_count / expected_count if expected_count else 1.0),
            failed_node_count=failed_count,
            skipped_node_count=skipped_count,
            retry_count_total=retry_total,
            fallback_count=fallback_count,
            recovery_success_rate=RobustnessEvaluator._clamp(recovery_success),
            wasted_work_estimate=round(RobustnessEvaluator._wasted_work(expected_node_traces), 6),
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
    def _wasted_work(node_traces):
        wasted = 0.0
        for item in node_traces:
            status = item.get("status", "success")
            duration = float(item.get("duration", 0.0) or 0.0)
            retry_count = int(item.get("retry_count", 0) or 0)
            if status in RobustnessEvaluator.FAILURE_STATUSES:
                wasted += duration
            elif retry_count > 0:
                wasted += duration * retry_count / (retry_count + 1)
        return wasted

    @staticmethod
    def _clamp(value: float) -> float:
        return round(max(0.0, min(1.0, value)), 6)
