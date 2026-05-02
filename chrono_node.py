"""
Chrono Save for Civitai — auto-extracts all generation metadata from the workflow.
Only 'images' needs to be connected. Everything else is parsed from the hidden
prompt JSON that ComfyUI always provides.

Strategy: scan ALL nodes for known field names with direct (non-link) values,
then trace connections backwards to find checkpoint/model names.
"""

import os
import json
import re
from datetime import datetime
from typing import Any, Optional
from collections import deque

import numpy as np
from PIL import Image
import torch

import folder_paths

from .saver.saver import save_image
from .utils import sanitize_filename, get_sha256, full_checkpoint_path_for
from .utils_civitai import get_civitai_sampler_name, get_civitai_metadata, MAX_HASH_LENGTH
from .prompt_metadata_extractor import PromptMetadataExtractor


# ---------------------------------------------------------------------------
# Workflow Auto-Extractor  (generic — scans all nodes)
# ---------------------------------------------------------------------------

# Known field names for each metadata type.
# We scan every node and pick up direct (non-link) values.
SEED_FIELDS = ("seed", "noise_seed")
STEPS_FIELDS = ("steps",)
CFG_FIELDS = ("cfg", "cfg_scale", "guidance")
SAMPLER_FIELDS = ("sampler_name",)
SCHEDULER_FIELDS = ("scheduler",)
DENOISE_FIELDS = ("denoise",)
WIDTH_FIELDS = ("width", "empty_latent_width")
HEIGHT_FIELDS = ("height", "empty_latent_height")

# Checkpoint / model loader class_types
CHECKPOINT_TYPES = {
    "CheckpointLoaderSimple", "CheckpointLoader",
    "UNETLoader", "UnetLoaderGGUF",
}

CKPT_NAME_FIELDS = ("ckpt_name", "unet_name")


def _is_direct_value(v) -> bool:
    """True if v is a direct value (not a node link). Links are [node_id, output_index]."""
    return not isinstance(v, list)


def _first_direct(prompt: dict, field_names: tuple, default=None):
    """Scan all nodes for the first direct (non-link) value matching any of the field names."""
    for nid, node in prompt.items():
        inputs = node.get("inputs", {})
        for fname in field_names:
            if fname in inputs and _is_direct_value(inputs[fname]):
                return inputs[fname]
    return default


def _all_direct(prompt: dict, field_names: tuple) -> list:
    """Collect all direct values matching field names across all nodes."""
    results = []
    for nid, node in prompt.items():
        inputs = node.get("inputs", {})
        for fname in field_names:
            if fname in inputs and _is_direct_value(inputs[fname]):
                results.append((nid, inputs[fname]))
    return results


def _find_checkpoint_name(prompt: dict) -> str:
    """Find the checkpoint/model name by scanning ALL nodes for ckpt_name/unet_name fields."""
    for nid, node in prompt.items():
        inputs = node.get("inputs", {})
        for fname in CKPT_NAME_FIELDS:
            if fname in inputs and _is_direct_value(inputs[fname]):
                val = str(inputs[fname])
                if val and val.lower() != "none":
                    return val
    return ""


def _find_lora_info(prompt: dict) -> list:
    """
    Find all LoRA names + strengths from the workflow.
    Supports: LoraLoader, LoraLoaderModelOnly, Power Lora Loader (rgthree),
    LoRA Stacker, easy loraStack, and any node with lora_name field.
    Returns list of (lora_name, strength_model, strength_clip).
    """
    loras = []
    seen_names = set()

    for nid, node in prompt.items():
        ct = node.get("class_type", "")
        inputs = node.get("inputs", {})

        # Standard LoraLoader / LoraLoaderModelOnly
        if "lora_name" in inputs and _is_direct_value(inputs.get("lora_name")):
            name = str(inputs["lora_name"])
            if name and name != "None" and name not in seen_names:
                sm = inputs.get("strength_model", 1.0)
                sc = inputs.get("strength_clip", 1.0)
                sm = sm if _is_direct_value(sm) else 1.0
                sc = sc if _is_direct_value(sc) else 1.0
                loras.append((name, float(sm), float(sc)))
                seen_names.add(name)

        # Power Lora Loader (rgthree) — dynamic inputs like lora_1, lora_2, ...
        # Each value is a dict: {"on": True, "lora": "filename.safetensors", "strength": 0.9}
        if "rgthree" in ct.lower() or "power" in ct.lower() or "lora" in ct.lower():
            for key, val in inputs.items():
                if key.startswith("lora_") and isinstance(val, dict):
                    if val.get("on", False) and val.get("lora"):
                        name = str(val["lora"])
                        if name and name != "None" and name not in seen_names:
                            strength = float(val.get("strength", 1.0))
                            loras.append((name, strength, strength))
                            seen_names.add(name)

        # easy loraStack / Lora Stacker — numbered lora inputs
        if "stack" in ct.lower() and "lora" in ct.lower():
            for key, val in inputs.items():
                if ("lora" in key.lower() and "name" in key.lower()
                    and _is_direct_value(val)):
                    name = str(val)
                    if name and name != "None" and name not in seen_names:
                        loras.append((name, 1.0, 1.0))
                        seen_names.add(name)

    return loras


