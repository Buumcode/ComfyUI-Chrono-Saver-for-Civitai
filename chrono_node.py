"""
Chrono Saver for Civitai — auto-extracts all generation metadata from the workflow.
Only 'images' needs to be connected. Everything else is parsed from the hidden
prompt JSON that ComfyUI always provides.

Strategy: scan ALL nodes for known field names with direct (non-link) values,
then trace connections backwards to find checkpoint/model names.
"""

import os
import json
import re
from datetime import datetime

import numpy as np
from PIL import Image
import torch

import folder_paths

from .saver.saver import save_image
from .utils import sanitize_filename, get_sha256, full_checkpoint_path_for
from .utils_civitai import get_civitai_sampler_name, get_civitai_metadata
from .prompt_metadata_extractor import PromptMetadataExtractor

from .chrono_core import Session


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _resolve_strftime(text: str) -> str:
    return datetime.now().strftime(text)


def _parse_ckpt_basename(ckpt_name: str) -> str:
    filename = os.path.basename(ckpt_name)
    name, ext = os.path.splitext(filename)
    supported = getattr(folder_paths, "supported_pt_extensions", set()) | {".gguf"}
    return name if ext.lower() in supported else filename


def _get_unique_filename(output_path: str, prefix: str, extension: str) -> str:
    existing = [f for f in os.listdir(output_path)
                if f.startswith(prefix) and f.endswith(extension)]
    if not existing:
        return prefix
    suffixes = []
    for f in existing:
        name, _ = os.path.splitext(f)
        parts = name.split("_")
        if parts[-1].isdigit():
            suffixes.append(int(parts[-1]))
    return f"{prefix}_{(max(suffixes) + 1) if suffixes else 1:04d}"


def _clean_prompt(prompt_text: str, extractor: PromptMetadataExtractor) -> str:
    from pathlib import Path
    prompt_text = re.sub(extractor.LORA, "", prompt_text)
    prompt_text = re.sub(extractor.EMBEDDING, lambda m: Path(m.group(1)).stem, prompt_text)
    prompt_text = re.sub(r'\b[A-Z]+\([^)]*\)', "", prompt_text)
    return prompt_text


def _metadata_scalar(value, default=0):
    """
    Convert Chrono Core multi-values into a harmless scalar.
    Used only for Civitai compatibility prompt.
    Real data remains in workflow chunk.
    """

    if isinstance(value, list):

        if not value:
            return default

        # берем первое найденное значение,
        # потому что metadata является декоративной
        return _metadata_scalar(value[0], default)

    if isinstance(value, tuple):

        if not value:
            return default

        return _metadata_scalar(value[0], default)

    return value        


def _normalize_air(air: str) -> str:
    """Normalize diffusionmodel AIRs to checkpoint AIRs."""
    air = (air or "").strip()
    return re.sub(
        r"^(urn:air:[a-z0-9._-]+:)diffusionmodel(:civitai:)",
        r"\1checkpoint\2",
        air,
        flags=re.IGNORECASE,
    )


def _parse_resource_airs(resources_to_keep: str) -> list[str]:
    """Extract complete AIR identifiers even if upstream collapses newlines."""
    pattern = (
        r"urn:air:[a-z0-9._-]+:[a-z0-9._-]+:civitai:\d+"
        r"(?:@\d+)?(?:\+\d+)?"
    )
    result = []
    seen = set()
    for match in re.finditer(pattern, resources_to_keep or "", flags=re.IGNORECASE):
        air = _normalize_air(match.group(0))
        key = air.lower()
        if key not in seen:
            seen.add(key)
            result.append(air)
    return result


def _air_resource_type(air: str) -> str:
    """Return the AIR's resource type segment, or an empty string if invalid."""
    match = re.match(
        r"^urn:air:[a-z0-9._-]+:([a-z0-9._-]+):civitai:\d+(?:@\d+)?(?:\+\d+)?$",
        (air or "").strip(),
        flags=re.IGNORECASE,
    )
    if not match:
        return ""
    kind = match.group(1).lower()
    return "checkpoint" if kind == "diffusionmodel" else kind


def _is_lora_air(air: str) -> bool:
    return _air_resource_type(air) == "lora"


