"""Write artifacts/serve_config.yaml with every generated LoRA module."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import yaml


def build(lora_root: Path, model: str, port: int, gpu_util: float = 0.55,
          max_model_len: int = 4096) -> dict:
    modules = [
        json.dumps({"name": f"t2l_{d.name}", "path": str(d)})
        for d in sorted(lora_root.iterdir())
        if d.is_dir()
    ]
    return {
        "model": model,
        "enable_lora": True,
        "max_lora_rank": 64,
        "lora_modules": modules,
        "gpu_memory_utilization": gpu_util,
        "max_model_len": max_model_len,
        "port": port,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lora-root", default="artifacts/t2l_loras")
    parser.add_argument("--model", default="unsloth/gemma-2-2b-it")
    parser.add_argument("--port", type=int, default=8010)
    parser.add_argument("--out", default="artifacts/serve_config.yaml")
    parser.add_argument("--gpu-util", type=float, default=0.55)
    parser.add_argument("--max-model-len", type=int, default=4096)
    args = parser.parse_args(argv)

    config = build(Path(args.lora_root), args.model, args.port,
                   gpu_util=args.gpu_util, max_model_len=args.max_model_len)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(yaml.safe_dump(config, sort_keys=False))
    print(f"wrote {out} with {len(config['lora_modules'])} LoRA modules")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
