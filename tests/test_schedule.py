import pytest

from t2lgepa.config import load_config
from t2lgepa.schedule import Job, assert_one_job_per_gpu, plan_grid


@pytest.fixture
def cfg():
    return load_config("configs/base.yaml")


def test_target_jobs_run_on_the_target_gpu_only(cfg):
    jobs = plan_grid(cfg)
    assert {j.gpu for j in jobs if j.kind == "target"} == {cfg.gpu_target}
    assert {j.gpu for j in jobs if j.kind == "reflect"} == {cfg.gpu_reflect}


def test_gepa_jobs_come_after_their_seed_prompt_dependency(cfg):
    jobs = plan_grid(cfg)
    arms = [j.arm for j in jobs]
    assert arms.index("gepa_3shot") > arms.index("icl3")
    assert arms.index("gepa_0shot") > arms.index("base")


def test_grid_covers_all_arms_tasks_seeds(cfg):
    names = {(j.arm, j.task, j.seed) for j in plan_grid(cfg)}
    assert ("t2l_icl", "gsm8k", 0) in names
    assert ("gepa_3shot", "gsm8k", 2) in names
    assert ("base", "gsm8k", 0) in names
    assert ("t2l", "gsm8k", 0) in names


def test_extras_are_opt_in(cfg):
    fast = {j.arm for j in plan_grid(cfg)}
    full = {j.arm for j in plan_grid(cfg, extras=True)}
    assert "gepa_merge" not in fast and "gepa_merge" in full
    assert {"base", "icl3", "t2l", "t2l_icl", "gepa_3shot", "gepa_0shot"} <= fast


def test_one_job_per_gpu_is_enforced():
    jobs = [Job("base", "gsm8k", 0, 6, "target"), Job("t2l", "gsm8k", 0, 7, "target")]
    with pytest.raises(ValueError, match="gpu"):
        assert_one_job_per_gpu(jobs)


def test_plan_is_deterministic(cfg):
    assert plan_grid(cfg) == plan_grid(cfg)


def test_reflect_cmd_uses_gpu7_model_and_port(cfg):
    from run_grid import REFLECT_PORT, reflect_cmd

    cmd = reflect_cmd(cfg)
    assert cmd[cmd.index("--model") + 1] == cfg.reflection_model
    assert cmd[cmd.index("--port") + 1] == str(REFLECT_PORT)
    assert "--served-model-name" in cmd


def test_reflection_server_starts_before_any_gepa_job(cfg):
    jobs = plan_grid(cfg)
    reflect_at = next(i for i, j in enumerate(jobs) if j.kind == "reflect")
    first_gepa = next(i for i, j in enumerate(jobs) if j.arm.startswith("gepa"))
    assert reflect_at < first_gepa


def test_arm_dispatch_kinds():
    from run_grid import arm_kind

    assert arm_kind("base") == "run_arm"
    assert arm_kind("gepa_3shot") == "gepa"
    assert arm_kind("gepa_merge") == "unsupported"
    assert arm_kind("gepa_noreflect") == "unsupported"


def test_reflect_cmd_uses_the_isolated_vllm_binary(cfg):
    from run_grid import reflect_cmd

    assert reflect_cmd(cfg)[0].endswith(".venv-serve/bin/vllm")
