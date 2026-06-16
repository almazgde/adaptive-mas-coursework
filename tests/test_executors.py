import unittest
from unittest.mock import patch

from adaptive_mas.dag import DAG, Edge, Node
from adaptive_mas.execution import BaseExecutor, ExecutionManager
from adaptive_mas.topology import TopologyType


class ExecutorTest(unittest.IsolatedAsyncioTestCase):
    async def test_sequential_executor_order(self):
        trace = await self._execute(self._chain(), TopologyType.SEQUENTIAL)

        self.assertEqual(trace.execution_order, ["a", "b", "c"])

    async def test_parallel_executor_respects_dependencies(self):
        dag = self._fork_join()
        trace = await self._execute(dag, TopologyType.PARALLEL)

        positions = {node_id: index for index, node_id in enumerate(trace.execution_order)}
        for edge in dag.edges:
            self.assertLess(positions[edge.from_node], positions[edge.to_node])

    async def test_hybrid_executor_runs_layers_correctly(self):
        trace = await self._execute(self._fork_join(), TopologyType.HYBRID)

        levels = {item["node_id"]: item["level"] for item in trace.node_traces}

        self.assertEqual(levels["root"], 1)
        self.assertEqual(levels["left"], 2)
        self.assertEqual(levels["right"], 2)
        self.assertEqual(levels["join"], 3)

    async def test_hierarchical_executor_adds_aggregate_step(self):
        trace = await self._execute(self._fork_join(), TopologyType.HIERARCHICAL)

        self.assertTrue(any(node_id.startswith("aggregate-") for node_id in trace.execution_order))

    async def test_node_trace_contains_required_fields(self):
        trace = await self._execute(self._chain(), TopologyType.SEQUENTIAL)
        required = {"node_id", "start_time", "end_time", "duration", "status"}

        for item in trace.node_traces:
            self.assertTrue(required.issubset(item))
            self.assertGreaterEqual(item["duration"], 0.0)

    async def test_execution_order_does_not_violate_dependencies(self):
        dag = self._chain()
        trace = await self._execute(dag, TopologyType.SEQUENTIAL)
        positions = {node_id: index for index, node_id in enumerate(trace.execution_order)}

        for edge in dag.edges:
            self.assertLess(positions[edge.from_node], positions[edge.to_node])

    async def _execute(self, dag, topology):
        with patch.object(BaseExecutor, "_persist_trace"), patch.object(BaseExecutor, "_persist_metrics"):
            return await ExecutionManager.create_executor(dag, topology).execute()

    def _chain(self):
        dag = DAG()
        for node_id in ("a", "b", "c"):
            dag.add_node(Node(node_id, f"research {node_id}"))
        dag.add_edge(Edge("a", "b"))
        dag.add_edge(Edge("b", "c"))
        return dag

    def _fork_join(self):
        dag = DAG()
        for node_id in ("root", "left", "right", "join"):
            task = "synthesize join" if node_id == "join" else f"research {node_id}"
            dag.add_node(Node(node_id, task))
        dag.add_edge(Edge("root", "left"))
        dag.add_edge(Edge("root", "right"))
        dag.add_edge(Edge("left", "join"))
        dag.add_edge(Edge("right", "join"))
        return dag


if __name__ == "__main__":
    unittest.main()
