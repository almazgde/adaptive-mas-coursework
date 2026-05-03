from typing import Any, Dict


class Node:
    """Represents a node in the DAG with a task and associated data."""

    def __init__(self, node_id: str, task: str, data: Dict[str, Any] = None):
        self.node_id = node_id
        self.task = task
        self.data = data or {}

    def __repr__(self):
        return f"Node(id={self.node_id}, task={self.task})"