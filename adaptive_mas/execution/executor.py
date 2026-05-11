import asyncio
import json
import random
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
class FailureSimulationConfig:
    """Configuration for lightweight failure simulation.

    Failure simulation is disabled by default, preserving the original executor
    behavior. When enabled, each node attempt can raise an exception, timeout,
    or return an empty result according to the configured probabilities.
    """

    failure_enabled: bool = False
    failure_probability: float = 0.0
    timeout_probability: float = 0.0
    empty_result_probability: float = 0.0
    max_retries: int = 0
    timeout_seconds: float = 1.0
    fallback_enabled: bool = False
    random_seed: Optional[int] = None


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
    def create_executor(
        dag: DAG,
        topology_type: TopologyType,
        failure_config: Optional[FailureSimulationConfig] = None,
    ):
        if topology_type == TopologyType.SEQUENTIAL:
            return SequentialExecutor(dag, topology_type, failure_config)
        elif topology_type == TopologyType.PARALLEL:
            return ParallelExecutor(dag, topology_type, failure_config)
        elif topology_type == TopologyType.HIERARCHICAL:
            return HierarchicalExecutor(dag, topology_type, failure_config)
        elif topology_type == TopologyType.HYBRID:
            return HybridExecutor(dag, topology_type, failure_config)
        raise ValueError(f"Unsupported topology type: {topology_type}")


class BaseExecutor:
    def __init__(
        self,
        dag: DAG,
        topology_type: TopologyType,
        failure_config: Optional[FailureSimulationConfig] = None,
    ):
        self.dag = dag
        self.topology_type = topology_type
        self.topology_config = TopologySelector.select_topology(dag, topology_type)
        self.node_traces: List[Dict[str, Any]] = []
        self.execution_order: List[str] = []
        self.node_levels = self._build_node_level_map()
        self.failure_config = failure_config or FailureSimulationConfig()
        self.random = random.Random(self.failure_config.random_seed)
        self.failed_nodes = set()
        self.skipped_nodes = set()

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
        if self._has_blocked_predecessor(node_id):
            self._skip_node(node_id, order_index, "predecessor_failed")
            return {"status": "skipped", "reason": "predecessor_failed"}

        node = self.dag.get_node(node_id)
        if node is None:
            node = type("DynamicNode", (), {"task": node_id})()
        agent = self._select_agent(node)
        task_label = getattr(node, "task", node_id)
        start_ts = time.time()
        result: Dict[str, Any] = {}
        status = "success"
        retry_count = 0
        error_message = None
        used_fallback = False

        for attempt in range(self.failure_config.max_retries + 1):
            try:
                result = await self._attempt_agent_execution(
                    agent,
                    {"node_id": node_id, "task": task_label, "order": order_index, "attempt": attempt},
                )
                status = "success"
                error_message = None
                break
            except asyncio.TimeoutError as exc:
                retry_count = attempt + 1 if attempt < self.failure_config.max_retries else attempt
                status = "timeout"
                error_message = str(exc) or f"Timed out after {self.failure_config.timeout_seconds}s"
            except Exception as exc:
                retry_count = attempt + 1 if attempt < self.failure_config.max_retries else attempt
                status = "failed"
                error_message = str(exc)
        else:
            result = {}

        if status in {"failed", "timeout"} and not result:
            if self.failure_config.fallback_enabled:
                status = "fallback"
                used_fallback = True
                result = {
                    "fallback": True,
                    "node_id": node_id,
                    "agent": agent.__class__.__name__,
                    "reason": error_message,
                }
            else:
                self.failed_nodes.add(node_id)

        end_ts = time.time()
        duration = end_ts - start_ts
        trace = {
            "node_id": node_id,
            "task": task_label,
            "agent": agent.__class__.__name__,
            "order": order_index,
            "status": status,
            "retry_count": retry_count,
            "error_message": error_message,
            "used_fallback": used_fallback,
            "start_time": start_ts,
            "end_time": end_ts,
            "duration": duration,
            "topology": self.topology_config["type"],
            "level": self.node_levels.get(node_id),
            "layer": self.node_levels.get(node_id),
            "result": result,
        }
        self.node_traces.append(trace)
        if status != "failed":
            self.execution_order.append(node_id)
        return result

    async def _attempt_agent_execution(self, agent: Any, payload: Dict[str, Any]) -> Dict[str, Any]:
        if not self.failure_config.failure_enabled:
            return await agent.execute(payload)

        roll = self.random.random()
        if roll < self.failure_config.failure_probability:
            raise RuntimeError("Simulated agent exception")

        roll = self.random.random()
        if roll < self.failure_config.timeout_probability:
            await asyncio.wait_for(
                asyncio.sleep(self.failure_config.timeout_seconds + 0.01),
                timeout=self.failure_config.timeout_seconds,
            )

        roll = self.random.random()
        if roll < self.failure_config.empty_result_probability:
            return {}

        return await asyncio.wait_for(agent.execute(payload), timeout=self.failure_config.timeout_seconds)

    def _has_blocked_predecessor(self, node_id: str) -> bool:
        if node_id not in self.dag.graph:
            return False
        return any(
            predecessor in self.failed_nodes or predecessor in self.skipped_nodes
            for predecessor in self.dag.get_predecessors(node_id)
        )

    def _skip_node(self, node_id: str, order_index: int, reason: str):
        if node_id in self.skipped_nodes:
            return
        now = time.time()
        node = self.dag.get_node(node_id)
        task_label = getattr(node, "task", node_id) if node is not None else node_id
        trace = {
            "node_id": node_id,
            "task": task_label,
            "agent": None,
            "order": order_index,
            "status": "skipped",
            "retry_count": 0,
            "error_message": reason,
            "used_fallback": False,
            "start_time": now,
            "end_time": now,
            "duration": 0.0,
            "topology": self.topology_config["type"],
            "level": self.node_levels.get(node_id),
            "layer": self.node_levels.get(node_id),
            "result": {},
        }
        self.skipped_nodes.add(node_id)
        self.node_traces.append(trace)

    def _skip_blocked_remaining(self, remaining: set, order_index: int) -> int:
        skipped_count = 0
        changed = True
        while changed:
            changed = False
            for node_id in sorted(list(remaining)):
                if self._has_blocked_predecessor(node_id):
                    remaining.remove(node_id)
                    self._skip_node(node_id, order_index + skipped_count, "predecessor_failed")
                    skipped_count += 1
                    changed = True
        return skipped_count

    def _build_node_level_map(self) -> Dict[str, int]:
        if "levels" in self.topology_config:
            return dict(self.topology_config["levels"])
        if "layers" in self.topology_config:
            return {
                node_id: index + 1
                for index, layer in enumerate(self.topology_config["layers"])
                for node_id in layer
            }
        return {}

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
        durations = {
            trace["node_id"]: trace["duration"]
            for trace in self.node_traces
            if trace.get("status") not in {"failed", "skipped"}
        }
        if not durations:
            return 0.0
        longest: Dict[str, float] = {}
        for node in self.dag.topological_sort():
            if node not in durations:
                continue
            pred_durations = [longest[p] for p in self.dag.get_predecessors(node) if p in longest]
            longest[node] = max(pred_durations) + durations[node] if pred_durations else durations[node]
        return max(longest.values(), default=0.0)

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
            order_index += self._skip_blocked_remaining(remaining, order_index)


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
            if coordinator in self.failed_nodes or coordinator in self.skipped_nodes:
                self._skip_node(f"aggregate-{coordinator}", order_index, "coordinator_failed")
            else:
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
