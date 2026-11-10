from collections import deque

from .graph import Graph
from .node import Node


class GraphWalker:
    """
    Универсальный обходчик ComfyUI-графа.

    Идёт от узла вверх по входящим связям.
    Не знает о конкретных моделях и нодах.
    """

    def __init__(self, graph: Graph):
        self.graph = graph


    def get_link_node(self, value):
        """
        ComfyUI link format:

        ["node_id", output_index]

        Возвращает Node.
        """

        if not isinstance(value, list):
            return None

        if len(value) < 1:
            return None

        return self.graph.get(value[0])


    def walk_backwards(
        self,
        start,
        max_depth=50,
    ):
        """
        Обход графа назад.

        Возвращает найденные узлы
        в порядке обнаружения.
        """

        result = []

        start_node = self.get_link_node(start)

        if start_node is None:
            return result


        queue = deque([start_node])
        visited = set()


        while queue:

            node = queue.popleft()


            if node.id in visited:
                continue

            visited.add(node.id)

            result.append(node)


            if len(visited) >= max_depth:
                break


            for value in node.inputs.values():

                next_node = self.get_link_node(value)

                if next_node:
                    queue.append(next_node)


        return result



    def find_first(
        self,
        start,
        predicate,
        max_depth=50,
    ):
        """
        Найти первый узел,
        удовлетворяющий условию.
        """

        for node in self.walk_backwards(
            start,
            max_depth
        ):

            if predicate(node):
                return node


        return None