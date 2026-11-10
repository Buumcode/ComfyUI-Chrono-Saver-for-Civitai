class DependencyAnalyzer:
    """
    Анализатор зависимостей workflow.

    Строит простую карту:
    node -> node

    Не знает о конкретных ComfyUI-нодах.
    Работает только через Graph API.
    """

    def analyze(self, graph):

        nodes = []
        edges = []

        for node in graph.all_nodes():

            nodes.append(
                {
                    "id": node.id,
                    "type": node.class_type,
                }
            )

            for value in node.inputs.values():

                if isinstance(value, list) and value:

                    parent = graph.get(value[0])

                    if parent:
                        edges.append(
                            {
                                "from": parent.id,
                                "to": node.id,
                            }
                        )

        return {
            "nodes": nodes,
            "edges": edges,
        }