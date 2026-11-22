"""Long-lived adapter generator.

Loading the hypernetwork costs ~16s; generating one adapter costs ~0.04s once warm. A search
that proposes dozens of descriptions therefore needs this process to stay up, reading one JSON
request per line and answering with one JSON line.

    python scripts/adapter_worker.py --checkpoint .../hypermod.pt --out /data/.../candidates

stdin:  {"id": "d3", "description": "..."}
stdout: {"id": "d3", "path": "/data/.../candidates/d3", "seconds": 0.04}
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

VENDOR = Path(__file__).resolve().parents[1] / "vendor/text-to-lora"
sys.path.insert(0, str(VENDOR / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))


def load_generator(checkpoint: str, device: str = "cuda"):
    """Load the frozen T2L hypernetwork and everything it needs. Returns a generate() callable."""
    import torch
    from hyper_llm_modulator.utils import model_loading
    from peft import PeftConfig

    from t2lgepa._t2l_shim import disable_flash_attn, tolerate_newer_peft_configs

    disable_flash_attn(model_loading)
    tolerate_newer_peft_configs()

    import peft
    from hyper_llm_modulator.hyper_modulator import load_hypermod_checkpoint, save_lora
    from hyper_llm_modulator.utils import embed_texts, get_layers

    checkpoint_dir = Path(checkpoint).parent
    peft_config = peft.get_peft_config(
        PeftConfig.from_json_file(str(checkpoint_dir / "adapter_config.json"))
    )
    (
        _args,
        hypermod,
        model,
        _tokenizer,
        emb_model,
        emb_tokenizer,
        task_desc_format_fn,
        pooling_fn,
    ) = load_hypermod_checkpoint(checkpoint, device)

    layers = torch.tensor(
        range(len(get_layers(model))), dtype=torch.long, device=device
    )

    def generate(description: str, out_dir: str | Path) -> Path:
        started = time.perf_counter()
        with torch.no_grad():
            emb = embed_texts(
                [description], emb_model, emb_tokenizer, task_desc_format_fn, pooling_fn,
                torch.device(device),
            )
            encoded = hypermod.task_encoder(emb)["encoded_task_emb"].detach()
            state = hypermod.gen_lora(layers, encoded)
        dest = Path(out_dir)
        dest.mkdir(parents=True, exist_ok=True)
        save_lora(state, peft_config, str(dest))
        (dest / "task_desc.txt").write_text(description)
        _force_alpha_over_r_scaling(dest / "adapter_config.json")
        elapsed = time.perf_counter() - started
        (dest / "gen_seconds.txt").write_text(f"{elapsed:.3f}\n")
        return dest

    return generate


def _force_alpha_over_r_scaling(path: Path) -> None:
    config = json.loads(path.read_text())
    if config.get("use_rslora"):
        config["use_rslora"] = False
        path.write_text(json.dumps(config, indent=2))


def main(argv: list[str] | None = None) -> int:
    # the protocol is JSON lines on stdout; libraries chat on stdout too, so move them away
    protocol = sys.stdout
    sys.stdout = sys.stderr

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--device", default="cuda")
    args = parser.parse_args(argv)

    generate = load_generator(args.checkpoint, args.device)
    print(json.dumps({"ready": True}), file=protocol, flush=True)
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        request = json.loads(line)
        path = generate(request["description"], Path(args.out) / request["id"])
        seconds = float((path / "gen_seconds.txt").read_text())
        print(json.dumps({"id": request["id"], "path": str(path), "seconds": seconds}),
              file=protocol, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
