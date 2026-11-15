"""Typed configuration plus the run fingerprint used to key cached results."""

from __future__ import annotations

import hashlib
import json
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

import yaml

DECODE_FIELDS = (
    "model_id",
    "t2l_checkpoint",
    "reflection_model",
    "tasks",
    "seeds",
    "max_tokens",
    "temperature",
    "rollout_temperature",
    "rollout_top_p",
)


def _git_sha(repo: str) -> str:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=repo, capture_output=True, text=True, check=True
        )
        sha = out.stdout.strip()
        status = subprocess.run(
            ["git", "status", "--porcelain"], cwd=repo, capture_output=True, text=True,
            check=True,
        )
        return f"{sha}-dirty" if status.stdout.strip() else sha
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


@dataclass(frozen=True)
class Config:
    model_id: str
    t2l_checkpoint: str
    reflection_model: str
    tasks: tuple[str, ...]
    seeds: tuple[int, ...]
    gepa_budget: int
    gpu_target: int
    gpu_reflect: int
    results_dir: str
    cache_dir: str
    max_tokens: int
    temperature: float
    rollout_temperature: float
    rollout_top_p: float
    smoke_limit: int
    max_eval_items: int
    gate_tol_smoke_pp: float
    gate_tol_full_pp: float
    expected: dict[str, float] = field(default_factory=dict)

    @classmethod
    def from_yaml(cls, path: str | Path) -> Config:
        raw = yaml.safe_load(Path(path).read_text())
        raw["tasks"] = tuple(raw["tasks"])
        raw["seeds"] = tuple(raw["seeds"])
        return cls(**raw)


def load_config(path: str | Path) -> Config:
    return Config.from_yaml(path)


def run_fingerprint(cfg: Config, repo_root: str | Path | None = None) -> str:
    """Stable hash of the setup that decides whether two runs are comparable."""
    root = Path(repo_root) if repo_root is not None else Path(__file__).resolve().parents[2]
    payload = {name: getattr(cfg, name) for name in DECODE_FIELDS}
    payload["tasks"] = list(payload["tasks"])
    payload["seeds"] = list(payload["seeds"])
    payload["git_sha"] = _git_sha(str(root))
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(blob).hexdigest()