def _is_checkpoint_air(air: str) -> bool:
    return _air_resource_type(air) == "checkpoint"


def _filter_civitai_resources(
    resources: list[dict],
    remove_all_loras: bool,
    resources_to_keep: str,
) -> list[dict]:
    """
    Filter metadata resources only.
    Preserve checkpoints and all non-LoRA resource types.
    """
    # Normalize every existing AIR regardless of whether LoRA filtering is enabled.
    normalized_resources = []
    for resource in resources:
        normalized = dict(resource)
        if normalized.get("air"):
            normalized["air"] = _normalize_air(normalized["air"])
        normalized_resources.append(normalized)

    if not remove_all_loras:
        return normalized_resources

    keep_airs = {air.lower() for air in _parse_resource_airs(resources_to_keep)}
    filtered = []

    for resource in normalized_resources:
        air = resource.get("air", "")

        if not _is_lora_air(air):
            filtered.append(resource)
            continue

        if air.lower() in keep_airs:
            filtered.append(resource)

    return filtered

def build_civitai_prompt(
    positive,
    negative,
    modelname,
    checkpoint_air,
    lora_entries,
    seed,
    steps,
    cfg,
    sampler_name,
    scheduler_name,
    denoise,
    width,
    height,
    checkpoint_airs=None,
):
    """
    Build a synthetic minimal ComfyUI prompt specifically for Civitai parsing.

    This prompt is NOT the real workflow.

    It contains:
      - checkpoint/model loader
      - CLIP text encode positive
      - CLIP text encode negative
      - optional LoRA chain
      - KSampler
      - EmptyLatentImage
      - VAEDecode
      - SaveImage

    Resource loader names are replaced by Civitai AIRs.
    """

    prompt = {}
    lora_entries = lora_entries or []

    # All checkpoint AIRs are represented in the synthetic metadata prompt.
    checkpoint_airs = checkpoint_airs or []
    if checkpoint_airs and not checkpoint_air:
        checkpoint_air = checkpoint_airs[0]

    width = _metadata_scalar(width, 0)
    height = _metadata_scalar(height, 0)
    seed = _metadata_scalar(seed, 0)
    steps = _metadata_scalar(steps, 0)
    cfg = _metadata_scalar(cfg, 0)

    sampler_name = _metadata_scalar(sampler_name, "unknown")
    scheduler_name = _metadata_scalar(scheduler_name, "unknown")

    # ---------------------------------------------------------
    # Fixed node IDs
    # ---------------------------------------------------------

    POSITIVE_ID = "6"
    VAE_DECODE_ID = "8"
    MODEL_ID = "29"
    SAVE_IMAGE_ID = "48"
    KSAMPLER_ID = "75"
    LATENT_ID = "76"
    NEGATIVE_ID = "90"

    # ---------------------------------------------------------
    # Positive prompt
    # ---------------------------------------------------------

    prompt[POSITIVE_ID] = {
        "inputs": {
            "text": str(positive or ""),
            "clip": ["85", 1],
        },
        "class_type": "CLIPTextEncode",
        "_meta": {
            "title": "CLIP Text Encode (Prompt)"
        },
    }

    # ---------------------------------------------------------
    # Negative prompt
    # ---------------------------------------------------------

    prompt[NEGATIVE_ID] = {
        "inputs": {
            "text": str(negative or ""),
            "clip": ["85", 1],
        },
        "class_type": "CLIPTextEncode",
        "_meta": {
            "title": "CLIP Text Encode (Prompt)"
        },
    }

    # ---------------------------------------------------------
    # Model loader
    # ---------------------------------------------------------

    if checkpoint_air:
        prompt[MODEL_ID] = {
            "inputs": {
                "ckpt_name": checkpoint_air,
            },
            "class_type": "CheckpointLoaderSimple",
            "_meta": {
                "title": "Load Checkpoint"
            },
        }

    else:
        # Fallback: retain original model name if Civitai AIR
        # could not be determined.
        prompt[MODEL_ID] = {
            "inputs": {
                "ckpt_name": modelname or "",
            },
            "class_type": "CheckpointLoaderSimple",
            "_meta": {
                "title": "Load Checkpoint"
            },
        }

    # ---------------------------------------------------------
    # Additional checkpoint loaders are intentionally disconnected from
    # generation. Civitai scans them to identify all declared resources.
    # ---------------------------------------------------------

    primary_air_key = (checkpoint_air or "").lower()
    extra_checkpoint_airs = []
    seen_checkpoint_airs = {primary_air_key} if primary_air_key else set()
    for air in checkpoint_airs:
        air = _normalize_air(air)
        key = air.lower()
        if not _is_checkpoint_air(air) or key in seen_checkpoint_airs:
            continue
        seen_checkpoint_airs.add(key)
        extra_checkpoint_airs.append(air)

    for index, air in enumerate(extra_checkpoint_airs, start=1):
        node_id = str(100 + index)
        prompt[node_id] = {
            "inputs": {"ckpt_name": air},
            "class_type": "CheckpointLoaderSimple",
            "_meta": {"title": f"Additional Checkpoint {index + 1}"},
        }

    # ---------------------------------------------------------
    # LoRA chain
    # ---------------------------------------------------------

    current_model_id = MODEL_ID
    current_clip_id = MODEL_ID

    lora_counter = 85

    for entry in lora_entries:
        lora = entry["lora"]
        air = entry["air"]

        if not air:
            continue

        node_id = str(lora_counter)
        lora_counter += 1

        strength_model = lora.get("strength_model", 1)
        strength_clip = lora.get("strength_clip")

        if strength_clip is None:
            strength_clip = strength_model

        prompt[node_id] = {
            "inputs": {
                "lora_name": air,
                "strength_model": strength_model,
                "strength_clip": strength_clip,
                "model": [current_model_id, 0],
                "clip": [current_clip_id, 1],
            },
            "class_type": "LoraLoader",
            "_meta": {
                "title": "Load LoRA (Model and CLIP)"
            },
        }    

        current_model_id = node_id
        current_clip_id = node_id

    # ---------------------------------------------------------
    # Reconnect CLIP encoders to the final LoRA
    # ---------------------------------------------------------

    prompt[POSITIVE_ID]["inputs"]["clip"] = [current_clip_id, 1]
    prompt[NEGATIVE_ID]["inputs"]["clip"] = [current_clip_id, 1]

    # ---------------------------------------------------------
    # Empty latent
    # ---------------------------------------------------------

    prompt[LATENT_ID] = {
        "inputs": {
            "width": int(width),
            "height": int(height),
            "batch_size": 1,
        },
        "class_type": "EmptyLatentImage",
        "_meta": {
            "title": "Empty Latent Image"
        },
    }

    # ---------------------------------------------------------
    # KSampler
    # ---------------------------------------------------------

    prompt[KSAMPLER_ID] = {
        "inputs": {
            "seed": int(seed),
            "steps": int(steps),
            "cfg": float(cfg),
            "sampler_name": sampler_name,
            "scheduler": scheduler_name,
            "denoise": float(denoise if denoise is not None else 1.0),
            "model": [current_model_id, 0],
            "positive": [POSITIVE_ID, 0],
            "negative": [NEGATIVE_ID, 0],
            "latent_image": [LATENT_ID, 0],
        },
        "class_type": "KSampler",
        "_meta": {
            "title": "KSampler"
        },
    }

    # ---------------------------------------------------------
    # VAE Decode
    #
    # For the first test we don't need to identify a real VAE.
    # The Civitai parser is primarily interested in the model,
    # LoRAs and generation parameters.
    # ---------------------------------------------------------

    prompt[VAE_DECODE_ID] = {
        "inputs": {
            "samples": [KSAMPLER_ID, 0],
            "vae": [MODEL_ID, 2],
        },
        "class_type": "VAEDecode",
        "_meta": {
            "title": "VAE Decode"
        },
    }

    # ---------------------------------------------------------
    # SaveImage
    # ---------------------------------------------------------

    prompt[SAVE_IMAGE_ID] = {
        "inputs": {
            "filename_prefix": "ComfyUI",
            "images": [VAE_DECODE_ID, 0],
        },
        "class_type": "SaveImage",
        "_meta": {
            "title": "Save Image"
        },
    }

    return prompt


