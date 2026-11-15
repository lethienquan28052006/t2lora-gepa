"""Phase-1 validity gate.

smoke: 300 items, +-6pp, catches a broken pipeline.
full : all items,  +-3pp, the real validity check (SE is ~1.4pp at n=1319).

Exit code 0 means the harness reproduces the published T2L numbers on this model.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from t2lgepa.client import VLLMClient
from t2lgepa.config import load_config
from t2lgepa.data import make_splits
from t2lgepa.gate import check_gate
from t2lgepa.prompts import three_shot, zero_shot
from t2lgepa.runner import run_arm
from t2lgepa.t2l import lora_module_name


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=["smoke", "full"], required=True)
    parser.add_argument("--task", default="gsm8k")
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--config", default="configs/base.yaml")
    args = parser.parse_args(argv)

    cfg = load_config(args.config)
    adapter = lora_module_name(args.task)
    client = VLLMClient(args.base_url, cfg.model_id, adapters=[adapter])
    client.assert_ready()

    splits = make_splits(args.task, cache_dir=cfg.cache_dir)
    demos = splits.train[:3]
    limit = cfg.smoke_limit if args.mode == "smoke" else None
    tol = cfg.gate_tol_smoke_pp if args.mode == "smoke" else cfg.gate_tol_full_pp

    observed = {}
    for arm, model, prompt_fn in (
        ("base", cfg.model_id, zero_shot),
        ("t2l_icl", adapter, lambda ex: three_shot(ex, demos)),
    ):
        summary = run_arm(arm, args.task, 0, client, prompt_fn, model, cfg, limit=limit)
        observed[arm] = summary.score
        print(f"{arm:10s} {summary.score * 100:6.2f}%  (n={summary.n})")

    expected = {arm: cfg.expected[f"{args.task}/{arm}"] for arm in ("base", "t2l_icl")}
    ok, messages = check_gate(observed, expected, tol)
    print(f"\ngate [{args.mode}, tol ±{tol}pp]: {'PASS' if ok else 'FAIL'}")
    for message in messages:
        print(f"  - {message}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
