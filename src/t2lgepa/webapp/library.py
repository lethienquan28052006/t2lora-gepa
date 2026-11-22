"""Read-only access to the real GEPA prompt history shown by the demo."""

from __future__ import annotations

import json
from pathlib import Path

TASKS = ("gsm8k", "arc_challenge", "boolq", "hellaswag", "winogrande")
SEARCHED_ARMS = ("gepa_3shot", "t2l_gepa_opt")


def _instruction(path: Path) -> str:
    text = path.read_text()
    return text.removesuffix("\n")


class PromptLibrary:
    def __init__(self, results_dir: str | Path) -> None:
        self.results_dir = Path(results_dir)

    def history(self, task: str, arm: str, seed: int = 0) -> dict:
        if task not in TASKS:
            raise ValueError(f"unknown task {task!r}")
        if arm not in SEARCHED_ARMS:
            raise ValueError(f"arm {arm!r} has no stored prompt history")
        stem = self.results_dir / f"{arm}_{task}_s{seed}"
        seed_path = Path(f"{stem}_seed_prompt.txt")
        best_path = Path(f"{stem}_best_prompt.txt")
        candidates_path = Path(f"{stem}_candidates.json")
        if not (seed_path.exists() and best_path.exists() and candidates_path.exists()):
            raise ValueError(f"no stored prompt history for {arm}/{task}")

        seed_text = _instruction(seed_path)
        best_text = _instruction(best_path)
        candidates = json.loads(candidates_path.read_text())
        curve_path = Path(f"{stem}.curve.jsonl")
        curve = [json.loads(line) for line in curve_path.read_text().splitlines()
                 if line.strip()] if curve_path.exists() else []
        rendered_path = Path(f"{stem}_rendered_example.txt")
        return {
            "task": task,
            "arm": arm,
            "seed": seed_text,
            "best": best_text,
            "unchanged": seed_text == best_text,
            "best_index": next((c["index"] for c in candidates
                                if c.get("instruction") == best_text), None),
            "candidates": candidates,
            "curve": curve,
            "rendered_example": _instruction(rendered_path) if rendered_path.exists() else None,
        }
