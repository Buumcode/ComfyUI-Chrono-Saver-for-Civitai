from typing import Any
from PIL.PngImagePlugin import PngInfo
from PIL.Image import Image
import json
import piexif
import piexif.helper
import copy


# Основная функция save_image()
def save_image(
    image: Image,
    filepath: str,
    extension: str,
    quality_jpeg_or_webp: int,
    lossless_webp: bool,
    optimize_png: bool,
    prompt: dict[str, Any] | None,
    extra_pnginfo: dict[str, Any] | None,
    embed_workflow: bool,
    civitai_resources: list[dict[str, Any]] | None = None,
    extra_metadata: dict | None = None,
) -> None:
    """Сохраняет изображение с метаданными."""

    # Сохраняем PNG
    if extension == 'png':

        metadata = PngInfo()

        # ----------------------------------------------------
        # Режим 1: Embedded workflow (ComfyUI native)
        # ----------------------------------------------------
        if embed_workflow:

            # prompt ComfyUI modified with urn:air
            if prompt is not None:
                metadata.add_text(
                    "prompt",
                    json.dumps(prompt)
                )

            # оригинальный workflow ComfyUI
            if embed_workflow and extra_pnginfo:
                for k, v in extra_pnginfo.items():
                    metadata.add_text(
                        k,
                        json.dumps(v)
                    )


        # ----------------------------------------------------
        # Режим 2: A1111 parameters only
        # ----------------------------------------------------
        else:

            if extra_metadata:

                prompt_text = extra_metadata.get("prompt", "")
                negative = extra_metadata.get("negativePrompt", "")
                steps = extra_metadata.get("steps", "")
                sampler = extra_metadata.get("sampler", "")
                cfg = extra_metadata.get("cfgScale", "")
                seed = extra_metadata.get("seed", "")
                width = extra_metadata.get("width")
                height = extra_metadata.get("height")
                denoise = extra_metadata.get("denoise")

                resources_data = copy.deepcopy(
                    extra_metadata.get("resources", [])
                )

                for r in resources_data:
                    if r.get("type"):
                        r["type"] = r["type"].lower()

                    if "strength" in r:
                        r["weight"] = r.pop("strength")

                resources = json.dumps(
                    resources_data,
                    separators=(",", ":")
                )

                size = (
                    f"{width}x{height}"
                    if width is not None and height is not None
                    else "unknown"
                )

                parameters = (
                    f"{prompt_text}\n"
                    f"Negative prompt: {negative}\n"
                    f"Steps: {steps}, "
                    f"Sampler: {sampler}, "
                    f"CFG scale: {cfg}, "
                    f"Seed: {seed}, "
                    f"Size: {size}, "
                    f"Denoising strength: {denoise}, "
                    f"Civitai resources: {resources}"
                )

                metadata.add_text(
                    "parameters",
                    parameters
                )

        exif = None

        image.save(
            filepath,
            pnginfo=metadata,
            exif=exif,
            optimize=optimize_png
        )

    # ---------------------------------------------------------
    # EXIF для JPEG
    # ---------------------------------------------------------
    elif extension in ("jpg", "jpeg"):

        # -----------------------------------------------------
        # embed_workflow = True
        #
        # Полностью повторяем механизм ExtendedSaveImage:
        #
        # UserComment (0x9286):
        # {
        #     "prompt": civitai_prompt,
        #     "workflow": original_workflow
        # }
        # -----------------------------------------------------
        if embed_workflow and extra_pnginfo and isinstance(extra_pnginfo, dict):

            # ---------------------------------------------------------
            # Формируем Civitai/A1111-style Parameters.
            # Это НЕ должно находиться вне JSON.
            # ---------------------------------------------------------

            parameters = ""

            if extra_metadata:
                prompt_text = extra_metadata.get("prompt", "")
                negative = extra_metadata.get("negativePrompt", "")
                steps = extra_metadata.get("steps", "")
                sampler = extra_metadata.get("sampler", "")
                cfg = extra_metadata.get("cfgScale", "")
                seed = extra_metadata.get("seed", "")
                width = extra_metadata.get("width")
                height = extra_metadata.get("height")
                denoise = extra_metadata.get("denoise")

                resources_data = copy.deepcopy(
                    extra_metadata.get("resources", [])
                )

                for r in resources_data:
                    if r.get("type"):
                        r["type"] = r["type"].lower()

                    if "strength" in r:
                        r["weight"] = r.pop("strength")

                resources = json.dumps(
                    resources_data,
                    separators=(",", ":")
                )

                size = (
                    f"{width}x{height}"
                    if width is not None and height is not None
                    else "unknown"
                )

                parameters = (
                    f"{prompt_text}\n"
                    f"Negative prompt: {negative}\n"
                    f"Steps: {steps}, "
                    f"Sampler: {sampler}, "
                    f"CFG scale: {cfg}, "
                    f"Seed: {seed}, "
                    f"Size: {size}, "
                    f"Denoising strength: {denoise}, "
                    f"Civitai resources: {resources}"
                )

            # ---------------------------------------------------------
            # ВАЖНО:
            # весь UserComment остаётся одним валидным JSON.
            # ---------------------------------------------------------

            exif_data = {
                "prompt": prompt,
                "workflow": extra_pnginfo.get("workflow", {}),
                "civitai_resources": civitai_resources,
            }

            imgexif = image.getexif()

            # ComfyUI workflow — оставляем в UserComment
            imgexif[0x9286] = json.dumps(exif_data)

            # A1111/Civitai parameters — отдельное EXIF-поле
            imgexif[0x010E] = parameters

            image.save(
                filepath,
                exif=imgexif,
                optimize=True,
                quality=quality_jpeg_or_webp,
                lossless=lossless_webp,
            )
            return

        # -----------------------------------------------------
        # embed_workflow = False
        #
        # Оставляем уже работающий A1111 UserComment.
        # -----------------------------------------------------
        elif not embed_workflow and extra_metadata:
            parameters = ""

            prompt_text = extra_metadata.get("prompt", "")
            negative = extra_metadata.get("negativePrompt", "")
            steps = extra_metadata.get("steps", "")
            sampler = extra_metadata.get("sampler", "")
            cfg = extra_metadata.get("cfgScale", "")
            seed = extra_metadata.get("seed", "")
            width = extra_metadata.get("width", image.width)
            height = extra_metadata.get("height", image.height)
            denoise = extra_metadata.get("denoisingStrength", "")

            size = f"{width}x{height}"

            resources_data = extra_metadata.get("resources", [])
            resources = []

            for resource in resources_data:
                resource_copy = resource.copy()
                if "type" in resource_copy:
                    resource_copy["type"] = resource_copy["type"].lower()
                if "strength" in resource_copy:
                    resource_copy["weight"] = resource_copy.pop("strength")
                resources.append(resource_copy)

            parameters = (
                f"{prompt_text}\n"
                f"Negative prompt: {negative}\n"
                f"Steps: {steps}, "
                f"Sampler: {sampler}, "
                f"CFG scale: {cfg}, "
                f"Seed: {seed}, "
                f"Size: {size}, "
                f"Denoising strength: {denoise}, "
                f"Civitai resources: {json.dumps(resources, separators=(',', ':'))}"
            )

            image.save(
                filepath,
                optimize=True,
                quality=quality_jpeg_or_webp,
            )

            exif_dict = {"Exif": {}}
            exif_dict["Exif"][piexif.ExifIFD.UserComment] = (
                piexif.helper.UserComment.dump(parameters, encoding="unicode")
            )

            exif_bytes = piexif.dump(exif_dict)

            MAX_EXIF_SIZE = 65535
            if len(exif_bytes) > MAX_EXIF_SIZE:
                print(
                    "Chrono-Image-Saver: Warning: EXIF too large. "
                    "Skipping EXIF insertion."
                )
                return

            if exif_bytes:
                piexif.insert(exif_bytes, filepath)
                

    # ---------------------------------------------------------
    # Сохранение WebP с метаданными
    # ---------------------------------------------------------
    elif extension == "webp":
        imgexif = image.getexif()

        if embed_workflow:
            # Синтетический Civitai prompt.
            # EXIF tag 0x0110 — Model.
            if prompt is not None:
                imgexif[0x0110] = (
                    "prompt:" + json.dumps(prompt)
                )

            # Оригинальный workflow.
            # EXIF tag 0x010F — Make.
            if extra_pnginfo:
                tag = 0x010F

                for key, value in extra_pnginfo.items():
                    imgexif[tag] = (
                        f"{key}:{json.dumps(value)}"
                    )
                    tag -= 1

            image.save(
                filepath,
                exif=imgexif,
                quality=quality_jpeg_or_webp,
                lossless=lossless_webp,
            )

        # -----------------------------------------------------
        # EmbedWorkflow=False: синтетический Parameters
        # -----------------------------------------------------
        elif extra_metadata:
            prompt_text = extra_metadata.get("prompt", "")
            negative = extra_metadata.get("negativePrompt", "")
            steps = extra_metadata.get("steps", "")
            sampler = extra_metadata.get("sampler", "")
            cfg = extra_metadata.get("cfgScale", "")
            seed = extra_metadata.get("seed", "")
            width = extra_metadata.get("width", image.width)
            height = extra_metadata.get("height", image.height)
            denoise = extra_metadata.get(
                "denoisingStrength",
                extra_metadata.get("denoise", "")
            )

            size = f"{width}x{height}"

            resources_data = copy.deepcopy(
                extra_metadata.get("resources", [])
            )

            for resource in resources_data:
                if resource.get("type"):
                    resource["type"] = resource["type"].lower()

                if "strength" in resource:
                    resource["weight"] = resource.pop("strength")

            parameters = (
                f"{prompt_text}\n"
                f"Negative prompt: {negative}\n"
                f"Steps: {steps}, "
                f"Sampler: {sampler}, "
                f"CFG scale: {cfg}, "
                f"Seed: {seed}, "
                f"Size: {size}, "
                f"Denoising strength: {denoise}, "
                f"Civitai resources: "
                f"{json.dumps(resources_data, separators=(',', ':'))}"
            )

            # Сначала сохраняем WebP без метаданных.
            image.save(
                filepath,
                quality=quality_jpeg_or_webp,
                lossless=lossless_webp,
            )

            # Затем записываем Parameters в EXIF UserComment.
            exif_dict = {"Exif": {}}
            exif_dict["Exif"][piexif.ExifIFD.UserComment] = (
                piexif.helper.UserComment.dump(
                    parameters,
                    encoding="unicode"
                )
            )

            exif_bytes = piexif.dump(exif_dict)

            MAX_EXIF_SIZE = 65535
            if len(exif_bytes) > MAX_EXIF_SIZE:
                print(
                    "Chrono-Image-Saver: Warning: EXIF too large. "
                    "Skipping EXIF insertion."
                )
                return

            if exif_bytes:
                piexif.insert(exif_bytes, filepath)

        else:
            # Нет дополнительных метаданных — сохраняем изображение.
            image.save(
                filepath,
                quality=quality_jpeg_or_webp,
                lossless=lossless_webp,
            )
