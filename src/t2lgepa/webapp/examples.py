"""Build concrete, read-only GEPA optimization stories from stored run artifacts."""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

_STORIES = (
    {
        "id": "gepa-arc-challenge",
        "task": "arc_challenge",
        "arm": "gepa_3shot",
        "baseline_arm": "icl3",
        "title": "GEPA develops an ARC science-answering protocol",
        "changes": [
            "Turns generic multiple-choice rules into a science-specific answering strategy.",
            "Adds concise reasoning and a standalone, exactly formatted final answer line.",
            "Adds checks for common scientific misconceptions and invalid answer options.",
        ],
    },
    {
        "id": "t2l-gepa-arc-challenge",
        "task": "arc_challenge",
        "arm": "t2l_gepa_opt",
        "baseline_arm": "t2l_icl",
        "title": "Adapter-aware GEPA sharpens ARC reasoning and formatting",
        "changes": [
            "Clarifies that the final unanswered question is the target, not the demonstrations.",
            "Adds scientific evidence checks and deliberate comparison of the alternatives.",
            "Prevents missing or malformed final answer lines with explicit corrective rules.",
        ],
    },
    {
        "id": "t2l-gepa-boolq",
        "task": "boolq",
        "arm": "t2l_gepa_opt",
        "baseline_arm": "t2l_icl",
        "title": "GEPA grounds BoolQ decisions in the passage",
        "changes": [
            "Restricts the decision to the final passage rather than earlier demonstrations.",
            "Separates direct textual support from outside world knowledge.",
            "Adds edge-case guidance and a one-word lowercase yes/no output contract.",
        ],
    },
    {
        "id": "t2l-gepa-hellaswag",
        "task": "hellaswag",
        "arm": "t2l_gepa_opt",
        "baseline_arm": "t2l_icl",
        "title": "GEPA refines how HellaSwag continuations are selected",
        "changes": [
            "Distinguishes wikiHow-style steps from ordinary narrative continuation.",
            "Prioritizes factual and logical fit over surface fluency or repeated wording.",
            "Adds elimination of irrelevant, contradictory and nonsensical options.",
        ],
    },
)

ItemLookup = Callable[[str, str], dict[str, Any] | None]


def _items(path: Path) -> dict[str, dict]:
    """Return the latest stored record per item ID, including resumed-run duplicates."""
    items: dict[str, dict] = {}
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            if not isinstance(row, dict):
                raise TypeError(f"non-object record in {path}")
            if row.get("record_type") == "item" and row.get("id"):
                items[row["id"]] = row
    return items


def _prompt(path: Path) -> str:
    return path.read_text(encoding="utf-8").removesuffix("\n")


class PromptExampleLibrary:
    def __init__(self, results_dir: str | Path, item_lookup: ItemLookup | None = None) -> None:
        self.results_dir = Path(results_dir)
        self.item_lookup = item_lookup
        self._cached: list[dict] | None = None

    def _lookup(self, task: str, example_id: str) -> dict[str, Any] | None:
        if self.item_lookup is None:
            return None
        try:
            return self.item_lookup(task, example_id)
        except (OSError, RuntimeError, ValueError):
            return None

    def _case(self, task: str, before: dict, after: dict) -> dict:
        item = self._lookup(task, after["id"])
        return {
            "id": after["id"],
            "question": item.get("question", after["question"]) if item else after["question"],
            "options": list(item.get("options", [])) if item else [],
            "passage": item.get("passage") if item else after.get("rationale"),
            "gold": item.get("gold", after["gold"]) if item else after["gold"],
            "before": {
                "text": before["text"], "pred": before.get("pred"), "correct": False,
            },
            "after": {
                "text": after["text"], "pred": after.get("pred"), "correct": True,
            },
        }

    def _story(self, definition: dict) -> dict | None:
        task, arm = definition["task"], definition["arm"]
        stem = self.results_dir / f"{arm}_{task}_s0"
        seed = _prompt(Path(f"{stem}_seed_prompt.txt"))
        best = _prompt(Path(f"{stem}_best_prompt.txt"))
        if seed == best:
            return None

        baseline_arm = definition["baseline_arm"]
        before = _items(self.results_dir / f"{baseline_arm}_{task}_s0.jsonl")
        after = _items(self.results_dir / f"{arm}_{task}_s0.jsonl")
        cases = [
            self._case(task, before[example_id], after[example_id])
            for example_id in sorted(after)
            if example_id in before
            and before[example_id].get("correct") is False
            and after[example_id].get("correct") is True
        ][:3]
        return {**definition, "changes": list(definition["changes"]),
                "seed": seed, "best": best, "cases": cases}

    def stories(self) -> list[dict]:
        if self._cached is None:
            stories = []
            for definition in _STORIES:
                try:
                    story = self._story(definition)
                except (OSError, UnicodeError, ValueError, TypeError, KeyError):
                    # A partial or corrupt run must not suppress healthy stories.
                    continue
                if story is not None:
                    stories.append(story)
            self._cached = stories
        return self._cached
