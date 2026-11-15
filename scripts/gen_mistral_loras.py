"""Generate one T2L adapter per configured task.

    uv run python scripts/gen_mistral_loras.py --config configs/mistral.yaml \
        --out /data/quan.lt/temp/t2l-mistral/loras

Each adapter comes from the paper-time task description in
`configs/task_descriptions.yaml`; nothing is trained on our evaluation data.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from t2lgepa.config import Config, load_config
from t2lgepa.t2l import generate_lora


def main(argv: list[str] | None = None, cfg: Config | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/mistral.yaml")
    parser.add_argument("--out", default="/data/quan.lt/temp/t2l-mistral/loras")
    parser.add_argument("--tasks", default=None, help="comma separated subset")
    args = parser.parse_args(argv)

    cfg = cfg or load_config(args.config)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    tasks = args.tasks.split(",") if args.tasks else cfg.tasks
    for task in tasks:
        path = generate_lora(cfg, task, str(out_dir))
        print(f"{task}: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
