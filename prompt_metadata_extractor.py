import re
from typing import Optional, Dict, Tuple

# Defensive imports — these functions moved across ComfyUI versions
escape_important = None
unescape_important = None
token_weights = None

for _module_path in ("comfy.sd1_clip", "comfy.text_encoders.sd1_clip"):
    try:
        import importlib
        _mod = importlib.import_module(_module_path)
        escape_important = getattr(_mod, "escape_important", None)
        unescape_important = getattr(_mod, "unescape_important", None)
        token_weights = getattr(_mod, "token_weights", None)
        if escape_important is not None:
            break
    except (ImportError, ModuleNotFoundError):
        continue

if escape_important is None:
    print("[ComfyUI-Chrono-Saver] Warning: Could not import clip tokenizer functions. Using basic embedding/lora extraction.")
    def escape_important(text: str) -> str:
        return text
    def unescape_important(text: str) -> str:
        return text
    def token_weights(text: str, default_weight: float):
        return [(text, default_weight)]

from .utils import full_embedding_path_for, full_lora_path_for, get_sha256
from .utils_civitai import civitai_embedding_key_name, civitai_lora_key_name

class PromptMetadataExtractor:
    EMBEDDING: str = r'embedding:([^,\s\(\)\:]+)'
    LORA: str = r'<lora:([^>:]+)(?::([^>]+))?>'

    def __init__(self, positive_prompt: Optional[str] = None, negative_prompt: Optional[str] = None) -> None:
        self.__embeddings: Dict[str, Tuple[str, float, str]] = {}
        self.__loras: Dict[str, Tuple[str, float, str]] = {}
        self.__perform(positive_prompt, negative_prompt)

    def get_embeddings(self) -> Dict[str, Tuple[str, float, str]]:
        """Returns embeddings used in the prompts in CivitAI format."""
        return self.__embeddings

    def get_loras(self) -> Dict[str, Tuple[str, float, str]]:
        """Returns LoRA models used in the prompts in CivitAI format."""
        return self.__loras

    def __perform(self, positive_prompt: Optional[str], negative_prompt: Optional[str]) -> None:
        # Process positive prompt if it exists
        if positive_prompt and isinstance(positive_prompt, str):
            parsed = ((unescape_important(value), weight) for value, weight in token_weights(escape_important(positive_prompt), 1.0))
            for text, weight in parsed:
                embeddings = re.findall(self.EMBEDDING, text, re.IGNORECASE | re.MULTILINE)
                for embedding in embeddings:
                    self.__extract_embedding_information(embedding, weight)
                loras = re.findall(self.LORA, text, re.IGNORECASE | re.MULTILINE)
                for lora in loras:
                    self.__extract_lora_information(lora)

        # Process negative prompt if it exists
        if negative_prompt and isinstance(negative_prompt, str):
            parsed = ((unescape_important(value), weight) for value, weight in token_weights(escape_important(negative_prompt), 1.0))
            for text, weight in parsed:
                embeddings = re.findall(self.EMBEDDING, text, re.IGNORECASE | re.MULTILINE)
                for embedding in embeddings:
                    self.__extract_embedding_information(embedding, weight)
                loras = re.findall(self.LORA, text, re.IGNORECASE | re.MULTILINE)
                for lora in loras:
                    self.__extract_lora_information(lora)

    def __extract_embedding_information(self, embedding: str, weight: float) -> None:
        from .utils_civitai import civitai_embedding_key_name
        from .utils import full_embedding_path_for, get_sha256
        embedding_name = civitai_embedding_key_name(embedding)
        embedding_path = full_embedding_path_for(embedding)
        if embedding_path is None:
            return
        sha = get_sha256(embedding_path)[:10]
        self.__embeddings[embedding_name] = (embedding_path, weight, sha)

    def __extract_lora_information(self, lora: Tuple[str, str]) -> None:
        from .utils_civitai import civitai_lora_key_name
        from .utils import full_lora_path_for, get_sha256
        lora_name = civitai_lora_key_name(lora[0])
        lora_path = full_lora_path_for(lora[0])
        if lora_path is None:
            return
        try:
            lora_weight = float(lora[1].split(':')[0]) if lora[1] else 1.0
        except (ValueError, TypeError, IndexError):
            lora_weight = 1.0
        sha = get_sha256(lora_path)[:10]
        self.__loras[lora_name] = (lora_path, lora_weight, sha)

    def __get_shortened_sha(self, file_path: str) -> str:
        return get_sha256(file_path)[:10]