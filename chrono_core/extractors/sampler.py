from ..graph.graph import Graph


class SamplerExtractor:
    """
    Извлекает параметры sampler.
    Поддерживает:
    - KSampler
    - KSamplerAdvanced
    - SamplerCustomAdvanced pipeline
    """

    def extract(self, graph: Graph):

        # -------------------------------------------------
        # Старый ComfyUI pipeline
        # -------------------------------------------------

        node = graph.find_first_type(
            "KSampler",
            "KSamplerAdvanced"
        )

        if node is not None:
            return {
                "type": node.class_type,
                "seed": node.get_input("seed"),
                "steps": node.get_input("steps"),
                "cfg": node.get_input("cfg"),
                "sampler": node.get_input("sampler_name"),
                "scheduler": node.get_input("scheduler"),
                "denoise": node.get_input("denoise"),
            }


        # -------------------------------------------------
        # Новый pipeline:
        #
        # RandomNoise
        #      |
        # SamplerCustomAdvanced
        #
        # BasicScheduler -> SamplerCustomAdvanced
        #
        # CFGGuider
        #
        # KSamplerSelect
        # -------------------------------------------------

        custom = graph.find_first_type(
            "SamplerCustomAdvanced"
        )

        if custom is None:
            return None


        noise = graph.find_first_type(
            "RandomNoise"
        )

        scheduler = graph.find_first_type(
            "BasicScheduler"
        )

        guider = graph.find_first_type(
            "CFGGuider"
        )

        sampler_select = graph.find_first_type(
            "KSamplerSelect"
        )


        return {
            "type": "SamplerCustomAdvanced",

            "seed":
                noise.get_input("noise_seed")
                if noise else None,

            "steps":
                scheduler.get_input("steps")
                if scheduler else None,

            "cfg":
                guider.get_input("cfg")
                if guider else None,

            "sampler":
                sampler_select.get_input("sampler_name")
                if sampler_select else None,

            "scheduler":
                scheduler.class_type
                if scheduler else None,

            "denoise":
                None,
        }