def _find_clip_texts(prompt: dict) -> dict:
    """Find all CLIPTextEncode nodes and extract their text."""
    texts = {}
    for nid, node in prompt.items():
        if node.get("class_type") == "CLIPTextEncode":
            text = node.get("inputs", {}).get("text", "")
            if isinstance(text, str):
                texts[nid] = text
            elif isinstance(text, list):
                texts[nid] = _follow_text_link(text, prompt)
    return texts


def _follow_text_link(link, prompt, depth=0) -> str:
    """Follow a node link to resolve a text value."""
    if depth > 5 or not isinstance(link, list) or len(link) < 1:
        return ""
    nid = str(link[0])
    node = prompt.get(nid, {})
    inputs = node.get("inputs", {})
    for key in ("text", "string", "text_positive", "text_negative", "value",
                "text_g", "text_l", "prompts_text"):
        if key in inputs:
            val = inputs[key]
            if isinstance(val, str):
                return val
            if isinstance(val, list):
                return _follow_text_link(val, prompt, depth + 1)
    return ""


def _trace_to_clip_text(start_nid: str, prompt: dict, clip_texts: dict) -> str:
    """BFS from a node backwards to find CLIPTextEncode text."""
    if start_nid in clip_texts:
        return clip_texts[start_nid]

    visited = set()
    queue = deque([start_nid])

    while queue:
        nid = queue.popleft()
        if nid in visited:
            continue
        visited.add(nid)

        if nid in clip_texts:
            return clip_texts[nid]

        node = prompt.get(nid, {})
        for val in node.get("inputs", {}).values():
            if isinstance(val, list) and len(val) >= 1:
                next_nid = str(val[0])
                if next_nid not in visited:
                    queue.append(next_nid)

        if len(visited) > 50:
            break

    return ""


def _find_prompts(prompt: dict) -> tuple:
    """Find positive and negative prompt text from the workflow."""
    clip_texts = _find_clip_texts(prompt)
    positive = ""
    negative = ""

    # Look for any node that has both "positive" and "negative" conditioning inputs
    for nid, node in prompt.items():
        inputs = node.get("inputs", {})

        pos_ref = inputs.get("positive")
        neg_ref = inputs.get("negative")

        if isinstance(pos_ref, list) and not positive:
            found = _trace_to_clip_text(str(pos_ref[0]), prompt, clip_texts)
            if found:
                positive = found

        if isinstance(neg_ref, list) and not negative:
            found = _trace_to_clip_text(str(neg_ref[0]), prompt, clip_texts)
            if found:
                negative = found

        if positive and negative:
            break

    # Fallback: if no conditioning links found, just grab CLIPTextEncode texts by length
    if not positive and clip_texts:
        sorted_texts = sorted(clip_texts.values(), key=len, reverse=True)
        positive = sorted_texts[0] if sorted_texts else ""
        if len(sorted_texts) > 1:
            negative = sorted_texts[1]

    return positive, negative


