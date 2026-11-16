"""Sequential grid: one job at a time on the target GPU, reflection on the other."""

from __future__ import annotations

from dataclasses import dataclass

from t2lgepa.config import Config

TARGET_ONLY_ARMS = ("base", "icl3", "t2l", "t2l_icl")
GEPA_ARMS = ("gepa_3shot", "gepa_0shot")


@dataclass(frozen=True)
class Job:
    arm: str
    task: str
    seed: int
    gpu: int
    kind: str


def plan_grid(cfg: Config, extras: bool = False, gepa: bool = True,
              gepa_seeds: list[int] | None = None,
              gepa_arms: list[str] | None = None,
              gepa_tasks: list[str] | None = None) -> list[Job]:
    jobs: list[Job] = []
    gepa_arms = tuple(gepa_arms) if gepa_arms else (
        GEPA_ARMS + (("gepa_noreflect", "gepa_merge") if extras else ())
    )
    for task in cfg.tasks:
        for arm in TARGET_ONLY_ARMS:
            jobs.append(Job(arm, task, 0, cfg.gpu_target, "target"))
    if not gepa:
        return jobs
    jobs.append(Job("reflection-server", "all", 0, cfg.gpu_reflect, "reflect"))
    for task in (gepa_tasks if gepa_tasks is not None else cfg.tasks):
        for seed in (gepa_seeds if gepa_seeds is not None else cfg.seeds):
            for arm in gepa_arms:
                jobs.append(Job(arm, task, seed, cfg.gpu_target, "target"))
    return jobs


def assert_one_job_per_gpu(jobs: list[Job]) -> None:
    """All target jobs share one GPU, and no job shares a GPU with the reflection server.

    The GPU ids come from the config, so a run can be pinned to any free device.
    """
    target_gpus = {job.gpu for job in jobs if job.kind == "target"}
    reflect_gpus = {job.gpu for job in jobs if job.kind == "reflect"}
    if len(target_gpus) > 1:
        raise ValueError(f"target jobs span several gpus: {sorted(target_gpus)}")
    if target_gpus & reflect_gpus:
        raise ValueError(
            f"target and reflection jobs share gpu {sorted(target_gpus & reflect_gpus)}"
        )
    for job in jobs:
        if job.kind not in ("target", "reflect"):
            raise ValueError(f"{job} has an unknown kind")
