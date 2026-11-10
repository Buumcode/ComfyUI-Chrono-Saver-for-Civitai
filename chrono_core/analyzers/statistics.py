from collections import Counter


class WorkflowStatistics:
    """
    Анализатор структуры workflow.

    Работает через Graph API.
    Не модифицирует Node.
    """


    def analyze(self, graph):

        nodes = list(
            graph.all_nodes()
        )


        types = Counter(
            node.class_type
            for node in nodes
        )


        return {

            "nodes": len(nodes),

            "node_types": dict(
                types
            ),

            "depth": self._estimate_depth(
                graph
            ),

            "has_lora": (
                "LoraLoader"
                in types
            ),

            "has_upscale": any(
                "Upscale"
                in node.class_type
                for node in nodes
            ),
        }



    def _estimate_depth(
        self,
        graph
    ):

        maximum = 0


        for node in graph.all_nodes():

            depth = self._depth(
                graph,
                node,
                set()
            )

            maximum = max(
                maximum,
                depth
            )


        return maximum



    def _depth(
        self,
        graph,
        node,
        visited
    ):

        if node.id in visited:
            return 0


        visited.add(
            node.id
        )


        depths = []


        for value in node.inputs.values():

            if isinstance(value, list) and value:

                parent = graph.get(
                    value[0]
                )

                if parent:

                    depths.append(
                        self._depth(
                            graph,
                            parent,
                            visited.copy()
                        )
                    )


        if not depths:
            return 1


        return 1 + max(depths)