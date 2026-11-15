"""One vLLM server, three adaptation surfaces: base, base+LoRA, base+GEPA prompt."""

from __future__ import annotations

import time
from pathlib import Path

from t2lgepa.client import VLLMClient
from t2lgepa.config import Config
from t2lgepa.t2l import lora_module_name

BASE_URL_DEFAULT = "http://localhost:8010"
REPO_ROOT = Path(__file__).resolve().parents[2]
VLLM_BIN = REPO_ROOT / ".venv-serve/bin/vllm"
SURFACES = ("base", "t2l", "gepa")


def build_serve_cmd(cfg: Config, lora_dir: Path, port: int = 8010, task: str = "gsm8k") -> list[str]:
    return [
        str(VLLM_BIN),
        "serve",
        "--model",
        cfg.model_id,
        "--enable-lora",
        "--max-lora-rank",
        "64",
        "--lora-modules",
        f"{lora_module_name(task)}={lora_dir}",
        "--gpu-memory-utilization",
        "0.85",
        "--port",
        str(port),
    ]


def wait_ready(url: str, timeout_s: float = 900) -> None:
    import httpx

    deadline = time.time() + timeout_s
    while time.time() < deadline:
        try:
            if httpx.get(f"{url}/v1/models", timeout=5).status_code == 200:
                return
        except httpx.HTTPError:
            pass
        time.sleep(5)
    raise TimeoutError(f"{url} did not become ready")


def gepa_prompt_from_curve(results_dir: Path) -> str | None:
    candidates = sorted(Path(results_dir).glob("gepa_*_best_prompt.txt"))
    if not candidates:
        return None
    return candidates[-1].read_text().strip()


def run_all(
    prompts: list[str],
    cfg: Config,
    gepa_prompt: str | None = None,
    base_url: str = BASE_URL_DEFAULT,
    task: str = "gsm8k",
) -> dict[str, list[str]]:
    client = VLLMClient(base_url, cfg.model_id, adapters=[lora_module_name(task)])
    out: dict[str, list[str]] = {}
    out["base"] = [g.text for g in client.generate(prompts, model=cfg.model_id)]
    out["t2l"] = [g.text for g in client.generate(prompts, model=lora_module_name(task))]
    gepa_prompts = [
        f"{gepa_prompt}\n\n{p}" if gepa_prompt else p for p in prompts
    ]
    out["gepa"] = [g.text for g in client.generate(gepa_prompts, model=cfg.model_id)]
    return out
