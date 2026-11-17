"""Write docs/report/cases.md from two arms' item records."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from t2lgepa.cases import pick_cases, render_cases


def load_items_file(path: Path) -> dict[str, dict]:
    items = {}
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if row.get("record_type") == "item":
            items[row["id"]] = row
    return items


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--a", required=True, help="path to the T2L arm jsonl")
    parser.add_argument("--b", required=True, help="path to the GEPA arm jsonl")
    parser.add_argument("--k", type=int, default=2)
    parser.add_argument("--out", default="docs/report/cases.md")
    args = parser.parse_args(argv)

    a = load_items_file(Path(args.a))
    b = load_items_file(Path(args.b))
    text = render_cases(pick_cases(a, b, k=args.k), a, b)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text)
    print(f"wrote {out} ({len(a & b.keys())} shared items)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