def find_power_lora(workflow):
    loras = []

    if not isinstance(workflow, dict):
        return loras

    nodes = workflow.get("nodes", [])

    for node in nodes:

        if not isinstance(node, dict):
            continue

        node_type = node.get("type", "")

        if "Power Lora Loader" not in node_type:
            continue


        # Приоритет: widgets_values_named
        named = node.get("widgets_values_named", {})

        for key, item in named.items():

            if not key.startswith("lora_"):
                continue

            if not isinstance(item, dict):
                continue

            if not item.get("on", True):
                continue

            name = item.get("lora")

            if not name:
                continue

            loras.append({
                "name": name,
                "strength_model": item.get("strength", 1),
                "strength_clip": item.get("strengthTwo"),
            })


        # fallback для старых workflow
        if not named:

            widgets = node.get("widgets_values", [])

            for item in widgets:

                if not isinstance(item, dict):
                    continue

                if "lora" not in item:
                    continue

                if not item.get("on", True):
                    continue

                loras.append({
                    "name": item["lora"],
                    "strength_model": item.get("strength", 1),
                    "strength_clip": item.get("strengthTwo"),
                })


    return loras


def resolve_prompt_value(value, prompt):
    """
    Resolve ComfyUI link values:
    [node_id, output_index]
    into actual widget value.
    """

    if not isinstance(value, list):
        return value

    if len(value) != 2:
        return value

    node_id = str(value[0])

    node = prompt.get(node_id)

    if not node:
        return value


    inputs = node.get("inputs", {})


    # common primitive values

    for key in [
        "value",
        "int",
        "float",
        "number",
        "seed",
        "width",
        "height"
    ]:

        if key in inputs:
            return inputs[key]


    return value


