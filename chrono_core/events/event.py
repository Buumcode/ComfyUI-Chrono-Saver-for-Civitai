from datetime import datetime, timezone
import uuid


class WorkflowEvent:

    def __init__(
        self,
        event_type,
        payload=None
    ):

        self.id = str(
            uuid.uuid4()
        )

        self.type = event_type

        self.payload = (
            payload or {}
        )

        self.created = (
            datetime.now(
                timezone.utc
            )
        )


    def to_dict(self):

        return {
            "id": self.id,
            "type": self.type,
            "payload": self.payload,
            "created":
                self.created.isoformat(),
        }
        
    @classmethod
    def from_dict(
        cls,
        data
    ):

        event = cls(
            data["type"],
            data.get(
                "payload",
                {}
            )
        )

        event.id = data["id"]

        return event        