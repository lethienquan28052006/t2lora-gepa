"""Sequential grid runner: target jobs on GPU 6, reflection server on GPU 7."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from t2lgepa.client import VLLMClient
from t2lgepa.config import Config, load_config
from t2lgepa.data import make_splits
from t2lgepa.gepa_arm import (
    GepaGateFailed,
    assert_gate,
    export_best_prompt,
    prompt_fn_from,
    run_gepa,
)
from t2lgepa.prompts import demo_block, three_shot, zero_shot
from t2lgepa.runner import read_summary, run_arm
from t2lgepa.schedule import Job, assert_one_job_per_gpu, plan_grid
from t2lgepa.t2l import lora_module_name

REFLECT_PORT = 8001
GEPA_ARMS_SUPPORTED = ("gepa_3shot", "gepa_0shot")

SEED_INSTRUCTION = (
    "Solve the arithmetic word problem. Reason step by step and finish with the final "
    "numeric answer on its own line as '#### <number>'."
)


def reflect_cmd(cfg: Config, port: int = REFLECT_PORT) -> list[str]:
    return [
        cfg.vllm_bin,
        "serve",
        "--model",
        cfg.reflection_model,
        "--port",
        str(port),
        "--gpu-memory-utilization",
        "0.85",
        "--max-model-len",
        "8192",
        "--served-model-name",
        cfg.reflection_model,
    ]


def wait_for(url: str, timeout_s: float = 900) -> None:
    import httpx

    deadline = time.time() + timeout_s
    while time.time() < deadline:
        try:
            if httpx.get(f"{url}/v1/models", timeout=5).status_code == 200:
                return
        except httpx.HTTPError:
            pass
        time.sleep(5)
    raise TimeoutError(f"{url} did not become ready in {timeout_s}s")


def args_lora_root() -> str:
    import os

    return os.environ.get("T2L_LORA_ROOT", "artifacts/t2l_loras")


def arm_kind(arm: str) -> str:
    if arm in ("base", "icl3", "t2l", "t2l_icl"):
        return "run_arm"
    if arm in GEPA_ARMS_SUPPORTED:
        return "gepa"
    return "unsupported"


def run_job(
    job: Job,
    cfg: Config,
    target: VLLMClient,
    reflect: VLLMClient | None,
    results_dir: Path,
) -> dict:
    adapter = lora_module_name(job.task)
    splits = make_splits(job.task, cache_dir=cfg.cache_dir)
    demos = splits.train[:3]
    if job.arm in ("base", "icl3", "t2l", "t2l_icl"):
        model = adapter if job.arm.startswith("t2l") else cfg.model_id
        prompt_fn = zero_shot if job.arm in ("base", "t2l") else (lambda ex: three_shot(ex, demos))
        lora_dir = Path(args_lora_root()) / job.task
        summary = run_arm(job.arm, job.task, job.seed, target, prompt_fn, model, cfg,
                          results_dir=results_dir,
                          adapter_path=lora_dir if model != cfg.model_id and lora_dir.exists()
                          else None)
        return {"arm": job.arm, "task": job.task, "seed": job.seed,
                "score": summary.score, "n": summary.n,
                "wall_seconds": summary.wall_seconds}
    if reflect is None:
        raise RuntimeError(f"{job.arm} needs the reflection server")
    few_shot_block = demo_block(demos) if job.arm == "gepa_3shot" else None
    result = run_gepa(
        task=job.task, seed=job.seed, cfg=cfg, client=target, reflect_client=reflect,
        seed_prompt=SEED_INSTRUCTION, few_shot_block=few_shot_block,
        train=splits.train, pareto=splits.pareto, out_dir=results_dir,
    )
    export_best_prompt(result, results_dir, task=job.task, seed=job.seed)

    # Score the final prompt greedily on the held-out test set: the Pareto score above
    # is measured on the selection set the optimiser maximised, so it is not comparable
    # to the other arms.
    summary = run_arm(
        job.arm, job.task, job.seed, target,
        prompt_fn_from(result.best_prompt, few_shot_block), cfg.model_id, cfg,
        results_dir=results_dir, adapter_path=results_dir,
    )
    baseline = cfg.expected.get(f"{job.task}/base", 0.0)
    base_file = results_dir / f"base_{job.task}_s0.jsonl"
    if base_file.exists():
        baseline = read_summary(base_file)["score"]
    gate = "pass"
    try:
        assert_gate(result, baseline)
    except GepaGateFailed as exc:
        gate = f"fail: {exc}"
    (results_dir / f"{job.arm}_{job.task}_s{job.seed}.gate.json").write_text(
        json.dumps({"arm": job.arm, "task": job.task, "seed": job.seed, "gate": gate,
                    "partial": result.partial, "pareto_score": result.pareto_score,
                    "baseline": baseline}, indent=2)
    )
    return {"arm": job.arm, "task": job.task, "seed": job.seed,
            "gate": gate, "partial": result.partial,
            "test_score": summary.score, "test_n": summary.n,
            "pareto_score": result.pareto_score, "metric_calls": result.metric_calls,
            "reflection_calls": result.reflection_calls,
            "wall_seconds": result.wall_seconds + summary.wall_seconds,
            "best_prompt": result.best_prompt}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/base.yaml")
    parser.add_argument("--base-url", default="http://localhost:8010")
    parser.add_argument("--extras", action="store_true")
    parser.add_argument("--no-gepa", action="store_true")
    parser.add_argument("--gepa-tasks", default=None,
                        help="comma separated tasks to optimise with GEPA")
    parser.add_argument("--gepa-arms", default=None,
                        help="comma separated GEPA arms, e.g. gepa_3shot")
    parser.add_argument("--gepa-seeds", default=None,
                        help="comma separated seeds for GEPA arms, e.g. 0")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--no-reflect-server", action="store_true",
                        help="assume a reflection server is already running on port 8001")
    args = parser.parse_args(argv)

    cfg = load_config(args.config)
    gs = [int(s) for s in args.gepa_seeds.split(",")] if args.gepa_seeds else None
    ga = args.gepa_arms.split(",") if args.gepa_arms else None
    gt = args.gepa_tasks.split(",") if args.gepa_tasks else None
    jobs = plan_grid(cfg, extras=args.extras, gepa=not args.no_gepa, gepa_seeds=gs,
                     gepa_arms=ga, gepa_tasks=gt)
    assert_one_job_per_gpu(jobs)
    for job in jobs:
        print(f"{job.kind:7s} gpu{job.gpu}  {job.arm:16s} {job.task:14s} seed={job.seed}")
    if args.dry_run:
        return 0

    results_dir = Path(cfg.results_dir)
    results_dir.mkdir(parents=True, exist_ok=True)
    adapters = [lora_module_name(t) for t in cfg.tasks]
    target = VLLMClient(args.base_url, cfg.model_id, adapters=adapters)
    target.assert_ready()
    reflect_url = f"http://localhost:{REFLECT_PORT}"

    reflect_proc = None
    reflect = None
    try:
        for job in jobs:
            if job.kind == "reflect":
                if args.no_reflect_server:
                    reflect = VLLMClient(reflect_url, cfg.reflection_model, adapters=[])
                    reflect.assert_ready()
                    continue
                env = {**os.environ, "CUDA_VISIBLE_DEVICES": str(cfg.gpu_reflect),
                       "VLLM_USE_FLASHINFER_SAMPLER": "0"}
                reflect_proc = subprocess.Popen(reflect_cmd(cfg), env=env)
                wait_for(reflect_url)
                reflect = VLLMClient(reflect_url, cfg.reflection_model, adapters=[])
                continue
            kind = arm_kind(job.arm)
            if kind == "unsupported":
                record = {"arm": job.arm, "task": job.task, "seed": job.seed,
                          "status": "skipped: not implemented in this harness"}
                (results_dir / f"{job.arm}_{job.task}_s{job.seed}.job.json").write_text(
                    json.dumps(record, indent=2))
                print(json.dumps(record))
                continue
            record = run_job(job, cfg, target, reflect, results_dir)
            out = results_dir / f"{job.arm}_{job.task}_s{job.seed}.job.json"
            out.write_text(json.dumps(record, indent=2))
            print(json.dumps(record))
    finally:
        if reflect_proc is not None:
            reflect_proc.terminate()
            reflect_proc.wait(timeout=60)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
