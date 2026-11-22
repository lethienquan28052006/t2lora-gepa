"""CLI plumbing: a run can be redirected to a fresh results directory."""

import argparse

from run_grid import resolve_config


def _args(**kwargs):
    values = {"config": "configs/base.yaml", "results_dir": None}
    values.update(kwargs)
    return argparse.Namespace(**values)


def test_resolve_config_keeps_the_config_default():
    cfg = resolve_config(_args())
    assert cfg.results_dir == "results"


def test_resolve_config_redirects_results_to_a_fresh_directory():
    cfg = resolve_config(_args(results_dir="/tmp/opencode/fresh-run"))
    assert cfg.results_dir == "/tmp/opencode/fresh-run"
    # everything that decides the numbers is untouched by the redirect
    assert cfg.model_id and cfg.max_eval_items and cfg.temperature == 0.0


def test_rendered_example_contains_seed_and_best(tmp_path):
    from run_grid import export_rendered_example

    from t2lgepa.data import Example
    from t2lgepa.gepa_arm import GepaResult

    ex = Example(id="gsm8k:train:0", task="gsm8k", question="2+2?", answers=[],
                 answer="4", rationale="2+2=4", split="train")
    result = GepaResult(best_prompt="BEST", pareto_score=0.5, curve=[], metric_calls=1,
                        reflection_calls=0, wall_seconds=0.0, accepted_candidates=3)
    path = export_rendered_example(result, "SEED", None, ex, tmp_path, "gsm8k", 0, "gepa_3shot")
    text = path.read_text()
    assert path.name == "gepa_3shot_gsm8k_s0_rendered_example.txt"
    assert "SEED" in text and "BEST" in text and "2+2?" in text


def test_main_applies_the_results_dir_override(monkeypatch):
    import run_grid

    seen = {}

    def fake_plan(cfg, **kwargs):
        seen["results_dir"] = cfg.results_dir
        return []

    monkeypatch.setattr(run_grid, "plan_grid", fake_plan)
    monkeypatch.setattr(run_grid, "assert_one_job_per_gpu", lambda jobs: None)
    assert run_grid.main(["--config", "configs/base.yaml",
                          "--results-dir", "/tmp/opencode/fresh", "--dry-run"]) == 0
    assert seen["results_dir"] == "/tmp/opencode/fresh"


def test_report_tables_tolerate_incomplete_runs(tmp_path):
    import json

    from build_report_v1 import accuracy_table, ci_table, cost_table

    (tmp_path / "base_gsm8k_s0.jsonl").write_text(json.dumps(
        {"arm": "base", "task": "gsm8k", "seed": 0, "n": 40, "score": 0.5,
         "generated_tokens": 10}) + "\n")
    (tmp_path / "base_gsm8k_s0.job.json").write_text(json.dumps({"wall_seconds": 3.0}))
    text = accuracy_table(tmp_path, ["gsm8k", "boolq"])
    assert "50.0 (n=40)" in text and "—" in text and "mean over complete tasks only" in text
    assert "| icl3 | gsm8k | — | — | 0 |" in ci_table(tmp_path, ["gsm8k"], "base")
    assert "| base | gsm8k | 3 | 10 | 0 | 40 | 0 |" in cost_table(tmp_path, ["gsm8k"])
