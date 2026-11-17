"""Write the demo vLLM config: same five adapters, memory sized for a public page."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import yaml


def build(root: Path, model: str, gpu_util: float, max_model_len: int, port: int) -> dict:
    modules = [
        json.dumps({"name": f"t2l_{d.name}", "path": str(d)})
        for d in sorted((root / "loras").iterdir())
        if d.is_dir()
    ]
    return {
        "model": model,
        "served_model_name": "mistralai/Mistral-7B-Instruct-v0.2",
        "enable_lora": True,
        "max_lora_rank": 64,
        "lora_modules": modules,
        "gpu_memory_utilization": gpu_util,
        "max_model_len": max_model_len,
        "port": port,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default="/data/quan.lt/temp/t2l-mistral")
    parser.add_argument(
        "--model",
        default="/mnt/home/quan.lt/dev/t2lora-gepa/models/mistral-7b-instruct-v0.2",
    )
    parser.add_argument("--gpu-util", type=float, default=0.35)
    parser.add_argument("--max-model-len", type=int, default=4096)
    parser.add_argument("--port", type=int, default=8010)
    args = parser.parse_args(argv)

    root = Path(args.root)
    config = build(root, args.model, args.gpu_util, args.max_model_len, args.port)
    out = root / "serve_demo.yaml"
    out.write_text(yaml.safe_dump(config, sort_keys=False))
    print(f"wrote {out} with {len(config['lora_modules'])} adapters")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
