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


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        raise SystemExit("usage: python -m t2lgepa._t2l_shim <script> [args...]")

    from hyper_llm_modulator.utils import model_loading

    disable_flash_attn(model_loading)

    script, *rest = argv
    sys.argv = [script, *rest]
    runpy.run_path(script, run_name="__main__")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
