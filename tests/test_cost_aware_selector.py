import unittest

from adaptive_mas.dag import DAG, Edge, Node
from adaptive_mas.topology import TopologySelector, TopologyType
from experiments.benchmarks.synthetic_graphs import SyntheticGraphFactory


class CostAwareSelectorTest(unittest.TestCase):
    def test_estimates_all_supported_topologies(self):
        dag = SyntheticGraphFactory.layered(node_count=16, seed=1)

        estimates = TopologySelector.estimate_topology_costs(dag)

        self.assertEqual(set(estimates), set(TopologyType))
        for estimate in estimates.values():
            self.assertIn("expected_latency", estimate)
            self.assertIn("coordination_overhead", estimate)
            self.assertIn("critical_path_impact", estimate)
            self.assertIn("parallel_efficiency", estimate)
            self.assertIn("score", estimate)

    def test_cost_aware_returns_valid_topology_type(self):
        dag = SyntheticGraphFactory.layered(node_count=16, seed=2)

        selected = TopologySelector.select_cost_aware_adaptive_topology_type(dag)

        self.assertIsInstance(selected, TopologyType)

    def test_cost_aware_prefers_parallel_for_wide_graph(self):
        dag = SyntheticGraphFactory.wide_sparse(node_count=32, seed=3)

        selected = TopologySelector.select_cost_aware_adaptive_topology_type(dag)

        self.assertEqual(selected, TopologyType.PARALLEL)

    def test_cost_aware_prefers_sequential_for_deep_dependency_graph(self):
        dag = DAG()
        for index in range(12):
            dag.add_node(Node(f"n{index}", f"task {index}", {"cost": 0.1}))
            if index > 0:
                dag.add_edge(Edge(f"n{index - 1}", f"n{index}"))

        selected = TopologySelector.select_cost_aware_adaptive_topology_type(dag)

        self.assertEqual(selected, TopologyType.SEQUENTIAL)


if __name__ == "__main__":
    unittest.main()
