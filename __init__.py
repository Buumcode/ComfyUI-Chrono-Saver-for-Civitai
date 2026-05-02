from .chrono_node import ChronoSaveForCivit

NODE_CLASS_MAPPINGS = {
    "ChronoSaveForCivit": ChronoSaveForCivit,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "ChronoSaveForCivit": "💾 Chrono Save for Civitai",
}

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS"]
