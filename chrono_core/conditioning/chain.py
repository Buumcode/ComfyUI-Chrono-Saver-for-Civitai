from ..graph.node import Node


class ConditioningChain:
    """
    Последовательность узлов conditioning-графа.
    """


    def __init__(self, nodes=None):

        self.nodes = nodes or []



    def add(self, node: Node):

        self.nodes.append(node)



    def contains(self, class_type: str) -> bool:

        return any(
            node.is_type(class_type)
            for node in self.nodes
        )



    def find(self, class_type: str):

        for node in self.nodes:

            if node.is_type(class_type):
                return node

        return None



    def __iter__(self):

        return iter(self.nodes)



    def __repr__(self):

        return (
            "<ConditioningChain "
            f"{[n.class_type for n in self.nodes]}>"
        )