from .event import WorkflowEvent


class WorkflowEventLog:

    def __init__(self):

        self.events = []


    def add(
        self,
        event_type,
        payload=None
    ):

        event = WorkflowEvent(
            event_type,
            payload
        )

        self.events.append(
            event
        )

        return event


    def all(self):

        return list(
            self.events
        )


    def latest(self):

        if not self.events:
            return None

        return self.events[-1]


    def to_dict(self):

        return [
            event.to_dict()
            for event
            in self.events
        ]
        
    @classmethod
    def from_dict(
        cls,
        data
    ):

        log = cls()

        from .event import WorkflowEvent


        for item in data:

            log.events.append(
                WorkflowEvent.from_dict(
                    item
                )
            )


        return log        