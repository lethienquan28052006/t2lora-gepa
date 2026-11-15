"""Arm runner: prompt -> generate -> extract -> score -> record, with resume."""

from __future__ import annotations

import hashlib
import json
import subprocess
import time
from collections.abc import Callable
from dataclasses import asdict, dataclass
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from t2lgepa.client import VLLMClient
from t2lgepa.config import Config, run_fingerprint
from t2lgepa.data import Example, load_task
from t2lgepa.records import RunKey, append_record, load_items, load_results, rewrite_with_summary
from t2lgepa.scoring import extract_answer, score


@dataclass(frozen=True)
class RunSummary:
    score: float
    n: int
    wall_seconds: float
    generated_tokens: int


def _version(pkg: str) -> str:
    try:
        return version(pkg)
    except PackageNotFoundError:
        return "not-installed"


def _git_sha() -> str:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, check=True
        )
        return out.stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def _dir_hash(path: Path) -> str:
    digest = hashlib.sha1()
    for file in sorted(p for p in path.rglob("*") if p.is_file()):
        stat = file.stat()
        digest.update(f"{file.name}:{stat.st_size}:{int(stat.st_mtime)}".encode())
    return digest.hexdigest()[:12]


def _paths(results_dir: Path, arm: str, task: str, seed: int) -> tuple[Path, Path]:
    stem = f"{arm}_{task}_s{seed}"
    return results_dir / f"{stem}.jsonl", results_dir / f"{stem}.generations.jsonl"


def run_arm(
    arm: str,
    task: str,
    seed: int,
    client: VLLMClient,
    prompt_fn: Callable[[Example], str],
    model: str,
    cfg: Config,
    limit: int | None = None,
    results_dir: str | Path | None = None,
    adapter_path: str | Path | None = None,
) -> RunSummary:
    out_dir = Path(results_dir) if results_dir is not None else Path(cfg.results_dir)
    items_path, gens_path = _paths(out_dir, arm, task, seed)
    fingerprint = run_fingerprint(cfg)
    if adapter_path is not None:
        fingerprint = f"{fingerprint}-{_dir_hash(Path(adapter_path))}"
    key = RunKey(arm, task, seed, fingerprint)

    examples = load_task(task, "test", cache_dir=cfg.cache_dir)[: cfg.max_eval_items]
    if limit is not None:
        examples = examples[:limit]

    finished = load_results(items_path).get(key)
    if finished is not None and finished["n"] >= len(examples):
        return RunSummary(
            score=finished["score"],
            n=finished["n"],
            wall_seconds=finished.get("wall_seconds", 0.0),
            generated_tokens=finished.get("generated_tokens", 0),
        )

    done = load_items(items_path, key)
    missing = [ex for ex in examples if ex.id not in done]
    prior = finished or {}


    started = time.time()
    tokens = 0
    if missing:
        generations = client.generate(
            [prompt_fn(ex) for ex in missing],
            model=model,
            temperature=cfg.temperature,
            max_tokens=cfg.max_tokens,
        )
        tokens = sum(g.n_tokens for g in generations)
        for ex, gen in zip(missing, generations):
            pred = extract_answer(gen.text, ex.task)
            record = {
                "arm": arm,
                "task": task,
                "seed": seed,
                "fingerprint": fingerprint,
                "id": ex.id,
                "question": ex.question,
                "text": gen.text,
                "pred": pred,
                "gold": ex.answer,
                "rationale": ex.rationale,
                "correct": score(pred, ex),
                "finish_reason": gen.finish_reason,
            }
            append_record(gens_path, {"id": ex.id, **record})
            done[ex.id] = record
    wall = time.time() - started
    wall += float(prior.get("wall_seconds", 0.0))
    tokens += int(prior.get("generated_tokens", 0))

    ordered = [done[ex.id] for ex in examples]
    summary = {
        "arm": arm,
        "task": task,
        "seed": seed,
        "fingerprint": fingerprint,
        "n": len(ordered),
        "score": sum(1 for r in ordered if r["correct"]) / len(ordered) if ordered else 0.0,
        "model_id": cfg.model_id,
        "adapter": "none" if model == cfg.model_id else model,
        "decode": {"temperature": cfg.temperature, "max_tokens": cfg.max_tokens},
        "git_sha": _git_sha(),
        "vllm_version": _version("vllm"),
        "torch_version": _version("torch"),
        "wall_seconds": round(wall, 2),
        "generated_tokens": tokens,
        "metric_calls": len(ordered),
        "reflection_calls": 0,
    }
    rewrite_with_summary(items_path, summary, ordered)
    return RunSummary(
        score=summary["score"], n=summary["n"], wall_seconds=wall, generated_tokens=tokens
    )


def read_summary(path: str | Path) -> dict:
    first = Path(path).read_text(encoding="utf-8").splitlines()[0]
    return json.loads(first)


__all__ = ["RunSummary", "asdict", "read_summary", "run_arm"]
