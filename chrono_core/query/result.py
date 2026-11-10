class QueryResult:

    def __init__(
        self,
        items,
    ):
        self.items = items


    def __iter__(self):

        return iter(
            self.items
        )


    def __len__(self):

        return len(
            self.items
        )


    def __getitem__(
        self,
        index,
    ):

        return self.items[index]


    def first(self):

        if not self.items:
            return None

        return self.items[0]


    def last(self):

        if not self.items:
            return None

        return self.items[-1]


    def count(self):

        return len(
            self.items
        )
        
    def order_by(
        self,
        path,
        descending=False,
    ):

        parts = path.split(".")

        def get_value(item):
            return self._resolve(
                item,
                parts,
            )


        return QueryResult(
            sorted(
                self.items,
                key=get_value,
                reverse=descending,
            )
        )

    def _resolve(
        self,
        item,
        parts,
    ):

        value = item

        # Snapshot -> Report -> dict
        if hasattr(value, "report"):
            value = value.report.to_dict()

        for part in parts:
            value = value[part]

        return value        
        
    def limit(
        self,
        count,
    ):

        return QueryResult(
            self.items[:count]
        )        
        
    def offset(
        self,
        count,
    ):

        return QueryResult(
            self.items[count:]
        )        
        
    def select(
        self,
        path,
    ):

        parts = path.split(".")

        result = []

        for item in self.items:

            result.append(
                self._resolve(
                    item,
                    parts,
                )
            )

        return QueryResult(
            result
        )        
        
    def min(self):

        return min(
            self.items
        )        
        
    def max(
        self,
    ):

        return max(
            self.items
        )        
        
    def sum(
        self,
    ):

        return sum(
            self.items
        )        
        
    def avg(
        self,
    ):

        if not self.items:
            return 0

        return (
            sum(self.items)
            /
            len(self.items)
        )        
        
    def distinct(
        self,
    ):

        result = []
        seen = set()

        for item in self.items:

            key = repr(item)

            if key in seen:
                continue

            seen.add(key)

            result.append(
                item
            )

        return QueryResult(
            result
        )        