"""Smoke-test every version in a manifest through one OpenAI-compatible endpoint.

This is the call pattern the future web demo uses: pick a task, pick a version, compose the
prompt from the manifest, POST it, show the outputs side by side.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from t2lgepa.client import VLLMClient
from t2lgepa.data import Example
from t2lgepa.prompts import question_block

SAMPLES = {
    "gsm8k": {"question": "A box holds 6 pens. How many pens are in 7 boxes?",
              "answers": [], "answer": "42", "rationale": "6 * 7 = 42"},
    "arc_challenge": {"question": "Which object is the best conductor of electricity?",
                      "answers": ["A rubber hose", "A copper wire", "A wooden stick",
                                  "A plastic spoon"],
                      "answer": "B", "rationale": None},
    "boolq": {"question": "is copper a good conductor of electricity",
              "answers": [], "answer": "yes",
              "rationale": "Copper is a metal with many free electrons, so electric charge "
                           "moves through it easily. It is widely used for household wiring."},
    "hellaswag": {"question": "A chef puts a pan on the stove and adds oil. The oil begins to "
                              "shimmer, so the chef",
                  "answers": ["adds the vegetables to the pan.",
                              "pours the oil down the sink.",
                              "puts the pan in the freezer.",
                              "throws the pan away."],
                  "answer": "A", "rationale": None},
    "winogrande": {"question": "The trophy didn't fit in the suitcase because _ was too small.",
                   "answers": ["the trophy", "the suitcase"], "answer": "B", "rationale": None},
}


def sample_for(task: str) -> Example:
    raw = SAMPLES[task]
    return Example(id=f"demo:{task}", task=task, split="demo", **raw)


def prompt_for(version: dict, example: Example) -> str:
    prompt = version["prompt"]
    if not prompt.get("instruction"):
        raise ValueError(f"{version['version_id']} has no instruction; refusing to send a "
                         "different prompt recipe than the harness used")
    return "\n\n".join(part for part in (prompt.get("demo_block"), prompt["instruction"],
                                         question_block(example)) if part)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--base-url", default="http://localhost:8010")
    parser.add_argument("--out", default=None, help="write the raw outputs as JSON here")
    parser.add_argument("--max-tokens", type=int, default=512)
    args = parser.parse_args(argv)

    manifest = json.loads(Path(args.manifest).read_text())
    client = VLLMClient(args.base_url, manifest["model_id"],
                        adapters=[v["model"] for v in manifest["versions"]
                                  if v["model"] != manifest["model_id"]])
    client.assert_ready()

    outputs = {}
    for task in manifest["tasks"]:
        example = sample_for(task)
        versions = [v for v in manifest["versions"] if v["task"] == task]
        print(f"\n=== {task}: {example.question}")
        for version in versions:
            if not version.get("complete", False):
                print(f"  [{version['version_id']}] SKIPPED: incomplete run "
                      f"(partial={version.get('partial')}, "
                      f"adapter_present={version.get('adapter_present')})")
                outputs[version["version_id"]] = None
                continue
            text = client.generate([prompt_for(version, example)], model=version["model"],
                                   temperature=0.0, max_tokens=args.max_tokens)[0].text
            outputs[version["version_id"]] = text
            shown = text.strip().replace("\n", " | ")
            print(f"  [{version['version_id']}] {shown[:400]}")
    if args.out:
        Path(args.out).write_text(json.dumps(outputs, indent=2) + "\n")
        print(f"\nwrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
