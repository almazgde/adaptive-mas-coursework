import asyncio
import json
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..agents.mock_agents import CriticAgent, PlannerAgent, ResearcherAgent, SynthesizerAgent
from ..dag.dag import DAG
from ..metrics.graph_metrics import GraphMetrics
from ..topology.selector import TopologySelector, TopologyType


RESULTS_DIR = Path("results")
LOGS_DIR = Path("logs")
RESULTS_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)


@dataclass
class ExecutionTrace:
    topology_type: str
    topology_config: Dict[str, Any]
    execution_order: List[str]
    start_time: float
    end_time: float
    duration: float
    node_traces: List[Dict[str, Any]]
    critical_path_duration: float


@dataclass
class ExecutionMetrics:
    total_latency: float
    per_node_latency: Dict[str, float]
    critical_path_latency: float
    parallel_efficiency: float
    topology_type: str
    node_count: int
    execution_order: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ExecutionManager:
    """Factory for executor creation."""

    @staticmethod
    def create_executor(dag: DAG, topology_type: TopologyType):
        if topology_type == TopologyType.SEQUENTIAL:
            return SequentialExecutor(dag, topology_type)
        elif topology_type == TopologyType.PARALLEL:
            return ParallelExecutor(dag, topology_type)
        elif topology_type == TopologyType.HIERARCHICAL:
            return HierarchicalExecutor(dag, topology_type)
        elif topology_type == TopologyType.HYBRID:
            return HybridExecutor(dag, topology_type)
        raise ValueError(f"Unsupported topology type: {topology_type}")


class BaseExecutor:
    def __init__(self, dag: DAG, topology_type: TopologyType):
        self.dag = dag
        self.topology_type = topology_type
        self.topology_config = TopologySelector.select_topology(dag, topology_type)
        self.node_traces: List[Dict[str, Any]] = []
        self.execution_order: List[str] = []

    async def execute(self) -> ExecutionTrace:
        self._ensure_acyclic()
        start_time = time.time()
        await self._run()
        end_time = time.time()
        duration = end_time - start_time
        critical_path_duration = self._compute_critical_path_duration()
        trace = ExecutionTrace(
            topology_type=self.topology_config["type"],
            topology_config=self.topology_config,
            execution_order=self.execution_order,
            start_time=start_time,
            end_time=end_time,
            duration=duration,
            node_traces=self.node_traces,
            critical_path_duration=critical_path_duration,
        )
        self._persist_trace(trace)
        metrics = self._build_metrics(trace)
        self._persist_metrics(metrics)
        return trace

    def _ensure_acyclic(self):
        if not self.dag.is_acyclic():
            raise RuntimeError("DAG must be acyclic for execution.")

    async def _run(self):
        raise NotImplementedError

    async def _execute_node(self, node_id: str, order_index: int) -> Dict[str, Any]:
        node = self.dag.get_node(node_id)
        if node is None:
            node = type("DynamicNode", (), {"task": node_id})()
        agent = self._select_agent(node)
        task_label = getattr(node, "task", node_id)
        start_ts = time.time()
        result = await agent.execute({"node_id": node_id, "task": task_label, "order": order_index})
        end_ts = time.time()
        duration = end_ts - start_ts
        trace = {
            "node_id": node_id,
            "task": task_label,
            "order": order_index,
            "start_time": start_ts,
            "end_time": end_ts,
            "duration": duration,
            "result": result,
        }
        self.node_traces.append(trace)
        self.execution_order.append(node_id)
        return result

    def _select_agent(self, node: Any):
        task_lower = getattr(node, "task", str(node)).lower()
        if "plan" in task_lower:
            return PlannerAgent()
        if "research" in task_lower:
            return ResearcherAgent()
        if "critic" in task_lower or "assess" in task_lower:
            return CriticAgent()
        if "synth" in task_lower or "aggregate" in task_lower:
            return SynthesizerAgent()
        return PlannerAgent()

    def _compute_critical_path_duration(self) -> float:
        durations = {trace["node_id"]: trace["duration"] for trace in self.node_traces}
        if not durations:
            return 0.0
        longest: Dict[str, float] = {}
        for node in self.dag.topological_sort():
            pred_durations = [longest[p] for p in self.dag.get_predecessors(node)]
            longest[node] = max(pred_durations) + durations[node] if pred_durations else durations[node]
        return max(longest.values())

    def _build_metrics(self, trace: ExecutionTrace) -> ExecutionMetrics:
        total_latency = trace.duration
        per_node_latency = {item["node_id"]: item["duration"] for item in trace.node_traces}
        critical_path_latency = trace.critical_path_duration
        parallel_efficiency = (critical_path_latency / total_latency) if total_latency > 0 else 0.0
        if parallel_efficiency > 1.0:
            parallel_efficiency = 1.0
        return ExecutionMetrics(
            total_latency=total_latency,
            per_node_latency=per_node_latency,
            critical_path_latency=critical_path_latency,
            parallel_efficiency=parallel_efficiency,
            topology_type=trace.topology_type,
            node_count=len(per_node_latency),
            execution_order=trace.execution_order,
        )

    def _persist_trace(self, trace: ExecutionTrace):
        path = RESULTS_DIR / "execution_trace.json"
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(asdict(trace), handle, indent=2)

    def _persist_metrics(self, metrics: ExecutionMetrics):
        path = LOGS_DIR / "execution_metrics.json"
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(metrics.to_dict(), handle, indent=2)


class SequentialExecutor(BaseExecutor):
    async def _run(self):
        for index, node_id in enumerate(self.topology_config["execution_order"]):
            await self._execute_node(node_id, index)


class ParallelExecutor(BaseExecutor):
    async def _run(self):
        remaining = set(self.dag.nodes.keys())
        indegree = {node: self.dag.graph.in_degree(node) for node in remaining}
        order_index = 0
        while remaining:
            ready = [node for node in remaining if indegree[node] == 0]
            if not ready:
                raise RuntimeError("DAG contains a cycle or unresolved dependency.")
            tasks = [self._execute_node(node, order_index + idx) for idx, node in enumerate(sorted(ready))]
            await asyncio.gather(*tasks)
            for node in ready:
                remaining.remove(node)
                for successor in self.dag.get_successors(node):
                    indegree[successor] -= 1
            order_index += len(ready)


class HierarchicalExecutor(BaseExecutor):
    async def _run(self):
        coordinator = self.topology_config.get("coordinator")
        if coordinator:
            await self._execute_node(coordinator, 0)
        subtask_groups = self.topology_config.get("subtask_groups", [])
        tasks: List[asyncio.Task] = []
        order_index = 1 if coordinator else 0
        for group in subtask_groups:
            tasks.append(asyncio.create_task(self._execute_subtask_group(group, order_index)))
            order_index += len(group)
        if tasks:
            await asyncio.gather(*tasks)
        if coordinator:
            await self._execute_node(f"aggregate-{coordinator}", order_index)

    async def _execute_subtask_group(self, group: List[str], starting_index: int):
        for offset, node_id in enumerate(group):
            await self._execute_node(node_id, starting_index + offset)

    def _select_agent(self, node: Any):
        if isinstance(node, str) and node.startswith("aggregate-"):
            return SynthesizerAgent()
        return super()._select_agent(node)


class HybridExecutor(BaseExecutor):
    async def _run(self):
        layers = self.topology_config.get("layers", [])
        order_index = 0
        for layer in layers:
            tasks = [self._execute_node(node, order_index + idx) for idx, node in enumerate(sorted(layer))]
            await asyncio.gather(*tasks)
            order_index += len(layer)
