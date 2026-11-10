from ..graph.graph import Graph


class ModelExtractor:

    MODEL_LOADERS = (
        "CheckpointLoaderSimple",
        "CheckpointLoader",
    )

    DIFFUSION_LOADERS = (
        "UNETLoader",
    )


    def extract(self, graph: Graph):

        # -----------------------------------------
        # Старый SD/SDXL workflow
        # -----------------------------------------

        node = graph.find_first_type(
            *self.MODEL_LOADERS
        )

        if node is not None:
            return {
                "type": node.class_type,
                "checkpoint": node.get_input(
                    "ckpt_name"
                ),
            }


        # -----------------------------------------
        # Новый workflow:
        #
        # UNETLoader
        # LoraLoaderModelOnly
        # ModelSamplingAuraFlow
        #
        # -----------------------------------------

        node = graph.find_first_type(
            *self.DIFFUSION_LOADERS
        )

        if node is not None:
            return {
                "type": node.class_type,
                "checkpoint": None,
                "unet": node.get_input(
                    "unet_name"
                ),
            }


        return None