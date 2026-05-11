import unittest

from adaptive_mas.topology import TopologySelector, TopologyType
from experiments.benchmarks.synthetic_graphs import SyntheticGraphFactory


class TopologySelectorTest(unittest.TestCase):
    def test_rule_based_adaptive_returns_valid_topology(self):
        dag = SyntheticGraphFactory.layered(node_count=16, seed=1)

        selected = TopologySelector.select_rule_based_adaptive_topology_type(dag)

        self.assertIsInstance(selected, TopologyType)

    def test_cost_aware_adaptive_returns_valid_topology(self):
        dag = SyntheticGraphFactory.layered(node_count=16, seed=1)

        selected = TopologySelector.select_cost_aware_adaptive_topology_type(dag)

        self.assertIsInstance(selected, TopologyType)

    def test_wide_sparse_prefers_parallel(self):
        dag = SyntheticGraphFactory.wide_sparse(node_count=32, seed=3)

        selected = TopologySelector.select_cost_aware_adaptive_topology_type(dag)

        self.assertEqual(selected, TopologyType.PARALLEL)

    def test_deep_dependency_prefers_sequential(self):
        dag = SyntheticGraphFactory.deep_dependency(node_count=32, seed=3)

        selected = TopologySelector.select_rule_based_adaptive_topology_type(dag)

        self.assertEqual(selected, TopologyType.SEQUENTIAL)


if __name__ == "__main__":
    unittest.main()
