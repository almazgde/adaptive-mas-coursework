import unittest

from adaptive_mas.dag import DAG, Edge, Node
from adaptive_mas.metrics import DEFAULT_NODE_COST, GraphMetrics


class GraphMetricsTest(unittest.TestCase):
    def test_graph_depth_for_chain(self):
        dag = self._chain([0.1, 0.2, 0.3])

        self.assertEqual(GraphMetrics.graph_depth(dag), 3)

    def test_parallel_width_for_wide_graph(self):
        dag = DAG()
        dag.add_node(Node("root", "root"))
        for index in range(4):
            node_id = f"leaf-{index}"
            dag.add_node(Node(node_id, node_id))
            dag.add_edge(Edge("root", node_id))

        self.assertEqual(GraphMetrics.parallel_width(dag), 4)

    def test_density_for_simple_graph(self):
        dag = DAG()
        for node_id in ("a", "b", "c"):
            dag.add_node(Node(node_id, node_id))
        dag.add_edge(Edge("a", "b"))

        self.assertAlmostEqual(GraphMetrics.graph_density(dag), 1 / 3)

    def test_weighted_critical_path_for_chain(self):
        dag = self._chain([0.2, 0.3, 0.4])

        self.assertAlmostEqual(GraphMetrics.weighted_critical_path_length(dag), 0.9)

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

    def test_default_cost_fallback(self):
        dag = DAG()
        dag.add_node(Node("a", "a"))

        self.assertAlmostEqual(GraphMetrics.node_cost(dag, "a"), DEFAULT_NODE_COST)

    def _chain(self, costs):
        dag = DAG()
        previous = None
        for index, cost in enumerate(costs):
            node_id = f"n{index}"
            dag.add_node(Node(node_id, node_id, {"cost": cost}))
            if previous is not None:
                dag.add_edge(Edge(previous, node_id))
            previous = node_id
        return dag


if __name__ == "__main__":
    unittest.main()
