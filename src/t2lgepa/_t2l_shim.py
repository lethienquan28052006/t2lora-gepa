"""Run the vendored Text-to-LoRA generator with CPU-friendly attention.

The vendor code hard-codes `attn_implementation="flash_attention_2"` for the base model.
On a host without flash-attn (or when generating on CPU) that fails, so we flip the
default of `get_model_and_tokenizer` before importing the generator.

Usage (same arguments as `generate_lora.py`):
    python -m t2lgepa._t2l_shim scripts/generate_lora.py <checkpoint_dir> "<description>"
"""

from __future__ import annotations

import runpy
import sys
from types import ModuleType


def disable_flash_attn(module: ModuleType) -> None:
    fn = module.get_model_and_tokenizer
    defaults = list(fn.__defaults__)
    defaults[0] = False
    fn.__defaults__ = tuple(defaults)


def filter_peft_config(config: dict, allowed: set[str]) -> dict:
    """Drop keys the installed (older) peft does not accept.

    The released checkpoints were saved with a newer peft, whose `adapter_config.json`
    carries fields such as `corda_config` and `megatron_config`. Older peft refuses them
    with a TypeError even though every dropped field is inert for inference.
    """
    return {key: value for key, value in config.items() if key in allowed}


def tolerate_newer_peft_configs() -> None:
    import inspect

    import peft
    from peft import LoraConfig

    allowed = set(inspect.signature(LoraConfig.__init__).parameters)
    original = peft.get_peft_config

    def wrapper(config, *args, **kwargs):
        if isinstance(config, dict):
            config = filter_peft_config(config, allowed)
        return original(config, *args, **kwargs)

    peft.get_peft_config = wrapper
    if hasattr(peft, "mapping"):
        peft.mapping.get_peft_config = wrapper
    # modules that did `from peft import get_peft_config` before this patch keep a direct
    # reference to the original; rebind it so they see the filtered version too.
    import sys

    for module in list(sys.modules.values()):
        for attr in ("get_peft_config", "_get_peft_config"):
            if getattr(module, attr, None) is original:
                setattr(module, attr, wrapper)


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        raise SystemExit("usage: python -m t2lgepa._t2l_shim <script> [args...]")

    from hyper_llm_modulator.utils import model_loading

    disable_flash_attn(model_loading)
    tolerate_newer_peft_configs()

    script, *rest = argv
    sys.argv = [script, *rest]
    runpy.run_path(script, run_name="__main__")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
