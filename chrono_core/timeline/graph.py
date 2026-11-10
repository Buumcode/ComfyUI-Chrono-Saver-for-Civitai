class WorkflowTimelineGraph:

    def __init__(
        self,
        nodes=None,
        edges=None,
    ):

        self._nodes = nodes or []
        self._edges = edges or []


    def nodes(self):

        return list(
            self._nodes
        )


    def edges(self):

        return list(
            self._edges
        )
        
    def find_node(
        self,
        node_id,
    ):

        for node in self._nodes:

            if (
                node.get("id") == node_id
                or
                node.get("snapshot") == node_id
            ):
                return node

        return None   
        
    def parents(
        self,
        node_id,
    ):

        result = []


        for edge in self._edges:

            if edge["to"] == node_id:

                result.append(
                    edge["from"]
                )


        return result        
        
    def children(
        self,
        node_id,
    ):

        result = []


        for edge in self._edges:

            if edge["from"] == node_id:

                result.append(
                    edge["to"]
                )


        return result 

    def roots(
        self,
    ):

        all_nodes = {
            node["id"]
            for node in self._nodes
        }


        children = {
            edge["to"]
            for edge in self._edges
        }


        return list(
            all_nodes - children
        )        
        
    def leaves(
        self,
    ):

        all_nodes = {
            node["id"]
            for node in self._nodes
        }


        parents = {
            edge["from"]
            for edge in self._edges
        }


        return list(
            all_nodes - parents
        )        
        
    def ancestors(
        self,
        node_id,
    ):

        result = []

        current = node_id


        while True:

            parents = self.parents(
                current
            )

            if not parents:
                break


            parent = parents[0]

            result.append(
                parent
            )

            current = parent


        return result        
        
    def descendants(
        self,
        node_id,
    ):

        result = []

        queue = [
            node_id
        ]


        visited = set()


        while queue:

            current = queue.pop(0)


            if current in visited:
                continue


            visited.add(
                current
            )


            for child in self.children(current):

                result.append(
                    child
                )

                queue.append(
                    child
                )


        return result        
        
    def common_ancestor(
        self,
        first,
        second,
    ):

        first_chain = [
            first
        ] + self.ancestors(first)


        second_chain = [
            second
        ] + self.ancestors(second)


        for node in first_chain:

            if node in second_chain:
                return node


        return None        
        
    def path(
        self,
        start,
        end,
    ):
        if start == end:
            return [start]


        queue = [
            (
                start,
                [start],
            )
        ]


        visited = set()


        while queue:

            current, route = queue.pop(0)


            if current in visited:
                continue


            visited.add(
                current
            )


            for child in self.children(current):

                new_route = route + [
                    child
                ]


                if child == end:
                    return new_route


                queue.append(
                    (
                        child,
                        new_route,
                    )
                )


        return []        
        
    def has_path(
        self,
        start,
        end,
    ):

        return bool(
            self.path(
                start,
                end,
            )
        )
        
    def is_ancestor(
        self,
        ancestor,
        node,
    ):

        return self.has_path(
            ancestor,
            node,
        )        
        
    def is_descendant(
        self,
        node,
        ancestor,
    ):

        return self.is_ancestor(
            ancestor,
            node,
        )        
        
