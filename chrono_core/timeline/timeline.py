from ..diff import WorkflowDiff
from ..report import WorkflowReport
from ..query import QueryEngine


class WorkflowTimeline:
    """
    Преобразует историю snapshot
    в последовательность событий.
    """

    def __init__(
        self,
        history,
    ):

        self.history = history

        self.query = QueryEngine()


    def build(self):

        snapshots = self.history.all()

        if not snapshots:
            return []


        events = []


        events.append(
            self._create_initial_event(
                snapshots[0]
            )
        )


        for index in range(
            1,
            len(snapshots)
        ):

            previous = snapshots[index - 1]

            current = snapshots[index]


            diff = previous.compare(
                current
            )


            if (
                diff["changed"]
                or diff["added"]
                or diff["removed"]
            ):

                events.append(
                    self._create_change_event(
                        current,
                        self._normalize_diff(diff),
                    )
                )


        return events
        
    def _normalize_diff(
        self,
        diff,
    ):

        if "changed" in diff:
            return diff["changed"]


        return diff

    def events(self):

        return [
            event.to_dict()
            for event in self.history.events()
        ]       

        
    def stream(self):

        stream = []


        for event in self.history.events():

            stream.append(
                event.to_dict()
            )


        return sorted(
            stream,
            key=lambda item:
                item["created"]
        )        

        
    def filter(
        self,
        type=None,
        after=None,
        before=None
    ):

        items = self.stream()


        result = []


        for item in items:

            if type is not None:

                if item.get("type") != type:
                    continue


            created = item.get(
                "created"
            )


            if after is not None:

                if created <= after:
                    continue


            if before is not None:

                if created >= before:
                    continue


            result.append(
                item
            )


        return result

    def summary(self):

        stream = self.stream()        

        result = {
            "total": len(stream),
            "snapshots": 0,
            "branches": 0,
            "changes": 0,
        }


        for item in stream:

            event_type = item.get("type")


            if event_type in (
                "snapshot_created",
                "created",
            ):
                result["snapshots"] += 1


            elif event_type == "branch_created":
                result["branches"] += 1


            elif event_type == "changed":
                result["changes"] += 1


        return result 

    def changed(
        self,
        key,
    ):

        result = []


        for event in self.build():

            if event["type"] != "changed":
                continue


            changes = event.get(
                "changes",
                {}
            )


            if key not in changes:
                continue


            result.append(
                changes[key]
            )


        return result        
        
    def history_of(
        self,
        path,
    ):

        result = []


        parts = path.split(
            "."
        )


        for snapshot in self.history.all():

            value = snapshot.report.to_dict()


            try:

                for part in parts:

                    value = value[part]


                result.append(
                    value
                )


            except (
                KeyError,
                TypeError,
            ):

                continue


        return result

    def branch_history(
        self,
        branch,
    ):

        if branch not in self.history.branches:
            return []


        target = self.history.branches[
            branch
        ]


        snapshots = []


        branch_point = getattr(
            target,
            "branch_point",
            None
        )


        if branch_point is not None:
            snapshots.append(
                branch_point
            )


        snapshots.extend(
            target.all()
        )


        return [
            snapshot.report.to_dict()
            for snapshot in snapshots
        ]
        
    def compare_branches(
        self,
        old_branch,
        new_branch,
    ):

        old_history = self.branch_history(
            old_branch
        )

        new_history = self.branch_history(
            new_branch
        )


        if not old_history or not new_history:
            return {
                "changed": {},
                "added": {},
                "removed": {},
            }

        old_report = WorkflowReport.from_dict(
            old_history[-1]
        )

        new_report = WorkflowReport.from_dict(
            new_history[-1]
        )


        return WorkflowDiff().compare(
            old_report,
            new_report
        )        
        
    def metrics(self):

        result = []


        for snapshot in self.history.all():

            report = snapshot.report


            if report.metrics:

                result.append(
                    report.metrics.copy()
                )


        return result 

    def metric_summary(self):

        metrics = self.metrics()

        result = {}


        for item in metrics:

            for name, value in item.items():

                if name not in result:

                    result[name] = {
                        "count": 0,
                        "min": value,
                        "max": value,
                        "sum": 0,
                    }


                result[name]["count"] += 1

                result[name]["sum"] += value


                if value < result[name]["min"]:
                    result[name]["min"] = value


                if value > result[name]["max"]:
                    result[name]["max"] = value


        for name in result:

            result[name]["avg"] = (
                result[name]["sum"]
                /
                result[name]["count"]
            )

            del result[name]["sum"]


        return result

    def export(self):

        return {
            "events": len(self.stream()),
            "snapshots": len(self.history.all()),
            "metrics": self.metric_summary(),
        }

    def report(self):

        return {
            "events": len(self.stream()),

            "snapshots": len(
                self.history.all()
            ),

            "branches": (
                self.history.list_branches()
            ),

            "metrics": self.metric_summary(),
        }

    def snapshot_at(
        self,
        index
    ):

        snapshots = self.history.all()

        if index < 0 or index >= len(snapshots):
            return None


        snapshot = snapshots[index]


        return snapshot.report.to_dict()
        
    def reconstruct(
        self,
        index
    ):

        snapshots = self.history.all()


        if not snapshots:
            return None


        if index < 0 or index >= len(snapshots):
            return None


        snapshot = snapshots[index]


        return snapshot.report.to_dict()

    def replay(self):

        snapshots = self.history.all()


        result = []


        for index, snapshot in enumerate(
            snapshots
        ):

            result.append(
                {
                    "index": index,
                    "state": snapshot.report.to_dict(),
                }
            )


        return result

    def checkpoints(self):

        checkpoints = []

        for index, snapshot in enumerate(
            self.history.all()
        ):

            checkpoints.append(
                {
                    "index": index,
                    "snapshot": snapshot.id,
                    "state": snapshot.report.to_dict(),
                }
            )

        return checkpoints 

    def restore(
        self,
        index
    ):

        snapshots = self.history.all()

        snapshot = snapshots[index]

        return snapshot.report.to_dict() 

    def rollback(
        self,
        index
    ):

        snapshots = self.history.all()

        snapshot = snapshots[index]


        from ..report import WorkflowReport

        report = WorkflowReport.from_dict(
            snapshot.report.to_dict()
        )


        self.history.add(
            report
        )


        return report.to_dict()
        

    def graph(self):

        from .graph import WorkflowTimelineGraph

        nodes = []
        edges = []

        previous = None

        for snapshot in self.history.all():

            nodes.append(
                {
                    "id": snapshot.id,
                    "snapshot": snapshot.id,
                    "report": snapshot.report.to_dict(),
                }
            )

            if previous is not None:

                edges.append(
                    {
                        "from": previous.id,
                        "to": snapshot.id,
                    }
                )

            previous = snapshot

        return WorkflowTimelineGraph(
            nodes=nodes,
            edges=edges,
        )   

        
    def history_between(
        self,
        start,
        end,
    ):

        graph = self.graph()

        ids = graph.path(
            start,
            end,
        )

        result = []

        for node_id in ids:

            node = graph.find_node(
                node_id
            )

            result.append(
                node
            )

        return result        

    def changes_between(
        self,
        start,
        end,
    ):

        history = self.history_between(
            start,
            end,
        )


        if len(history) < 2:
            return {}


        old_report = WorkflowReport.from_dict(
            history[0]["report"]
        )


        new_report = WorkflowReport.from_dict(
            history[-1]["report"]
        )


        diff = WorkflowDiff()


        return diff.compare(
            old_report,
            new_report,
        ) 

    def branch_base(
        self,
        old_branch,
        new_branch,
    ):

        branch = self.history.branches.get(
            new_branch
        )

        if branch is None:
            return None


        point = getattr(
            branch,
            "branch_point",
            None,
        )

        if point is None:
            return None


        return point.id        

    def merge_preview(
        self,
        target_branch,
        source_branch,
    ):

        return self.compare_branches(
            target_branch,
            source_branch,
        )        
        
    def merge_conflicts(
        self,
        target_branch,
        source_branch,
    ):

        diff = self.compare_branches(
            target_branch,
            source_branch,
        )

        return diff.get(
            "changed",
            {}
        )        
        
    def merge(
        self,
        target_branch,
        source_branch,
    ):

        history = self.branch_history(
            source_branch
        )

        if not history:
            return None

        return history[-1]
        
        
    def find_snapshots(
        self,
        **filters,
    ):

        result = []

        for snapshot in self.history.all():

            data = snapshot.report.to_dict()

            matched = True

            for key, expected in filters.items():

                parts, operator = self.query.parse_filter(
                    key
                )

                value = data

                for part in parts:

                    if not isinstance(
                        value,
                        dict,
                    ):

                        matched = False
                        break

                    if part not in value:

                        matched = False
                        break

                    value = value[part]

                if not matched:

                    break

                if not self.query.match(
                    value,
                    operator,
                    expected,
                ):

                    matched = False
                    break

            if matched:

                result.append(
                    snapshot
                )

        from ..query.result import QueryResult

        return QueryResult(
            result
        )
        
        
    def find(
        self,
        **filters,
    ):

        from ..query.result import QueryResult


        return QueryResult(
            [
                snapshot.report.to_dict()
                for snapshot in self.find_snapshots(
                    **filters
                )
            ]
        )       
        
    def first(
        self,
        **filters,
    ):

        items = self.find(
            **filters
        )

        if not items:
            return None

        return items[0]        
        
    def last(
        self,
        **filters,
    ):

        items = self.find(
            **filters
        )

        if not items:
            return None

        return items[-1]        
        
    def exists(
        self,
        **filters,
    ):

        return bool(
            self.find_snapshots(
                **filters
            )
        )        
        
    def count(
        self,
        **filters,
    ):

        return len(
            self.find_snapshots(
                **filters
            )
        )

    def _create_initial_event(
        self,
        snapshot,
    ):

        return {
            "type": "created",
            "message": "Initial workflow",
            "snapshot": snapshot.id,
        }  

    def _create_change_event(
        self,
        snapshot,
        changes,
    ):

        return {
            "type": "changed",
            "snapshot": snapshot.id,
            "changes": changes,
        }        