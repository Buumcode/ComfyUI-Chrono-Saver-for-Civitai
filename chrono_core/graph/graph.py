from .node import Node


class Graph:

    def __init__(self):
        self.nodes: dict[str, Node] = {}

    def add_node(self, node: Node):
        self.nodes[node.id] = node

    def get(self, node_id: str):
        return self.nodes.get(str(node_id))

    def __contains__(self, node_id):
        return str(node_id) in self.nodes

    def all_nodes(self):
        return self.nodes.values()
        
    def find_first_type(
        self,
        *types: str,
    ):
        """
        Возвращает первый узел
        одного из указанных типов.
        """

        for node in self.all_nodes():

            if node.class_type in types:
                return node

        return None

    ### `find_all_types()`
    def find_all_types(
        self,
        *types: str,
    ):
        """
        Возвращает все узлы
        указанных типов.
        """

        result = []

        for node in self.all_nodes():

            if node.class_type in types:
                result.append(node)

        return result

    ### `find_first()`
    def find_first(
        self,
        predicate,
    ):
        """
        Возвращает первый узел,
        удовлетворяющий условию.
        """

        for node in self.all_nodes():

            if predicate(node):
                return node

        return None        