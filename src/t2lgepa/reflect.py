"""Reflection-model credentials.

GEPA's reflection LM may live behind an OpenAI-compatible API instead of a local vLLM
server (the user's opencode provider, for example). The key is never stored in this repo:
it comes from an environment variable, or from the opencode config the user already has.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

OPENCODE_CONFIG = Path.home() / ".config/opencode/opencode.jsonc"


def _strip_jsonc(text: str) -> str:
    text = re.sub(r"(?m)^\s*//.*$", "", text)
    return re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)


def opencode_api_key(provider: str = "bioturing", path: Path | None = None) -> str | None:
    config_path = Path(path) if path is not None else OPENCODE_CONFIG
    try:
        data = json.loads(_strip_jsonc(config_path.read_text()))
    except (OSError, json.JSONDecodeError):
        return None
    block = data.get("providers", {}).get(provider, {})
    settings = block.get("settings", {}) if isinstance(block, dict) else {}
    key = settings.get("apiKey")
    return key if isinstance(key, str) and key else None


def resolve_key(cfg, provider: str = "bioturing") -> str | None:
    env_key = os.environ.get(cfg.reflection_api_key_env)
    if env_key:
        return env_key
    return opencode_api_key(provider)
