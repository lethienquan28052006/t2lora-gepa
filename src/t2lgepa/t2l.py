"""Thin wrapper around the vendored Text-to-LoRA generator."""

from __future__ import annotations

import re
import shutil
import subprocess
import time
from pathlib import Path

import yaml

from t2lgepa.config import Config

VENDOR_DIR = Path("vendor/text-to-lora")
DESCRIPTIONS = Path("configs/task_descriptions.yaml")
_SAVED = re.compile(r"Saved lora to\s+(\S+)")


class T2LError(RuntimeError):
    pass


def describe_task(task: str) -> str:
    table = yaml.safe_load(DESCRIPTIONS.read_text())
    return table[task]


def lora_module_name(task: str) -> str:
    return f"t2l_{task}"


def _run(cmd: list[str], cfg: Config) -> str:
    log = Path(cfg.results_dir) / "t2l_generate.log"
    log.parent.mkdir(parents=True, exist_ok=True)
    started = time.time()
    proc = subprocess.run(
        cmd,
        cwd=str(VENDOR_DIR),
        capture_output=True,
        text=True,
        check=False,
        env={
            **_env(cfg),
            "CUDA_VISIBLE_DEVICES": str(cfg.gpu_target),
            "PYTHONPATH": str((VENDOR_DIR / "src").absolute()),
        },
    )
    elapsed = time.time() - started
    log.write_text(
        f"$ {' '.join(cmd)}\n(elapsed {elapsed:.1f}s, exit {proc.returncode})\n"
        f"--- stdout ---\n{proc.stdout}\n--- stderr ---\n{proc.stderr}\n"
    )
    if proc.returncode != 0:
        raise T2LError(f"generate_lora.py failed with exit {proc.returncode}; see {log}")
    return proc.stdout


def _env(cfg: Config) -> dict[str, str]:
    import os

    return dict(os.environ)


def generate_lora(cfg: Config, task: str, out_dir: str) -> Path:
    description = describe_task(task)
    cmd = [
        str(VENDOR_DIR.absolute() / ".venv-t2l/bin/python"),
        "scripts/generate_lora.py",
        str(Path(cfg.t2l_checkpoint).resolve()),
        description,
    ]
    stdout = _run(cmd, cfg)
    match = _SAVED.search(stdout)
    if not match:
        raise T2LError(f"could not find 'Saved lora to' in generator output: {stdout[-500:]}")
    source = Path(match.group(1)).resolve()
    dest = Path(out_dir) / task
    if source != dest.resolve():
        if not source.exists():
            raise T2LError(f"generator reported {source}, which does not exist")
        shutil.copytree(source, dest, dirs_exist_ok=True)
    if not (dest / "adapter_config.json").exists():
        raise T2LError(f"{dest} has no adapter_config.json; the LoRA was not written correctly")
    _force_alpha_over_r_scaling(dest / "adapter_config.json")
    return dest


def _force_alpha_over_r_scaling(path: Path) -> None:
    """Match the paper's inference stack.

    The checkpoint ships `use_rslora: true`, but the released numbers were produced by
    vLLM 0.5.4, which applies the plain `alpha / r` scaling. With rslora scaling the
    adapter is ~2.8x too strong and the 2B model stops reasoning entirely (5% on GSM8K
    vs 62% for the base model); with `alpha / r` it behaves as published.
    """
    import json

    config = json.loads(path.read_text())
    if config.get("use_rslora"):
        config["use_rslora"] = False
        path.write_text(json.dumps(config, indent=2))
