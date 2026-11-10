from typing import Any


class Node:
    """
    Универсальный узел графа.

    ChronoCore ничего не знает о ComfyUI.
    Для него это просто вершина графа.
    """

    def __init__(
        self,
        node_id: str,
        class_type: str,
        inputs: dict[str, Any],
        meta: dict | None = None,
    ):
        self.id = str(node_id)
        self.class_type = class_type
        self.inputs = inputs or {}
        self.meta = meta or {}

    def get_input(self, name: str):
        return self.inputs.get(name)

    def is_type(self, name: str) -> bool:
        return self.class_type == name

    def __repr__(self):
        return f"<Node {self.id}: {self.class_type}>"