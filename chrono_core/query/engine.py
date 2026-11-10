from .operators import OPERATORS


class QueryEngine:

    def parse_filter(
        self,
        key,
    ):

        parts = key.split("__")


        if parts[-1] in OPERATORS:

            return (
                parts[:-1],
                parts[-1],
            )


        return (
            parts,
            "eq",
        )


    def match(
        self,
        value,
        operator,
        expected,
    ):

        if operator == "eq":
            return value == expected


        if operator == "ne":
            return value != expected


        if operator == "gt":
            return value > expected


        if operator == "gte":
            return value >= expected


        if operator == "lt":
            return value < expected


        if operator == "lte":
            return value <= expected


        if operator == "contains":
            return expected in value


        if operator == "startswith":
            return value.startswith(expected)


        if operator == "endswith":
            return value.endswith(expected)


        if operator == "in":
            return value in expected


        return False