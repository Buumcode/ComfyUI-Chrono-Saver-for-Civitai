import json
from pathlib import Path


class WorkflowLoader:
    """
    Загружает workflow из JSON-файла.

    Не зависит от ComfyUI.
    """

    @staticmethod
    def load(path):

        path = Path(path)

        with path.open(
            "r",
            encoding="utf-8"
        ) as f:

            return json.load(f)