from ..graph.graph import Graph


class ImageExtractor:

    IMAGE_TYPES = {
        "EmptyLatentImage",
    }

    def extract(self, graph: Graph):

        node = graph.find_first_type(
            *self.IMAGE_TYPES
        )

        if node is None:
            return None

        return {
            "width": node.get_input("width"),
            "height": node.get_input("height"),
        }