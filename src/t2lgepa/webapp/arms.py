"""Prompt construction for the four adaptation methods shown on the demo page."""

from __future__ import annotations

from t2lgepa.config import Config
from t2lgepa.data import Example
from t2lgepa.gepa_arm import _compose
from t2lgepa.prompts import demo_block, three_shot, zero_shot

ARMS: tuple[str, ...] = ("base", "t2l_icl", "gepa_3shot", "t2l_gepa_opt")
SEARCHED_ARMS = ("gepa_3shot", "t2l_gepa_opt")


def build_prompt(
    arm: str, example: Example, demos: list[Example], gepa_prompt: str | None
) -> str:
    if arm == "base":
        return zero_shot(example)
    if arm == "t2l_icl":
        return three_shot(example, demos)
    if arm in SEARCHED_ARMS:
        if not gepa_prompt:
            raise ValueError(f"no stored {arm} prompt for this task")
        return _compose(gepa_prompt, example, demo_block(demos) if demos else None)
    raise ValueError(f"unknown arm {arm!r}")


def model_for(arm: str, task: str, cfg: Config) -> str:
    if arm.startswith("t2l"):
        return f"t2l_{task}"
    return cfg.model_id
