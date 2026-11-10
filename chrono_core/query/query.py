class WorkflowQuery:

    def __init__(self, history):

        self.history = history


    def latest(self):

        return self.history.latest()


    def report(self):

        snapshot = self.latest()

        if snapshot is None:
            return None

        return snapshot.report


    def section(
        self,
        name,
        default=None
    ):

        report = self.report()

        if report is None:
            return default

        return report.get(
            name,
            default
        )


    def samplers(self):

        sampler = self.section(
            "sampler",
            {}
        )

        if not sampler:
            return []

        return [sampler]


    def models(self):

        model = self.section(
            "model",
            {}
        )

        if not model:
            return []

        return [model]


    def loras(self):

        return self.section(
            "loras",
            []
        )


    def prompts(self):

        return self.section(
            "prompts",
            {}
        )


    def conditioning(self):

        return self.section(
            "conditioning",
            {}
        )


    def dependencies(self):

        return self.section(
            "dependencies",
            {}
        )


    def statistics(self):

        return self.section(
            "statistics",
            {}
        )