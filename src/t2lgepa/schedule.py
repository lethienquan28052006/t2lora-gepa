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


def plan_grid(cfg: Config, extras: bool = False) -> list[Job]:
    jobs: list[Job] = []
    gepa_arms = GEPA_ARMS + (("gepa_noreflect", "gepa_merge") if extras else ())
    for task in cfg.tasks:
        for arm in TARGET_ONLY_ARMS:
            jobs.append(Job(arm, task, 0, cfg.gpu_target, "target"))
        for seed in cfg.seeds:
            for arm in gepa_arms:
                jobs.append(Job(arm, task, seed, cfg.gpu_target, "target"))
    jobs.append(Job("reflection-server", "all", 0, cfg.gpu_reflect, "reflect"))
    return jobs


def assert_one_job_per_gpu(jobs: list[Job]) -> None:
    for job in jobs:
        if job.kind == "target" and job.gpu != 6:
            raise ValueError(f"target job {job} is not on gpu 6")
        if job.kind == "reflect" and job.gpu != 7:
            raise ValueError(f"reflect job {job} is not on gpu 7")
        if job.kind not in ("target", "reflect"):
            raise ValueError(f"{job} has an unknown kind")
