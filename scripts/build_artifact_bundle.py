"""Build the versioned artifact bundle (adapters + prompts + results + manifest + tarball)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from t2lgepa.bundle import VERSIONS, build_bundle, make_tarball
from t2lgepa.config import load_config
from t2lgepa.data import make_splits


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/mistral.yaml")
    parser.add_argument("--run-dir", required=True, help="results directory of the finished run")
    parser.add_argument("--lora-root", default="/data/quan.lt/temp/t2l-mistral/loras")
    parser.add_argument("--out", required=True, help="bundle directory, e.g. .../mistral-7b-v1")
    parser.add_argument("--tarball", default=None, help="defaults to <out>.tar.gz")
    args = parser.parse_args(argv)

    cfg = load_config(args.config)
    run_dir = Path(args.run_dir)
    demos = {task: make_splits(task, cache_dir=cfg.cache_dir).train[:3] for task in cfg.tasks}
    out = build_bundle(run_dir, Path(args.lora_root), Path(args.out), cfg.model_id,
                       list(cfg.tasks), demos, cfg.max_eval_items)
    tarball = make_tarball(out, Path(args.tarball) if args.tarball else out.with_suffix(".tar.gz"))

    import json

    manifest = json.loads((out / "manifest.json").read_text())
    incomplete = [v["version_id"] for v in manifest["versions"] if not v["complete"]]
    print(f"bundle: {out}")
    print(f"tarball: {tarball} ({tarball.stat().st_size / 1e6:.1f} MB)")
    print(f"versions: {len(manifest['versions'])} "
          f"({len(VERSIONS)} methods x {len(cfg.tasks)} tasks)")
    if incomplete:
        print(f"INCOMPLETE versions: {incomplete}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
