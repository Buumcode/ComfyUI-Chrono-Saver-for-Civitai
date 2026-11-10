from ..graph.node import Node


def is_text_node(node: Node) -> bool:
    """
    Определяет ноды, которые могут содержать prompt.
    """

    class_type = node.class_type or ""

    return (
        "CLIPTextEncode" in class_type
        or "TextEncode" in class_type
    )


def extract_text(node: Node) -> str:
    """
    Извлекает текст из текстовой ноды.
    """

    for key in (
        "text",
        "text_g",
        "text_l",
        "prompt",
        "string",
    ):
        value = node.get_input(key)

        if isinstance(value, str):
            return value

    return ""