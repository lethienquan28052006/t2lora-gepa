"""Build the accuracy and cost tables from results/*.jsonl."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from t2lgepa.analysis import accuracy_table, cost_table
from t2lgepa.tables import collect


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", default="results")
    parser.add_argument("--out", default="docs/report")
    args = parser.parse_args(argv)

    accuracy, cost = collect(Path(args.results))
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "accuracy.md").write_text(accuracy_table(accuracy) + "\n")
    (out / "cost.md").write_text(cost_table(cost) + "\n")
    print(accuracy_table(accuracy))
    print()
    print(cost_table(cost))
    if not accuracy:
        print(f"\nno summaries found under {args.results}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
