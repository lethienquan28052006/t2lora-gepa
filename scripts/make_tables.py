"""Build the accuracy and cost tables from results/*.jsonl."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from t2lgepa.analysis import accuracy_table, cost_table, paired_bootstrap, summarize
from t2lgepa.runner import read_summary


def _item_files(results_dir: Path):
    for path in sorted(results_dir.glob("*.jsonl")):
        name = path.name
        if name.endswith((".generations.jsonl", ".curve.jsonl")):
            continue
        yield path


def collect(results_dir: Path) -> tuple[list[dict], list[dict]]:
    accuracy, cost, items_by_arm = [], [], {}
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
