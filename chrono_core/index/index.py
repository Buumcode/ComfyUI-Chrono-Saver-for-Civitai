class SnapshotIndex:

    def __init__(
        self,
        repository,
    ):

        self.repository = repository
        
        self._index = {}
        
        self._indexed_count = 0
        
        self._indexed_last_id = None


    def find(
        self,
        **filters,
    ):
        
        self._ensure_built()

        if len(filters) == 1:

            key, value = next(
                iter(filters.items())
            )

            parts = key.split("__")

            path = ".".join(parts)

            if path in self._index:

                snapshots = self._index[path].get(
                    value,
                    []
                )

                from ..query import QueryResult

                return QueryResult(
                    snapshots
                )


        return self.repository.timeline().find_snapshots(
            **filters
        )
        
    def build(
        self,
    ):

        self._index.clear()

        snapshots = self.repository.all()

        for snapshot in snapshots:

            data = snapshot.report.to_dict()

            self._walk(
                snapshot,
                data,
            )


        self._indexed_count = len(
            snapshots
        )


        if snapshots:

            self._indexed_last_id = (
                snapshots[-1].id
            )

        else:

            self._indexed_last_id = None
            
            
    def _walk(
        self,
        snapshot,
        value,
        prefix="",
    ):

        if not isinstance(
            value,
            dict,
        ):
            return

        for key, item in value.items():

            path = (
                key
                if not prefix
                else f"{prefix}.{key}"
            )

            self._index.setdefault(
                path,
                {}
            )

            if isinstance(
                item,
                dict,
            ):

                self._walk(
                    snapshot,
                    item,
                    path,
                )

            else:

                self._index[path].setdefault(
                    item,
                    [],
                ).append(
                    snapshot
                ) 

    def _ensure_built(
        self,
    ):

        snapshots = self.repository.all()


        current_count = len(
            snapshots
        )


        current_last_id = None


        if snapshots:

            current_last_id = (
                snapshots[-1].id
            )


        if (
            not self._index
            or
            self._indexed_count != current_count
            or
            self._indexed_last_id != current_last_id
        ):

            self.build()                