# ---------------------------------------------------------------------------
# Node
# ---------------------------------------------------------------------------

class ChronoSaverForCivitai:
    CATEGORY = "chrono-saver-for-civitai"
    FUNCTION = "save_images"
    OUTPUT_NODE = True
    RETURN_TYPES = ()
    DESCRIPTION = (
        "Save images with Civitai-compatible metadata. Auto-extracts model, "
        "sampler, seed, prompts, etc. from the workflow. Only 'images' needs connecting."
    )

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "images":                           ("IMAGE",),
                "filename_prefix":                  ("STRING",  {"default": "%Y-%m-%d_%H-%M-%S_Civitai",
                                                      "tooltip": "Supports strftime: %Y %m %d %H %M %S, plus %seed %model"}),
                "folder":                           ("STRING",  {"default": "Krea2/%Y-%m-%d/Civitai/",
                                                      "tooltip": "Subfolder under ComfyUI output dir. Supports strftime %Y %m %d %H %M %S."}),
                "file_format":                      (["png", "jpeg", "webp"],),
                "quality":                          ("INT",     {"default": 85, "min": 1, "max": 100}),
                "embed_workflow":                   ("BOOLEAN", {"default": True,
                                                      "tooltip": "False = no workflow leak. True = embed workflow in image."}),
                "download_civitai_data":            ("BOOLEAN", {"default": True,
                                                      "tooltip": "Fetch resource info from Civitai.com for resource linking."}),
                "easy_remix":                       ("BOOLEAN", {"default": False,
                                                      "tooltip": "Strip <lora:example_lora:0.9> and SUBJECT1(deleted text) from prompt text."}),
                "remove_all_loras_from_resources":  ("BOOLEAN", {"default": False,"tooltip": "Remove all LoRA resources except AIRs listed in resources_to_keep."}),
            },
            "optional": {
                "positive_override":    ("STRING",  {"default": "", "multiline": True, "forceInput": True,
                                                      "tooltip": "Override auto-detected positive prompt. Wire from STRING output."}),
                "resources_to_keep":    ("STRING",  {"default": "", "multiline": True, "tooltip": "Civitai AIRs to include in metadata (LoRA, checkpoint, etc.), one AIR per line."}),
            },
            "hidden": {
                "prompt": "PROMPT",
                "extra_pnginfo": "EXTRA_PNGINFO",
            },
        }

    def save_images(
        self,
        images,
        filename_prefix="%Y-%m-%d_%H-%M-%S_Civitai",
        folder="Krea2/%Y-%m-%d/Civitai/",
        file_format="png",
        quality=85,
        embed_workflow=True,
        download_civitai_data=True,
        easy_remix=False,
        positive_override="",
        prompt=None,
        extra_pnginfo=None,
        remove_all_loras_from_resources=False,
        resources_to_keep="",
    ):

        # --- Auto-extract metadata from workflow ---
        from .chrono_core import Session

        session = Session(prompt or {})
        report = session.report.to_dict()
