import json
from pathlib import Path

from ..report import WorkflowReport
from ..history import WorkflowSnapshot


class JsonHistoryStore:
    """
    JSON-хранилище истории workflow.
    """


    def __init__(
        self,
        path,
    ):

        self.path = Path(path)



    def save(self, history):

        data = []

        for snapshot in history.all():

            data.append(
                {
                    "id": snapshot.id,
                    "created": snapshot.created.isoformat(),
                    "report": snapshot.report.to_dict()
                }
            )

        self.path.write_text(
            json.dumps(
                data,
                indent=2
            ),
            encoding="utf-8"
        )



    def load(
        self,
    ):

        if not self.path.exists():
            return []


        data = json.loads(
            self.path.read_text(
                encoding="utf-8"
            )
        )


        return data