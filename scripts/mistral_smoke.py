"""Smoke driver: 4 arms x 5 tasks on a slice, with the adapter-collapse gate.

Run against a live server:

    uv run python scripts/mistral_smoke.py --config configs/mistral.yaml --limit 100

Exit code 1 means at least one adapter looks collapsed (or the arms disagree wildly);
do not start the full grid in that state.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from t2lgepa.client import VLLMClient
from t2lgepa.config import Config, load_config
from t2lgepa.data import make_splits
from t2lgepa.mistral_gate import smoke_failures
from t2lgepa.prompts import three_shot, zero_shot
from t2lgepa.runner import run_arm
from t2lgepa.t2l import lora_module_name

TASKS = ("gsm8k", "arc_challenge", "boolq", "hellaswag", "winogrande")
ARMS = ("base", "icl3", "t2l", "t2l_icl")


def render(scores: dict[str, dict[str, float]]) -> tuple[str, list[str]]:
    lines = [f"| {'task':14s} | " + " | ".join(f"{a:>7s}" for a in ARMS) + " |"]
    lines.append("|" + "|".join(["---"] * (len(ARMS) + 1)) + "|")
    for task in TASKS:
        if task not in scores:
            continue
        row = " | ".join(f"{scores[task].get(a, float('nan')) * 100:6.1f}%" for a in ARMS)
        lines.append(f"| {task:14s} | {row} |")
    base = {task: scores[task]["base"] for task in scores if "base" in scores[task]}
    adapter = {task: scores[task]["t2l"] for task in scores if "t2l" in scores[task]}
    return "\n".join(lines), smoke_failures(base, adapter)


def run(cfg: Config, client: VLLMClient, limit: int, out_dir: Path) -> int:
    out_dir.mkdir(parents=True, exist_ok=True)
    scores: dict[str, dict[str, float]] = {}
    for task in cfg.tasks:
        splits = make_splits(task, cache_dir=cfg.cache_dir)
        demos = splits.train[:3]
        adapter = lora_module_name(task)
        scores[task] = {}
        for arm in ARMS:
            model = adapter if arm.startswith("t2l") else cfg.model_id
            prompt_fn = zero_shot if arm in ("base", "t2l") else (lambda ex: three_shot(ex, demos))
            summary = run_arm(arm, task, cfg.seeds[0], client, prompt_fn, model, cfg,
                              limit=limit, results_dir=out_dir)
            scores[task][arm] = summary.score
    text, failures = render(scores)
    print(text)
    if failures:
        print("\nG1 FAILED:")
        for failure in failures:
            print(f"  - {failure}")
        return 1
    print("\nG1 passed: every adapter is alive.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/mistral.yaml")
    parser.add_argument("--base-url", default="http://localhost:8010")
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args(argv)

    cfg = load_config(args.config)
    limit = args.limit if args.limit is not None else cfg.smoke_limit
    client = VLLMClient(args.base_url, cfg.model_id,
                        adapters=[lora_module_name(t) for t in cfg.tasks])
    client.assert_ready()
    return run(cfg, client, limit, Path(cfg.results_dir) / "smoke")


if __name__ == "__main__":
    raise SystemExit(main())
