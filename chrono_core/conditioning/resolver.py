from ..graph.graph import Graph
from ..graph.node import Node
from ..graph.walker import GraphWalker
from .chain import ConditioningChain


class ConditioningResolver:
    """
    Разбирает conditioning-цепочки ComfyUI.

    Этот слой ничего не знает о prompt.
    Его задача:
    понять, что произошло с conditioning.
    """


    def __init__(self, graph: Graph):

        self.graph = graph
        self.walker = GraphWalker(graph)



    def resolve(self, link) -> Node | None:
        """
        Возвращает первый значимый conditioning-узел.
        """

        if not isinstance(link, list):
            return None


        node = self.walker.get_link_node(link)


        if node is None:
            return None


        return node


    def resolve_chain(self, link):

        nodes = self.walker.walk_backwards(
            link
        )

        return ConditioningChain(nodes)


    def is_zero_out(
        self,
        link
    ) -> bool:
        """
        Проверяет, был ли conditioning обнулён.
        """

        node = self.resolve(link)


        if node is None:
            return False


        return node.is_type(
            "ConditioningZeroOut"
        )