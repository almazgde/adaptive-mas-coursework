import unittest
from unittest.mock import patch

from adaptive_mas.dag import DAG, Edge, Node
from adaptive_mas.evaluation import RobustnessEvaluator
from adaptive_mas.execution import BaseExecutor, ExecutionManager, FailureSimulationConfig
from adaptive_mas.topology import TopologyType


class FailureRecoveryTest(unittest.IsolatedAsyncioTestCase):
    async def test_failure_disabled_preserves_successful_execution(self):
        trace = await self._execute_chain(FailureSimulationConfig())

        statuses = [item["status"] for item in trace.node_traces]

        self.assertEqual(statuses, ["success", "success"])
        self.assertEqual(sum(item["retry_count"] for item in trace.node_traces), 0)

    async def test_failed_node_gets_failed_status(self):
        trace = await self._execute_chain(
            FailureSimulationConfig(failure_enabled=True, failure_probability=1.0)
        )

        self.assertEqual(trace.node_traces[0]["status"], "failed")
        self.assertIn("Simulated agent exception", trace.node_traces[0]["error_message"])

    async def test_retry_count_increases_on_retry(self):
        trace = await self._execute_chain(
            FailureSimulationConfig(
                failure_enabled=True,
                failure_probability=1.0,
                max_retries=1,
            )
        )

        self.assertEqual(trace.node_traces[0]["retry_count"], 1)

    async def test_fallback_used_after_retries_exhausted(self):
        trace = await self._execute_chain(
            FailureSimulationConfig(
                failure_enabled=True,
                failure_probability=1.0,
                fallback_enabled=True,
            )
        )

        self.assertEqual(trace.node_traces[0]["status"], "fallback")
        self.assertTrue(trace.node_traces[0]["used_fallback"])
        self.assertTrue(trace.node_traces[0]["result"]["fallback"])

    async def test_descendants_of_failed_node_are_skipped(self):
        trace = await self._execute_chain(
            FailureSimulationConfig(failure_enabled=True, failure_probability=1.0)
        )

        statuses = {item["node_id"]: item["status"] for item in trace.node_traces}

        self.assertEqual(statuses["a"], "failed")
        self.assertEqual(statuses["b"], "skipped")

    async def test_robustness_metrics_are_in_expected_ranges(self):
        trace = await self._execute_chain(
            FailureSimulationConfig(
                failure_enabled=True,
                failure_probability=1.0,
                max_retries=1,
                fallback_enabled=True,
            )
        )
        metrics = RobustnessEvaluator.evaluate(trace, self._chain()).to_dict()

        for key in ("success_rate", "recovery_success_rate"):
            self.assertGreaterEqual(metrics[key], 0.0)
            self.assertLessEqual(metrics[key], 1.0)
        self.assertGreaterEqual(metrics["retry_count_total"], 0)
        self.assertGreaterEqual(metrics["fallback_count"], 0)
        self.assertGreaterEqual(metrics["wasted_work_estimate"], 0.0)

    async def _execute_chain(self, config):
        with patch.object(BaseExecutor, "_persist_trace"), patch.object(BaseExecutor, "_persist_metrics"):
            return await ExecutionManager.create_executor(
                self._chain(),
                TopologyType.SEQUENTIAL,
                failure_config=config,
            ).execute()

    def _chain(self):
        dag = DAG()
        dag.add_node(Node("a", "plan a"))
        dag.add_node(Node("b", "research b"))
        dag.add_edge(Edge("a", "b"))
        return dag


if __name__ == "__main__":
    unittest.main()
