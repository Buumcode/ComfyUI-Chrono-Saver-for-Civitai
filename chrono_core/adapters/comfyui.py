from ..graph.graph import Graph
from ..graph.node import Node


class ComfyUIAdapter:

    @staticmethod
    def from_prompt(prompt: dict) -> Graph:

        graph = Graph()

        if not isinstance(prompt, dict):
            return graph

        for node_id, data in prompt.items():

            if not isinstance(data, dict):
                continue

            node = Node(
                node_id=node_id,
                class_type=data.get(
                    "class_type",
                    data.get("type", "")
                ),
                inputs=data.get("inputs", {}),
                meta=data.get("_meta", {}),
            )

            graph.add_node(node)

        return graph