import unittest

from adaptive_mas.dag import DAG, Edge, Node
from adaptive_mas.evaluation import QualityEvaluator


class QualityEvaluatorTest(unittest.TestCase):
    def test_complete_execution_gets_high_completeness(self):
        dag = self._dag_with_synthesis()
        trace = self._trace(["plan", "research", "synthesize"])

        metrics = QualityEvaluator.evaluate(trace, dag)

        self.assertEqual(metrics.completeness_score, 1.0)
        self.assertEqual(metrics.dependency_coverage_score, 1.0)

    def test_missing_node_lowers_completeness(self):
        dag = self._dag_with_synthesis()
        trace = self._trace(["plan", "research"])

        metrics = QualityEvaluator.evaluate(trace, dag)

        self.assertLess(metrics.completeness_score, 1.0)

    def test_missing_synthesis_lowers_synthesis_score(self):
        dag = DAG()
        dag.add_node(Node("plan", "plan task"))
        dag.add_node(Node("research", "research task"))
        dag.add_edge(Edge("plan", "research"))
        trace = self._trace(["plan", "research"])

        metrics = QualityEvaluator.evaluate(trace, dag)

        self.assertEqual(metrics.synthesis_score, 0.0)

    def test_scores_stay_in_unit_range(self):
        dag = self._dag_with_synthesis()
        trace = self._trace(["research", "plan"], empty_result=True)

        metrics = QualityEvaluator.evaluate(trace, dag).to_dict()

        for score in metrics.values():
            self.assertGreaterEqual(score, 0.0)
            self.assertLessEqual(score, 1.0)

    def test_failed_and_skipped_nodes_lower_scores(self):
        dag = self._dag_with_synthesis()
        trace = self._trace(["plan", "research", "synthesize"])
        trace["node_traces"][1]["status"] = "failed"
        trace["node_traces"][1]["result"] = {}
        trace["node_traces"][2]["status"] = "skipped"
        trace["node_traces"][2]["result"] = {}

        metrics = QualityEvaluator.evaluate(trace, dag)

        self.assertLess(metrics.completeness_score, 1.0)
        self.assertLess(metrics.consistency_score, 1.0)

    def _dag_with_synthesis(self):
        dag = DAG()
        dag.add_node(Node("plan", "plan task"))
        dag.add_node(Node("research", "research task"))
        dag.add_node(Node("synthesize", "synthesize final answer"))
        dag.add_edge(Edge("plan", "research"))
        dag.add_edge(Edge("research", "synthesize"))
        return dag

    def _trace(self, node_ids, empty_result=False):
        node_traces = []
        for order, node_id in enumerate(node_ids):
            agent = "SynthesizerAgent" if "synth" in node_id else "ResearcherAgent"
            node_traces.append(
                {
                    "node_id": node_id,
                    "task": f"{node_id} task",
                    "agent": agent,
                    "order": order,
                    "start_time": float(order),
                    "end_time": float(order + 1),
                    "duration": 1.0,
                    "result": {} if empty_result else {"agent": agent, "status": "ok"},
                }
            )
        return {
            "topology_type": "sequential",
            "duration": float(len(node_ids)),
            "node_traces": node_traces,
        }


if __name__ == "__main__":
    unittest.main()
