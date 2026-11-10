from ..graph.graph import Graph
from ..graph.walker import GraphWalker
from ..conditioning.resolver import ConditioningResolver

from .text import (
    is_text_node,
    extract_text,
)


class PromptExtractor:


    def extract(self, graph: Graph):

        result = {
            "positive": "",
            "negative": "",
        }


        walker = GraphWalker(graph)
        conditioning = ConditioningResolver(graph)


        for node in graph.all_nodes():

            positive = node.get_input(
                "positive"
            )

            negative = node.get_input(
                "negative"
            )


            if positive:

                result["positive"] = (
                    self._extract_from_link(
                        positive,
                        walker,
                        conditioning
                    )
                )


            if negative:

                result["negative"] = (
                    self._extract_from_link(
                        negative,
                        walker,
                        conditioning
                    )
                )


        # fallback для workflow без KSampler
        if not result["positive"]:

            for node in graph.all_nodes():

                if node.class_type.startswith(
                    "CLIPTextEncode"
                ):

                    text = node.get_input(
                        "text"
                    )

                    if isinstance(text, str):
                        result["positive"] = text
                        break


        return result



    def _extract_from_link(
        self,
        link,
        walker: GraphWalker,
        conditioning: ConditioningResolver,
    ):

        if not isinstance(link, list):
            return ""


        first = walker.get_link_node(
            link
        )

        if first is None:
            return ""


        if conditioning.is_zero_out(link):
            return ""


        node = walker.find_first(
            link,
            is_text_node
        )


        if node:
            return extract_text(node)


        return ""