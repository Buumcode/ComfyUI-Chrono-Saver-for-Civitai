def make_air(resource_type: str, model_id: int, version_id: int):
    """
    Создаёт Civitai AIR.

    Примеры:
    urn:air:model:123@456
    urn:air:lora:123@456
    """

    return f"urn:air:{resource_type}:{model_id}@{version_id}"