from ..history import HistoryManager
from ..storage import JsonHistoryStore
from ..timeline import WorkflowTimeline
from ..query import WorkflowQuery


class WorkflowRepository:
    """
    Фасад для работы с историей workflow.

    Координирует HistoryManager, BranchManager
    и Storage, не добавляя собственной бизнес-логики.
    """


    def __init__(self):

        self.history_manager = HistoryManager()


    def add(
        self,
        report,
        branch=None
    ):

        if branch is None:
            return self.history_manager.add(
                report
            )

        return self.history_manager.add(
            report,
            branch=branch
        )


    def latest(self):

        return self.history_manager.latest()
        

    def history(self):

        return self.history_manager.all()        


    def timeline(self):

        return WorkflowTimeline(
            self.history_manager
        )


    def diff(
        self,
        old_id,
        new_id
    ):

        return self.history_manager.diff(
            old_id,
            new_id
        )


    def all(self):

        return self.history_manager.all()


    # Branch operations

    def create_branch(self, name):

        return self.history_manager.create_branch(name)


    def checkout(self, name):

        return self.history_manager.checkout(name)


    def current_branch(self):

        return self.history_manager.get_branch(
            self.history_manager.current_branch
        )


    def branches(self):

        return self.history_manager.list_branches()
        
    def query(self):

        return WorkflowQuery(
            self.history_manager
        )

    def to_dict(self):

        return {
            "history":
                self.history_manager.to_dict(),

            "active_branch":
                self.history_manager.active_branch,
        }


    @classmethod
    def from_dict(
        cls,
        data
    ):

        repo = cls()

        repo.history_manager = (
            HistoryManager.from_dict(
                data["history"]
            )
        )

        repo.history_manager.active_branch = (
            data.get(
                "active_branch",
                "main"
            )
        )

        return repo 

    def save(self, path):

        from ..serialization import WorkflowSerializer
        import json

        serializer = WorkflowSerializer()

        data = serializer.dump(
            self
        )

        with open(
            path,
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                data,
                file,
                indent=4
            ) 

    @classmethod
    def load(
        cls,
        path
    ):

        from ..serialization import WorkflowSerializer
        import json

        with open(
            path,
            "r",
            encoding="utf-8"
        ) as file:

            data = json.load(
                file
            )


        serializer = WorkflowSerializer()

        return serializer.load(
            data
        )            

    def snapshot_index(self):

        from ..index import SnapshotIndex

        return SnapshotIndex(
            self
        )