def _extract_from_workflow(prompt: dict) -> dict:
    """Parse the ComfyUI workflow prompt to extract all generation parameters."""
    if not prompt:
        return {
            "positive": "", "negative": "", "modelname": "",
            "loras": [],
            "seed": 0, "steps": 20, "cfg": 7.0,
            "sampler_name": "", "scheduler_name": "normal",
            "width": 512, "height": 512, "denoise": 1.0,
        }

    positive, negative = _find_prompts(prompt)

    # Pick the best width/height — prefer larger values (actual generation size)
    all_widths = _all_direct(prompt, WIDTH_FIELDS)
    all_heights = _all_direct(prompt, HEIGHT_FIELDS)
    width = max((v for _, v in all_widths), default=512) if all_widths else 512
    height = max((v for _, v in all_heights), default=512) if all_heights else 512

    return {
        "positive": positive,
        "negative": negative,
        "modelname": _find_checkpoint_name(prompt),
        "loras": _find_lora_info(prompt),
        "seed": _first_direct(prompt, SEED_FIELDS, 0),
        "steps": _first_direct(prompt, STEPS_FIELDS, 20),
        "cfg": _first_direct(prompt, CFG_FIELDS, 7.0),
        "sampler_name": _first_direct(prompt, SAMPLER_FIELDS, ""),
        "scheduler_name": _first_direct(prompt, SCHEDULER_FIELDS, "normal"),
        "width": int(width),
        "height": int(height),
        "denoise": _first_direct(prompt, DENOISE_FIELDS, 1.0),
    }


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


def _parse_manual_hashes(additional_hashes: str, existing_hashes: set, download_civitai: bool):
    re_hash = re.compile(r'^\s*([^:]+?)(?:\s*:\s*([^\s:][^:]*?))?\s*$')
    re_hash_w = re.compile(r'^\s*([^:]+?)(?:\s*:\s*([^\s:][^:]*?))?(?:\s*:\s*([-+]?(?:\d+(?:\.\d*)?|\.\d+)))?\s*$')
    manual = {}
    unnamed = 0
    for entry in (additional_hashes.replace("\n", ",").split(",") if additional_hashes else []):
        m = (re_hash_w if download_civitai else re_hash).search(entry)
        if m is None:
            continue
        groups = tuple(g for g in m.groups() if g)
        weight = None
        if download_civitai and len(groups) > 1:
            try:
                weight = float(groups[-1])
                groups = groups[:-1]
            except (ValueError, TypeError):
                pass
        name, hash_val = groups if len(groups) > 1 else (None, groups[0])
        if len(hash_val) > MAX_HASH_LENGTH:
            continue
        if hash_val.lower() in existing_hashes:
            continue
        if name is None:
            unnamed += 1
            name = f"manual{unnamed}"
        manual[name] = (None, weight, hash_val)
        if len(manual) > 29:
            break
    return manual


# ---------------------------------------------------------------------------
# Node
# ---------------------------------------------------------------------------

