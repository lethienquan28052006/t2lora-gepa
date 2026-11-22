"""Version manifest + artifact bundle: everything a report or a version-switching demo needs."""

from __future__ import annotations

import hashlib
import json
import shutil
import tarfile
from pathlib import Path

from t2lgepa.data import Example
from t2lgepa.prompts import demo_block, rules_for
from t2lgepa.runner import read_summary
from t2lgepa.t2l import lora_module_name

# version_id, arm, human label — the four methods compared in the report.
VERSIONS = (
    ("v0-base", "base", "Base Mistral-7B (zero-shot)"),
    ("v1-t2l", "t2l_icl", "T2L adapter + fixed 3-shot prompt"),
    ("v2-gepa", "gepa_3shot", "GEPA-optimised prompt on the base model"),
    ("v3-t2l-gepa", "t2l_gepa_opt", "Frozen T2L adapter + GEPA-optimised prompt"),
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _summary(run_dir: Path, arm: str, task: str, seed: int) -> dict | None:
    path = run_dir / f"{arm}_{task}_s{seed}.jsonl"
    return read_summary(path) if path.exists() else None


def _read(path: Path) -> str | None:
    """The exact instruction text: `export_*` appended one newline, remove only that one."""
    if not path.exists():
        return None
    text = path.read_text()
    return text.removesuffix("\n")


def _partial(run_dir: Path, arm: str, task: str, seed: int) -> bool:
    """A budget-exhausted search falls back to the seed instruction: not an optimised version."""
    path = run_dir / f"{arm}_{task}_s{seed}.job.json"
    if not path.exists():
        return False
    return bool(json.loads(path.read_text()).get("partial", False))


def version_entry(run_dir: Path, version_id: str, arm: str, label: str, task: str,
                  model_id: str, demos: list[Example], max_eval_items: int,
                  seed: int = 0, adapter_present: bool | None = None) -> dict:
    """One demo-selectable version: what to call, what to send, and how well it did."""
    summary = _summary(run_dir, arm, task, seed)
    is_gepa = arm.startswith("gepa") or arm == "t2l_gepa_opt"
    best = _read(run_dir / f"{arm}_{task}_s{seed}_best_prompt.txt")
    few_shot = None if arm == "base" else demo_block(demos[:3])
    partial = _partial(run_dir, arm, task, seed)
    return {
        "version_id": f"{version_id}-{task}",
        "label": label,
        "arm": arm,
        "task": task,
        "model": lora_module_name(task) if arm.startswith("t2l") else model_id,
        "adapter": f"adapters/{task}" if arm.startswith("t2l") else None,
        "adapter_present": adapter_present if arm.startswith("t2l") else None,
        "partial": partial,
        "prompt": {
            "instruction": best if is_gepa else rules_for(task),
            "demo_block": few_shot,
            "seed_instruction": _read(run_dir / f"{arm}_{task}_s{seed}_seed_prompt.txt")
            if is_gepa else None,
            "files": {
                name: f"prompts/{arm}/{arm}_{task}_s{seed}_{suffix}"
                for name, suffix in (
                    ("best", "best_prompt.txt"), ("seed", "seed_prompt.txt"),
                    ("candidates", "candidates.json"), ("curve", "curve.jsonl"),
                    ("rendered_example", "rendered_example.txt"),
                )
                if (run_dir / f"{arm}_{task}_s{seed}_{suffix}").exists()
            },
        },
        "metrics": None if summary is None else {
            "n": summary["n"],
            "accuracy": summary["score"],
            "wall_seconds": summary.get("wall_seconds", 0.0),
            "generated_tokens": summary.get("generated_tokens", 0),
        },
        "complete": bool(summary and summary["n"] >= max_eval_items and not partial
                         and (best is not None if is_gepa else True)
                         and (adapter_present is not False if arm.startswith("t2l") else True)),
    }


def build_manifest(run_dir: Path, model_id: str, tasks: list[str],
                   demos: dict[str, list[Example]], max_eval_items: int,
                   run_id: str = "mistral-7b-v1", seed: int = 0,
                   adapter_map: dict[str, bool] | None = None) -> dict:
    versions = [
        version_entry(run_dir, vid, arm, label, task, model_id, demos[task], max_eval_items, seed,
                      adapter_present=(adapter_map or {}).get(task))
        for task in tasks for vid, arm, label in VERSIONS
    ]
    return {
        "run_id": run_id,
        "model_id": model_id,
        "seed": seed,
        "endpoint": {"path": "/v1/chat/completions", "protocol": "openai-compatible"},
        "decode": {"temperature": 0.0, "max_tokens": 512},
        "tasks": tasks,
        "versions": versions,
        "prompt_recipe": (
            "prompt = '\\n\\n'.join(p for p in [demo_block, instruction, "
            "'Question: ...\\nAnswer:'] if p); send as one user message to `model`."
        ),
    }


def arm_of(filename: str) -> str:
    """`t2l_gepa_opt_gsm8k_s0_best_prompt.txt` -> `t2l_gepa_opt` (longest arm wins)."""
    arms = [arm for _, arm, _ in VERSIONS] + ["icl3", "t2l", "t2l_gepa"]
    for arm in sorted(arms, key=len, reverse=True):
        if filename.startswith(f"{arm}_"):
            return arm
    return "misc"


def build_bundle(run_dir: Path, lora_root: Path, out_dir: Path, model_id: str,
                 tasks: list[str], demos: dict[str, list[Example]], max_eval_items: int,
                 run_id: str = "mistral-7b-v1") -> Path:
    """Collect prompts, adapters and raw results into one portable directory."""
    out_dir.mkdir(parents=True, exist_ok=True)
    for path in sorted(run_dir.iterdir()):
        if not path.is_file():
            continue
        if path.name.endswith(("_prompt.txt", "_candidates.json", "_rendered_example.txt",
                               ".curve.jsonl")):
            target = out_dir / "prompts" / arm_of(path.name)
        elif path.suffix in (".jsonl", ".json"):
            target = out_dir / "results"
        else:
            continue
        target.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target / path.name)
    for task in tasks:
        source = lora_root / task
        if source.is_dir():
            shutil.copytree(source, out_dir / "adapters" / task, dirs_exist_ok=True)
            config = json.loads((out_dir / "adapters" / task / "adapter_config.json").read_text())
            config["use_rslora"] = False
            (out_dir / "adapters" / task / "adapter_config.json").write_text(
                json.dumps(config, indent=2) + "\n")
    adapter_map = {task: (out_dir / "adapters" / task).is_dir() for task in tasks}
    manifest = build_manifest(run_dir, model_id, tasks, demos, max_eval_items, run_id,
                              adapter_map=adapter_map)
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    write_serve_config(out_dir, model_id, [t for t in tasks if adapter_map[t]])
    write_bundle_readme(out_dir, run_id)
    return out_dir


