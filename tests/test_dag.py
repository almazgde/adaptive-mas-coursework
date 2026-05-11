import unittest

from adaptive_mas.dag import DAG, Edge, Node


class DAGTest(unittest.TestCase):
    def test_add_nodes(self):
        dag = DAG()
        dag.add_node(Node("a", "task a"))
        dag.add_node(Node("b", "task b"))

        self.assertIn("a", dag.nodes)
        self.assertIn("b", dag.graph.nodes)

    def test_add_edges(self):
        dag = DAG()
        dag.add_node(Node("a", "task a"))
        dag.add_node(Node("b", "task b"))
        dag.add_edge(Edge("a", "b"))

        self.assertEqual(len(dag.edges), 1)
        self.assertIn("b", dag.get_successors("a"))
        self.assertIn("a", dag.get_predecessors("b"))

    def test_topological_sort_respects_dependencies(self):
        dag = DAG()
        for node_id in ("a", "b", "c"):
            dag.add_node(Node(node_id, node_id))
        dag.add_edge(Edge("a", "b"))
        dag.add_edge(Edge("b", "c"))

        order = dag.topological_sort()

        self.assertLess(order.index("a"), order.index("b"))
        self.assertLess(order.index("b"), order.index("c"))

    def test_acyclic_graph(self):
        dag = DAG()
        dag.add_node(Node("a", "a"))
        dag.add_node(Node("b", "b"))
        dag.add_edge(Edge("a", "b"))

        self.assertTrue(dag.is_acyclic())

    def test_cycle_detection(self):
        dag = DAG()
        dag.add_node(Node("a", "a"))
        dag.add_node(Node("b", "b"))
        dag.add_edge(Edge("a", "b"))
        dag.add_edge(Edge("b", "a"))

        self.assertFalse(dag.is_acyclic())


if __name__ == "__main__":
    unittest.main()
