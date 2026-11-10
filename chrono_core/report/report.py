class WorkflowReport:

    def __init__(self):

        self.data = {}
        self.metrics = {}


    def add(
        self,
        key,
        value
    ):

        self.data[key] = value


    def metric(
        self,
        key,
        value
    ):

        self.metrics[key] = value


    def get(
        self,
        key,
        default=None
    ):

        return self.data.get(
            key,
            default
        )


    def __getitem__(
        self,
        key
    ):

        return self.data[key]


    def to_dict(self):

        result = dict(self.data)

        result["metrics"] = self.metrics

        return result


    def metrics_dict(self):

        return self.metrics


    @classmethod
    def from_dict(
        cls,
        data
    ):

        report = cls()

        report.data = data

        return report