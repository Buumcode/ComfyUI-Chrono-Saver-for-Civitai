class WorkflowBranch:
    """
    Ветка развития workflow.

    Хранит последовательность Snapshot,
    принадлежащих одному эксперименту.
    """


    def __init__(
        self,
        name,
        parent=None,
        branch_point=None
    ):

        self.name = name

        self.parent = parent

        self.branch_point = branch_point

        self.snapshots = []


    def add(
        self,
        snapshot,
    ):

        self.snapshots.append(
            snapshot
        )


    def latest(self):

        if not self.snapshots:
            return None

        return self.snapshots[-1]


    def size(self):

        return len(
            self.snapshots
        )


    def all(self):

        return list(
            self.snapshots
        )
        
    def to_dict(self):

        return {
            "name": self.name,

            "snapshots": [
                snapshot.to_dict()
                for snapshot
                in self.snapshots
            ],
        }        
        
    @classmethod
    def from_dict(
        cls,
        data
    ):

        from ..history.snapshot import WorkflowSnapshot

        branch = cls(
            data["name"]
        )


        branch.snapshots = [
            WorkflowSnapshot.from_dict(
                snapshot
            )
            for snapshot
            in data.get(
                "snapshots",
                []
            )
        ]


        return branch        