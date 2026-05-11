import random
from typing import Callable, Dict

from adaptive_mas.dag import DAG, Edge, Node


class SyntheticGraphFactory:
    """Builds synthetic task graphs for orchestration experiments."""

    TASK_BUILDERS: Dict[str, Callable[[int, int], DAG]] = {}

    @staticmethod
    def create(graph_type: str, node_count: int = 16, seed: int = 0) -> DAG:
        builders = {
            "wide_sparse": SyntheticGraphFactory.wide_sparse,
            "deep_dependency": SyntheticGraphFactory.deep_dependency,
            "layered": SyntheticGraphFactory.layered,
            "centralized_coordinator": SyntheticGraphFactory.centralized_coordinator,
        }
        if graph_type not in builders:
            raise ValueError(f"Unknown graph type: {graph_type}")
        return builders[graph_type](node_count, seed)

    @staticmethod
    def wide_sparse(node_count: int = 32, seed: int = 0) -> DAG:
        """Low dependency density with high parallelism but more complex structure."""
        rng = random.Random(seed)
        dag = DAG()
        for index in range(node_count):
            dag.add_node(SyntheticGraphFactory._node(index, "research", rng))
        # Основная цепь с большим шагом
        for index in range(0, max(0, node_count - 5), 5):
            if index + 5 < node_count:
                dag.add_edge(Edge(f"n{index}", f"n{index + 5}"))
        # Дополнительные боковые зависимости для большей сложности
        for index in range(0, node_count - 2, 6):
            if index + 2 < node_count:
                dag.add_edge(Edge(f"n{index}", f"n{index + 2}"))
        return dag

    @staticmethod
    def deep_dependency(node_count: int = 32, seed: int = 0) -> DAG:
        """Long critical path with mostly sequential dependencies + some branching."""
        rng = random.Random(seed)
        dag = DAG()
        for index in range(node_count):
            task = "plan" if index == 0 else "research"
            dag.add_node(SyntheticGraphFactory._node(index, task, rng))
            if index > 0:
                dag.add_edge(Edge(f"n{index - 1}", f"n{index}"))
        # Добавляем некоторые параллельные ветви для сложности
        for index in range(2, node_count - 3, 4):
            if index + 3 < node_count:
                dag.add_edge(Edge(f"n{index - 2}", f"n{index + 3}"))
        return dag

    @staticmethod
    def layered(node_count: int = 32, seed: int = 0) -> DAG:
        """Mixed topology with more complex layered structure."""
        rng = random.Random(seed)
        dag = DAG()
        for index in range(node_count):
            task = "synthesize" if index >= node_count - 3 else "research"
            dag.add_node(SyntheticGraphFactory._node(index, task, rng))

        layers = SyntheticGraphFactory._layers(node_count, [5, 8, 10, 7, 2])
        for layer_index in range(len(layers) - 1):
            current_layer = layers[layer_index]
            next_layer = layers[layer_index + 1]
            for pos, node in enumerate(current_layer):
                dag.add_edge(Edge(node, next_layer[pos % len(next_layer)]))
                if (pos + 1) % 2 == 0:
                    dag.add_edge(Edge(node, next_layer[(pos + 1) % len(next_layer)]))
        return dag

    @staticmethod
    def centralized_coordinator(node_count: int = 32, seed: int = 0) -> DAG:
        """Hierarchical graph with central coordinator and more complex aggregation."""
        rng = random.Random(seed)
        dag = DAG()
        for index in range(node_count):
            if index == 0:
                task = "plan coordinator"
            elif index == node_count - 1:
                task = "synthesize aggregate"
            elif index % 5 == 0:
                task = "critic"
            else:
                task = "research"
            dag.add_node(SyntheticGraphFactory._node(index, task, rng))

        aggregate = f"n{node_count - 1}"
        # Более сложная структура с множественными путями
        for index in range(1, node_count - 1):
            dag.add_edge(Edge("n0", f"n{index}"))
            if index % 4 == 0:
                dag.add_edge(Edge(f"n{index}", aggregate))
            elif index % 3 == 1 and index + 1 < node_count - 1:
                dag.add_edge(Edge(f"n{index}", f"n{index + 1}"))
            elif index % 5 == 2 and index + 2 < node_count - 1:
                dag.add_edge(Edge(f"n{index}", f"n{index + 2}"))
        return dag

    @staticmethod
    def _node(index: int, task: str, rng: random.Random) -> Node:
        cost = round(rng.uniform(0.07, 0.16), 4)
        return Node(f"n{index}", f"{task} task {index}", {"cost": cost})

    @staticmethod
    def _layers(node_count: int, shape: list) -> list:
        total = sum(shape)
        scaled = [max(1, round(node_count * width / total)) for width in shape]
        while sum(scaled) < node_count:
            scaled[scaled.index(max(scaled))] += 1
        while sum(scaled) > node_count:
            index = scaled.index(max(scaled))
            scaled[index] -= 1

        layers = []
        cursor = 0
        for width in scaled:
            layers.append([f"n{index}" for index in range(cursor, cursor + width)])
            cursor += width
        return layers
