from .chrono_node import ChronoSaverForCivitai

NODE_CLASS_MAPPINGS = {
    "ChronoSaverForCivitai": ChronoSaverForCivitai,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "ChronoSaverForCivitai": "Chrono Saver for Civitai",
}

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS"]