#       print(report)

        positive = positive_override.strip() if positive_override.strip() else report["prompts"]["positive"]
        negative = report["prompts"]["negative"]
        model_info = report.get("model") or {}

        modelname = (
            model_info.get("checkpoint")
            or model_info.get("unet")
            or ""
        )

        sampler = report.get("sampler") or {}

        seed = resolve_prompt_value(
            sampler.get("seed",0),
            prompt
        )
        steps = sampler.get("steps", 0)
        cfg = sampler.get("cfg", 0)
        sampler_name = sampler.get("sampler", "unknown")
        scheduler_name = sampler.get("scheduler", "unknown")
        denoise = sampler.get("denoise", None)

        # ---------------------------------------------------------
        # Image size — use the actual IMAGE tensor from ComfyUI
        #
        # ComfyUI IMAGE format:
        # [batch, height, width, channels]
        # ---------------------------------------------------------

        height = int(images.shape[1])
        width = int(images.shape[2])

        # ---------------------------------------------------------
        # Normalize decorative metadata values
        # ---------------------------------------------------------

        try:
            seed = int(seed)
        except (TypeError, ValueError):
            seed = 0

        try:
            steps = int(steps)
        except (TypeError, ValueError):
            steps = 0

        try:
            cfg = float(cfg)
        except (TypeError, ValueError):
            cfg = 0.0

        try:
            width = int(width)
        except (TypeError, ValueError):
            width = int(images[0].shape[2])

        try:
            height = int(height)
        except (TypeError, ValueError):
            height = int(images[0].shape[1])

        # --- Resolve strftime in folder and filename ---
        resolved_folder = _resolve_strftime(folder).strip().rstrip("/")
        resolved_prefix = _resolve_strftime(filename_prefix)

        # --- Build Civitai-compatible metadata ---
        ckpt_path = full_checkpoint_path_for(modelname)
        modelhash = get_sha256(ckpt_path)[:10] if ckpt_path else ""

        # Extract loras/embeddings from prompt text (<lora:name:weight> format)
        extractor = PromptMetadataExtractor(
            positive_prompt=str(positive) if positive is not None else None,
            negative_prompt=str(negative) if negative is not None else None
        )
        embeddings = extractor.get_embeddings()
        prompt_loras = extractor.get_loras()

        # Also extract loras from workflow nodes (LoraLoader, Power Lora Loader, etc.)
        from .utils import full_lora_path_for
        from .utils_civitai import civitai_lora_key_name

        node_loras = {}

        detected_loras = list(report["loras"])

        # fallback для Power Lora Loader (rgthree)
        workflow_data = {}

        if extra_pnginfo and isinstance(extra_pnginfo, dict):
            workflow_data = extra_pnginfo.get("workflow", {})

        power_loras = find_power_lora(workflow_data)

