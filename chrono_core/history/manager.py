from .snapshot import WorkflowSnapshot
from ..branches import WorkflowBranch
from ..report import WorkflowReport
from ..events import WorkflowEventLog


class HistoryManager:

    def __init__(self):

        self.event_log = WorkflowEventLog()

        main = WorkflowBranch(
            "main"
        )

        self.branches = {
            "main": main
        }

        self.current_branch = "main"

        # compatibility with pre-1.0 API
        self.active_branch = "main"

        self.snapshots = main.snapshots


    def _branch(self):

        return self.branches[
            self.current_branch
        ]


    def add(
        self,
        item,
        branch=None
    ):

        if isinstance(
            item,
            WorkflowReport
        ):

            item = WorkflowSnapshot(
                item
            )


        if branch is None:
            branch = self.current_branch


        if branch not in self.branches:

            self.create_branch(
                branch
            )


        self.branches[branch].add(
            item
        )

        self.event_log.add(
            "snapshot_created",
            {
                "snapshot": item.id,
                "branch": branch,
            }
)

        if branch == self.current_branch:

            self.snapshots = (
                self.branches[branch].snapshots
            )


        return item


    def all(self):

        return self._branch().all()


    def latest(self):

        items = self.all()

        if not items:
            return None

        return items[-1]


    def get(
        self,
        snapshot_id,
    ):

        for snapshot in self.all():

            if snapshot.id == snapshot_id:
                return snapshot

        return None


    def diff(
        self,
        old_id,
        new_id,
    ):

        old = self.get(
            old_id
        )

        new = self.get(
            new_id
        )

        if old is None or new is None:
            return None


        return old.compare(
            new
        )


    def create_branch(
        self,
        name: str,
    ):

        if name in self.branches:
            return self.branches[name]


        branch = WorkflowBranch(
            name
        )

        current = self._branch()

        if current.all():

            branch.branch_point = current.all()[-1]

        else:

            branch.branch_point = None

        branch.parent = self.current_branch
        branch.branch_point = self.latest()

        self.branches[name] = branch
            
        self.event_log.add(
            "branch_created",
            {
                "branch": name
            }
        )

        return branch


    def get_branch(
        self,
        name: str,
    ):

        return self.branches.get(
            name
        )


    def list_branches(self):

        return list(
            self.branches.keys()
        )


    @property
    def items(self):

        return self._branch().all()


    def checkout(
        self,
        name: str,
    ):

        if name not in self.branches:
            raise ValueError(
                f"Unknown branch: {name}"
            )


        self.current_branch = name
        
        self.event_log.add(
            "branch_checkout",
            {
                "branch": name
            }
        )        
        
        self.active_branch = name

        # compatibility with pre-1.0 API
        self.snapshots = (
            self.branches[name].snapshots
        )

        return self.branches[name]
        
    def to_dict(self):

        return {
            "branches":
                {
                    name:
                        branch.to_dict()
                    for name, branch
                    in self.branches.items()
                },
            # compatibility with pre-1.0 API
            "current_branch":
                self.current_branch,

            "active_branch":
                self.active_branch,
                
            "events":
                self.event_log.to_dict(),    
                    }  

    @classmethod
    def from_dict(
        cls,
        data
    ):

        manager = cls()
        # up this import to first lines?        
        from ..events import WorkflowEventLog


        manager.event_log = (
            WorkflowEventLog.from_dict(
                data.get(
                    "events",
                    []
                )
            )
        )        

        manager.branches = {}
        # up this import to first lines?
        from ..branches import WorkflowBranch


        for name, branch_data in (
            data.get("branches", {})
            .items()
        ):

            manager.branches[name] = (
                WorkflowBranch.from_dict(
                    branch_data
                )
            )


        manager.current_branch = (
            data.get(
                "current_branch",
                "main"
            )
        )

        manager.active_branch = (
            data.get(
                "active_branch",
                "main"
            )
        )


        if "main" in manager.branches:

            manager.snapshots = (
                manager.branches["main"]
                .snapshots
            )


        return manager 

    def events(self):

        return self.event_log.all()        