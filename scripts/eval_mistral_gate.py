"""Evaluate the finished Mistral grid against gates G2 (direction) and G3 (magnitude).

    uv run python scripts/eval_mistral_gate.py --results /data/quan.lt/temp/t2l-mistral/results
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from t2lgepa.mistral_gate import full_failures
from t2lgepa.tables import collect

PUBLISHED_MEAN = 0.126


def deltas(rows: list[dict]) -> dict[str, float]:
    return {
        row["task"]: row["delta"]
        for row in rows
        if row["arm"] == "t2l_icl" and row.get("delta") is not None
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", default="/data/quan.lt/temp/t2l-mistral/results")
    parser.add_argument("--published-mean", type=float, default=PUBLISHED_MEAN)
    parser.add_argument("--tol-pp", type=float, default=10.0)
    args = parser.parse_args(argv)

    rows, _ = collect(Path(args.results))
    observed = deltas(rows)
    if not observed:
        print(f"no t2l_icl results under {args.results}")
        return 1
    for task, delta in sorted(observed.items()):
        print(f"{task:14s} {delta * 100:+6.1f}pp")
    mean = sum(observed.values()) / len(observed)
    print(f"{'mean':14s} {mean * 100:+6.1f}pp  (published {args.published_mean * 100:+.1f}pp)")

    failures = full_failures(observed, published_mean=args.published_mean, tol_pp=args.tol_pp)
    if failures:
        print("\nGATE FAILED:")
        for failure in failures:
            print(f"  - {failure}")
        return 1
    print("\nG2 pass  G3 pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