def write_serve_config(out_dir: Path, model_id: str, tasks: list[str], port: int = 8010) -> Path:
    """A self-contained vLLM config: base model id + the bundled adapters by relative path."""
    import yaml

    config = {
        "model": model_id,
        "served_model_name": model_id,
        "enable_lora": True,
        "max_lora_rank": 64,
        "lora_modules": [json.dumps({"name": lora_module_name(task),
                                     "path": f"./adapters/{task}"}) for task in tasks],
        "gpu_memory_utilization": 0.90,
        "max_model_len": 4096,
        "port": port,
    }
    path = out_dir / "serve_config.yaml"
    path.write_text(yaml.safe_dump(config, sort_keys=False))
    return path


def write_bundle_readme(out_dir: Path, run_id: str) -> Path:
    path = out_dir / "README.md"
    path.write_text(f"""# {run_id} artifact bundle

Contents: `manifest.json` (four demo versions per task), `adapters/<task>/` (LoRA weights),
`prompts/<arm>/` (seed, best, candidates, curve, rendered example), `results/` (per-item scores
and generations), `serve_config.yaml`.

## Serve

From this directory, with vLLM 0.31 installed:

```bash
vllm serve --config serve_config.yaml
```

The endpoint then serves the base model plus one `t2l_<task>` module per task.

## Call a version

`manifest.json` gives, per version, the `model` to name in the request and the exact
`prompt.demo_block` + `prompt.instruction`. Compose
`demo_block + instruction + question block`, joined by blank lines, and POST it as one user
message with temperature 0.

## Smoke test

```bash
python scripts/demo_smoke.py --manifest manifest.json --base-url http://localhost:8010
```
""")
    return path


def make_tarball(bundle_dir: Path, tarball: Path) -> Path:
    with tarfile.open(tarball, "w:gz") as archive:
        archive.add(bundle_dir, arcname=bundle_dir.name)
    (tarball.with_suffix(tarball.suffix + ".sha256")).write_text(
        f"{sha256(tarball)}  {tarball.name}\n")
    return tarball