class ChronoSaveForCivit:
    CATEGORY = "chrono-save-for-civit"
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
                "images":                ("IMAGE",),
                "filename_prefix":       ("STRING",  {"default": "%Y-%m-%d_Civitai",
                                                      "tooltip": "Supports strftime: %Y %m %d %H %M %S, plus %seed %model"}),
                "folder":                ("STRING",  {"default": "Zimage/%Y-%m-%d/Civitai/",
                                                      "tooltip": "Subfolder under ComfyUI output dir. Supports strftime."}),
                "file_format":           (["jpeg", "png", "webp"],),
                "quality":               ("INT",     {"default": 100, "min": 1, "max": 100}),
                "embed_workflow":        ("BOOLEAN", {"default": False,
                                                      "tooltip": "False = no workflow leak. True = embed workflow in image."}),
                "download_civitai_data": ("BOOLEAN", {"default": True,
                                                      "tooltip": "Fetch resource info from civitai.com for resource linking."}),
                "easy_remix":            ("BOOLEAN", {"default": True,
                                                      "tooltip": "Strip LoRAs from prompt for cleaner Civitai remix."}),
            },
            "optional": {
                "positive_override":     ("STRING",  {"default": "", "multiline": True, "forceInput": True,
                                                      "tooltip": "Override auto-detected positive prompt. Wire from Chrono Prompt Queue."}),
                "additional_hashes":     ("STRING",  {"default": "", "multiline": False,
                                                      "tooltip": "Extra resource hashes: 'Name:HASH' separated by commas."}),
            },
            "hidden": {
                "prompt": "PROMPT",
                "extra_pnginfo": "EXTRA_PNGINFO",
            },
        }

    def save_images(
        self,
        images,
        filename_prefix="%Y-%m-%d_Civitai",
        folder="Zimage/%Y-%m-%d/Civitai/",
        file_format="jpeg",
        quality=100,
        embed_workflow=False,
        download_civitai_data=True,
        easy_remix=True,
        positive_override="",
        additional_hashes="",
        prompt=None,
        extra_pnginfo=None,
    ):
        # --- Auto-extract metadata from workflow ---
        wf = _extract_from_workflow(prompt or {})

        positive = positive_override.strip() if positive_override.strip() else wf["positive"]
        negative = wf["negative"]
        modelname = wf["modelname"]
        seed = wf["seed"]
        steps = wf["steps"]
        cfg = wf["cfg"]
        sampler_name = wf["sampler_name"]
        scheduler_name = wf["scheduler_name"]
        width = wf["width"]
        height = wf["height"]

        # --- Resolve strftime in folder and filename ---
        resolved_folder = _resolve_strftime(folder).strip().rstrip("/")
        resolved_prefix = _resolve_strftime(filename_prefix)

        # --- Build Civitai-compatible metadata ---
        ckpt_path = full_checkpoint_path_for(modelname)
        modelhash = get_sha256(ckpt_path)[:10] if ckpt_path else ""

        # Extract loras/embeddings from prompt text (<lora:name:weight> format)
        extractor = PromptMetadataExtractor([positive, negative])
        embeddings = extractor.get_embeddings()
        prompt_loras = extractor.get_loras()

        # Also extract loras from workflow nodes (LoraLoader, Power Lora Loader, etc.)
        from .utils import full_lora_path_for
        from .utils_civitai import civitai_lora_key_name
        node_loras = {}
        for lora_name, strength_model, strength_clip in wf["loras"]:
            key = civitai_lora_key_name(os.path.splitext(os.path.basename(lora_name))[0])
            if key not in prompt_loras:  # Don't duplicate
                lora_path = full_lora_path_for(lora_name)
                if lora_path:
                    lora_hash = get_sha256(lora_path)[:10]
                    node_loras[key] = (lora_path, strength_model, lora_hash)

        # Merge: prompt-detected + node-detected loras
        loras = {**prompt_loras, **node_loras}

        display_sampler = get_civitai_sampler_name(
            sampler_name.replace("_gpu", ""), scheduler_name
        )
        basemodelname = _parse_ckpt_basename(modelname)

        existing_hashes = ({modelhash.lower()} |
                          {t[2].lower() for t in loras.values()} |
                          {t[2].lower() for t in embeddings.values()})
        manual_entries = _parse_manual_hashes(additional_hashes, existing_hashes, download_civitai_data)

        civitai_resources, hashes, add_model_hash = get_civitai_metadata(
            modelname, ckpt_path, modelhash, loras, embeddings, manual_entries, download_civitai_data
        )

        # Clean prompts for remix if requested
        pos_text = _clean_prompt(positive, extractor).strip() if easy_remix else positive.strip()
        neg_text = _clean_prompt(negative, extractor).strip() if easy_remix else negative.strip()

        # --- Build A1111-style parameters string ---
        model_hash_str = f", Model hash: {add_model_hash}" if add_model_hash else ""
        hashes_str = f', Hashes: {json.dumps(hashes, separators=(",",":"))}' if hashes else ""

        a111_params = (
            f"{pos_text}\n"
            f"Negative prompt: {neg_text}\n"
            f"Steps: {steps}, Sampler: {display_sampler}, CFG scale: {cfg}, "
            f"Seed: {seed}, Size: {width}x{height}"
            f"{model_hash_str}, Model: {basemodelname}{hashes_str}, Version: ComfyUI"
        )

        if download_civitai_data and civitai_resources:
            a111_params += f', Civitai resources: {json.dumps(civitai_resources, separators=(",",":"))}' 

        # Log what was detected
        print(f"\n{'='*60}")
        print(f"  CHRONO SAVE FOR CIVITAI — Auto-detected metadata:")
        print(f"  Model:     {basemodelname}")
        print(f"  Sampler:   {display_sampler}")
        print(f"  Steps:     {steps}  |  CFG: {cfg}  |  Seed: {seed}")
        print(f"  Size:      {width}x{height}")
        print(f"  Prompt:    {pos_text[:80]}{'...' if len(pos_text) > 80 else ''}")
        print(f"  Hash:      {modelhash}")
        print(f"  Hashes:    {hashes}")
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

            save_image(
                img, filepath, ext,
                quality, True, False,
                a111_params,
                prompt if embed_workflow else None,
                extra_pnginfo if embed_workflow else None,
                embed_workflow,
            )

            subfolder = os.path.normpath(resolved_folder) if resolved_folder else ""
            results.append({
                "filename": final_filename,
                "subfolder": subfolder if subfolder != "." else "",
                "type": "output",
            })

        return {"ui": {"images": results}}
