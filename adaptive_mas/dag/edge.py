from typing import Any, Dict


class Edge:
    """Represents an edge in the DAG with dependency information."""

    def __init__(self, from_node: str, to_node: str, dependency_type: str = "depends_on", data: Dict[str, Any] = None):
        self.from_node = from_node
        self.to_node = to_node
        self.dependency_type = dependency_type
        self.data = data or {}

    def __repr__(self):
        return f"Edge({self.from_node} -> {self.to_node}, type={self.dependency_type})"