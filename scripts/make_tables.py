"""Build the accuracy and cost tables from results/*.jsonl."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from t2lgepa.analysis import accuracy_table, cost_table, summarize
from t2lgepa.runner import read_summary


def collect(results_dir: Path) -> tuple[list[dict], list[dict]]:
    accuracy, cost = [], []
    for path in sorted(results_dir.glob("*.jsonl")):
        if path.name.endswith(".generations.jsonl") or path.name.endswith(".curve.jsonl"):
            continue
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
    return accuracy, cost


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
