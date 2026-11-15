"""Three-surface demo: base vs base+LoRA vs base+GEPA-prompt, one hosted model."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

if __package__ in (None, ""):
    from t2lgepa.config import load_config
    from t2lgepa.serve import BASE_URL_DEFAULT, gepa_prompt_from_curve, run_all
else:  # pragma: no cover
    from .config import load_config
    from .serve import BASE_URL_DEFAULT, gepa_prompt_from_curve, run_all


def format_report(prompts: list[str], outputs: dict[str, list[str]]) -> str:
    blocks = []
    for i, prompt in enumerate(prompts):
        blocks.append(f"Question: {prompt}")
        for surface in ("base", "t2l", "gepa"):
            answer = outputs[surface][i].strip()
            blocks.append(f"  [{surface}] {answer}")
        blocks.append("")
    return "\n".join(blocks)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--question", action="append", default=[],
                        help="repeatable; defaults to two GSM8K-style questions")
    parser.add_argument("--config", default="configs/base.yaml")
    parser.add_argument("--base-url", default=BASE_URL_DEFAULT)
    parser.add_argument("--results", default="results")
    parser.add_argument("--gepa-prompt-file", default=None)
    args = parser.parse_args(argv)

    cfg = load_config(args.config)
    questions = args.question or [
        "Janet has 3 apples and buys 4 more. How many apples does she have?",
        "A box holds 12 pens. 5 are removed. How many pens remain?",
    ]
    gepa_prompt = (
        Path(args.gepa_prompt_file).read_text().strip()
        if args.gepa_prompt_file
        else gepa_prompt_from_curve(Path(args.results))
    )
    outputs = run_all(questions, cfg, gepa_prompt=gepa_prompt, base_url=args.base_url)
    print(format_report(questions, outputs))
    if gepa_prompt:
        print("GEPA prompt in use:\n" + gepa_prompt)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
