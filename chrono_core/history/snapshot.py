from datetime import datetime, UTC
import uuid
from uuid import uuid4
from datetime import datetime, timezone


class WorkflowSnapshot:
    """
    Снимок состояния workflow.

    Хранит результат анализа
    в определённый момент.
    """


    def __init__(self, report):

        self.id = str(uuid4())

        self.report = report

        self.created = datetime.now(
            timezone.utc
        )

        self.report = report



    def compare(
        self,
        other,
    ):

        from ..diff import WorkflowDiff


        return WorkflowDiff().compare(
            self.report,
            other.report
        )



    def to_dict(self):

        return {
            "id": self.id,
            "created": self.created.isoformat(),
            "report": self.report.to_dict(),
        }
        
    @classmethod
    def from_dict(cls, data):

        from ..report import WorkflowReport

        snapshot = cls(
            WorkflowReport.from_dict(
                data["report"]
            )
        )

        snapshot.id = data["id"]

        return snapshot    