#       print("\n=== POWER LORAS ===")
#       for l in power_loras:
#           print(l)

        existing = {
            l["name"]
            for l in detected_loras
        }

        for lora in power_loras:
            if lora["name"] not in existing:
                detected_loras.append(lora)


        for lora in detected_loras:

            lora_path = full_lora_path_for(lora["name"])

            if lora_path is None:
                continue

            key = civitai_lora_key_name(
                os.path.splitext(os.path.basename(lora["name"]))[0]
            )

            node_loras[key] = (
                lora_path,
                lora.get("strength_model", 1),
                get_sha256(lora_path)[:10],
            )

        # Merge: prompt-detected + node-detected loras    
        loras = {**prompt_loras, **node_loras}

        display_sampler = get_civitai_sampler_name(
            sampler_name.replace("_gpu", ""), scheduler_name
        )        

        basemodelname = _parse_ckpt_basename(modelname)

        civitai_resources = get_civitai_metadata(
            modelname,
            ckpt_path,
            modelhash,
            loras,
            embeddings,
            {},
            download_civitai_data,
        )

        # ---------------------------------------------------------
        # Build a lookup of local LoRAs by SHA-256, matching the known-working
        # implementation. Civitai-discovered resources carry _local_hash;
        # manually supplied AIRs intentionally do not need a local file.
        # ---------------------------------------------------------

        local_loras_by_hash = {}

        for lora in detected_loras:
            lora_path = full_lora_path_for(lora["name"])
            if lora_path is None:
                continue
            lora_hash = get_sha256(lora_path)[:10].lower()
            local_loras_by_hash.setdefault(lora_hash, []).append(lora)

        # Filter resources for metadata only. The real workflow/generation is
        # untouched; non-LoRA resources are retained by the filter.
        metadata_resources = _filter_civitai_resources(
            civitai_resources,
            remove_all_loras_from_resources,
            resources_to_keep,
        )

        # Add every manually supplied AIR to saved metadata. AIRs can describe
        # LoRAs, checkpoints, or other resources; no local filename is required.
        manual_airs = _parse_resource_airs(resources_to_keep)
        existing_airs = {
            _normalize_air(str(resource.get("air", ""))).lower()
            for resource in metadata_resources
            if resource.get("air")
        }
        for air in manual_airs:
            normalized_air = _normalize_air(air)
            if normalized_air.lower() not in existing_airs:
                metadata_resources.append({"air": normalized_air, "weight": 1.0})
                existing_airs.add(normalized_air.lower())

        # Build synthetic-prompt LoRA entries using the previously working
        # hash match. If no unique local match exists, still include the AIR
        # with its metadata weight (default 1.0); do not require filenames.
        lora_entries = []
        for resource in metadata_resources:
            air = resource.get("air", "")
            if not air or not _is_lora_air(air):
                continue

            resource_hash = str(resource.get("_local_hash", "")).lower()[:10]
            matching_loras = local_loras_by_hash.get(resource_hash, [])

            if len(matching_loras) == 1:
                lora = matching_loras[0]
            else:
                weight = resource.get("weight", 1.0)
                lora = {
                    "name": air,
                    "strength_model": weight,
                    "strength_clip": weight,
                }

            lora_entries.append({"lora": lora, "air": air})

        # ---------------------------------------------------------
        # Find checkpoint AIR in the filtered resource list.
        # Checkpoints are preserved by the filter.
        # ---------------------------------------------------------

        checkpoint_air = next(
            (
                r.get("air")
                for r in metadata_resources
                if r.get("air")
                and _is_checkpoint_air(r["air"])
            ),
            None,
        )

        # Every checkpoint AIR included in metadata is also represented in the
        # synthetic Civitai prompt; extra loaders remain disconnected from generation.
        checkpoint_airs_for_prompt = [
            _normalize_air(r.get("air", ""))
            for r in metadata_resources
            if _is_checkpoint_air(r.get("air", ""))
        ]

        # ---------------------------------------------------------
        # Normalize LoRA weights in metadata.
        # ---------------------------------------------------------

        for entry in lora_entries:
            resource = next(
                (
                    r for r in metadata_resources
                    if r.get("air") == entry["air"]
                ),
                None,
            )

            if resource is None or "weight" in resource:
                continue

            resource["weight"] = entry["lora"].get(
                "strength_model", 1
            )

#       print("\n=== CIVITAI AIRs ===")

#       print(f"Checkpoint AIR: {checkpoint_air}")


#       print(f"Checkpoint AIR: {checkpoint_air}")

