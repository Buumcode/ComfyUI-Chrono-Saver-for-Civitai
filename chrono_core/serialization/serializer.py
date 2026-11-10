from ..repository import WorkflowRepository


class WorkflowSerializer:
    """
    Сериализация объектов ChronoCore.
    """

    FORMAT = "chrono_core"
    VERSION = 1


    def dump(
        self,
        repository
    ):

        return {
            "format": self.FORMAT,
            "version": self.VERSION,
            "repository": repository.to_dict(),
        }


    def load(
        self,
        data
    ):

        self.validate(
            data
        )

        return WorkflowRepository.from_dict(
            data["repository"]
        )
        
    def validate(
        self,
        data
    ):

        if data.get(
            "format"
        ) != self.FORMAT:

            raise ValueError(
                "Invalid ChronoCore format"
            )


        if data.get(
            "version"
        ) != self.VERSION:

            raise ValueError(
                "Unsupported ChronoCore version"
            )


        if "repository" not in data:

            raise ValueError(
                "Missing repository data"
            )


        return True        