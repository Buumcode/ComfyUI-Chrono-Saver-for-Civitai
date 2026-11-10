class AIRExtractor:

    def extract(self, graph, resources):

        airs = []

        for r in resources:

            if r["type"] == "checkpoint":
                airs.append(
                    r["air"]
                )

            elif r["type"] == "lora":
                airs.append(
                    r["air"]
                )

        return airs