#       for index, air in enumerate(lora_airs, 1):
#           print(f"LoRA #{index}: {air}")


        # Normalize LoRA weights for Civitai workflow resources
        for resource in civitai_resources:
            if resource.get("air") and ":lora:" in resource["air"]:
                if "weight" not in resource:
                    version = resource["air"].split("@")[-1]

                    for lora in detected_loras:
                        if lora.get("strength_model") is not None:
                            resource["weight"] = lora["strength_model"]
                            break        

        exif_resources = []

        for resource in metadata_resources:
            air = resource.get("air")
            if not air:
                continue

            version_match = re.search(r"@(\d+)", air)
            if not version_match:
                continue
            version_id = int(version_match.group(1))

            if _is_lora_air(air):
                resource_type = "lora"
            elif _is_checkpoint_air(air):
                resource_type = "checkpoint"
            else:
                # Keep other AIR types in the workflow resources list, but do
                # not mislabel them as checkpoints in EXIF's typed resource list.
                continue

            exif_resources.append({
                "modelVersionId": version_id,
                "strength": resource.get("weight", 1),
                "type": resource_type,
            })

        airs = [
            resource["air"]
            for resource in metadata_resources
            if resource.get("air")
        ]

        # Clean prompts for remix if requested
        pos_text = _clean_prompt(
            positive,
            extractor
        ).strip() if easy_remix else positive.strip()

        neg_text = _clean_prompt(
            negative,
            extractor
        ).strip() if easy_remix else negative.strip()

        extra_metadata = {
            "prompt": pos_text,
            "negativePrompt": neg_text,

            "cfgScale": cfg,
            "steps": steps,
            "seed": seed,

            "sampler": display_sampler,
            "scheduler": scheduler_name,
            "denoise": denoise,

            "width": width,
            "height": height,

            "resources": exif_resources
        }

        # Log what was detected
        print(f"\n{'='*60}")
        print(f"  COMFYUI CHRONO SAVER FOR CIVITAI — Auto-detected metadata:")
        print(f"  Model:     {basemodelname}")
        print(f"  Sampler:   {display_sampler}")
        print(f"  Steps:     {steps}  |  CFG: {cfg}  |  Seed: {seed}")
        print(f"  Size:      {width}x{height}")
        print(f"  Prompt:    {pos_text[:80]}{'...' if len(pos_text) > 80 else ''}")
        print(f"  Hash:      {modelhash}")

        if airs:
            print(f"  AIRs:      {', '.join(airs)}")
        if loras:
            print(f"  LoRAs:     {len(loras)} detected: {', '.join(loras.keys())}")
        if civitai_resources:
            print(f"  Civitai:   {len(civitai_resources)} resource(s) detected")
        print(f"{'='*60}\n")

        # --- Filename substitutions ---
        resolved_prefix = resolved_prefix.replace("%seed", str(seed))
        resolved_prefix = resolved_prefix.replace("%model", basemodelname)

        # --- Save images ---
        output_dir = folder_paths.get_output_directory()
        full_output_path = os.path.join(output_dir, resolved_folder) if resolved_folder else output_dir
        os.makedirs(full_output_path, exist_ok=True)

        ext = "jpg" if file_format == "jpeg" else file_format
        results = []

        for idx, image in enumerate(images):
            i = 255.0 * image.cpu().numpy()
            img = Image.fromarray(np.clip(i, 0, 255).astype(np.uint8))

            unique_name = _get_unique_filename(full_output_path, resolved_prefix, ext)
            final_filename = f"{unique_name}.{ext}"
            filepath = os.path.join(full_output_path, final_filename)

            import copy

            # ------------------------------------------------------------
            # 1. Build synthetic Civitai prompt
            # ------------------------------------------------------------

            civitai_prompt = build_civitai_prompt(
                positive=pos_text,
                negative=neg_text,
                modelname=modelname,
                checkpoint_air=checkpoint_air,
                checkpoint_airs=checkpoint_airs_for_prompt,
                lora_entries=lora_entries,
                seed=seed,
                steps=steps,
                cfg=cfg,
                sampler_name=sampler_name,
                scheduler_name=scheduler_name,
                denoise=denoise,
                width=width,
                height=height,
            )

            # ------------------------------------------------------------
            # 2. Keep original ComfyUI workflow untouched
            # ------------------------------------------------------------

            workflow_pnginfo = {}

            if extra_pnginfo and isinstance(extra_pnginfo, dict):
                workflow_original = extra_pnginfo.get("workflow")

                if workflow_original is not None:
                    workflow_pnginfo["workflow"] = copy.deepcopy(workflow_original)

            save_image(
                img,
                filepath,
                ext,
                quality,
                True,
                False,

                civitai_prompt,       # PNG chunk: prompt
                workflow_pnginfo,     # PNG chunk: workflow, ORIGINAL

                embed_workflow,
                metadata_resources,
                extra_metadata,
            )

            subfolder = os.path.normpath(resolved_folder) if resolved_folder else ""
            results.append({
                "filename": final_filename,
                "subfolder": subfolder if subfolder != "." else "",
                "type": "output",
            })

        return {"ui": {"images": results}}            