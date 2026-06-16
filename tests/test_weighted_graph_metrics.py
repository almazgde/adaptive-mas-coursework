import unittest

from adaptive_mas.dag import DAG, Edge, Node
from adaptive_mas.metrics import DEFAULT_NODE_COST, GraphMetrics


class WeightedGraphMetricsTest(unittest.TestCase):
    def test_weighted_critical_path_for_chain(self):
        dag = DAG()
        dag.add_node(Node("a", "a", {"cost": 0.2}))
        dag.add_node(Node("b", "b", {"cost": 0.3}))
        dag.add_node(Node("c", "c", {"cost": 0.4}))
        dag.add_edge(Edge("a", "b"))
        dag.add_edge(Edge("b", "c"))

        self.assertAlmostEqual(GraphMetrics.weighted_critical_path_length(dag), 0.9)
        self.assertAlmostEqual(GraphMetrics.total_node_cost(dag), 0.9)
        self.assertAlmostEqual(GraphMetrics.weighted_parallel_width(dag), 0.4)

    def test_weighted_critical_path_for_parallel_branches(self):
        dag = DAG()
        dag.add_node(Node("start", "start", {"cost": 0.1}))
        dag.add_node(Node("fast", "fast", {"cost": 0.2}))
        dag.add_node(Node("slow", "slow", {"cost": 0.7}))
        dag.add_node(Node("end", "end", {"cost": 0.1}))
        dag.add_edge(Edge("start", "fast"))
        dag.add_edge(Edge("start", "slow"))
        dag.add_edge(Edge("fast", "end"))
        dag.add_edge(Edge("slow", "end"))

        self.assertAlmostEqual(GraphMetrics.weighted_critical_path_length(dag), 0.9)
        self.assertAlmostEqual(GraphMetrics.weighted_parallel_width(dag), 0.9)

    def test_default_cost_fallback(self):
        dag = DAG()
        dag.add_node(Node("a", "a"))
        dag.add_node(Node("b", "b", {"cost": 0.3}))
        dag.add_edge(Edge("a", "b"))

        self.assertAlmostEqual(GraphMetrics.node_cost(dag, "a"), DEFAULT_NODE_COST)
        self.assertAlmostEqual(
            GraphMetrics.weighted_critical_path_length(dag),
            DEFAULT_NODE_COST + 0.3,
        )

    def test_empty_dag_returns_safe_values(self):
        dag = DAG()

        self.assertEqual(GraphMetrics.node_costs(dag), {})
        self.assertEqual(GraphMetrics.total_node_cost(dag), 0.0)
        self.assertEqual(GraphMetrics.average_node_cost(dag), 0.0)
        self.assertEqual(GraphMetrics.max_node_cost(dag), 0.0)
        self.assertEqual(GraphMetrics.cost_variance(dag), 0.0)
        self.assertEqual(GraphMetrics.weighted_critical_path_length(dag), 0.0)
        self.assertEqual(GraphMetrics.weighted_parallel_width(dag), 0.0)


if __name__ == "__main__":
    unittest.main()
