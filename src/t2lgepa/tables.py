"""Collect results/*.jsonl into the accuracy and cost rows used by both the CLI and the web app."""

from __future__ import annotations

import json
from pathlib import Path

from t2lgepa.analysis import paired_bootstrap, summarize
from t2lgepa.runner import read_summary


def _item_files(results_dir: Path):
    for path in sorted(results_dir.glob("*.jsonl")):
        if path.name.endswith((".generations.jsonl", ".curve.jsonl")):
            continue
        yield path


def collect(results_dir: str | Path) -> tuple[list[dict], list[dict]]:
    results_dir = Path(results_dir)
    accuracy: list[dict] = []
    cost: list[dict] = []
    items_by_arm: dict[tuple[str, str], dict[str, bool]] = {}
    for path in _item_files(results_dir):
        text = path.read_text().splitlines()
        if not text:
            continue
        summary = read_summary(path)
        if summary.get("record_type") != "summary":
            continue
        items = [json.loads(line) for line in text[1:] if line.strip()]
        score, lo, hi = summarize(items)
        accuracy.append(
            {"arm": summary["arm"], "task": summary["task"], "n": summary["n"],
             "score": score, "lo": lo, "hi": hi}
        )
        cost.append({**summary, "score": score})
        items_by_arm[(summary["arm"], summary["task"])] = {
            item["id"]: bool(item["correct"]) for item in items
        }

    for row in accuracy:
        base = items_by_arm.get(("base", row["task"]))
        if row["arm"] == "base" or base is None:
            row.update({"delta": None, "delta_lo": None, "delta_hi": None})
            continue
        mine = items_by_arm.get((row["arm"], row["task"]), {})
        shared = sorted(set(mine) & set(base))
        if not shared:
            row.update({"delta": None, "delta_lo": None, "delta_hi": None})
            continue
        left = [mine[i] for i in shared]
        right = [base[i] for i in shared]
        delta = sum(left) / len(left) - sum(right) / len(right)
        lo, hi = paired_bootstrap(left, right)
        row.update({"delta": delta, "delta_lo": lo, "delta_hi": hi})
    return accuracy, cost
