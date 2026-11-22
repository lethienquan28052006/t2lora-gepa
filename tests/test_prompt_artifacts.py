"""GEPA prompt artifacts are scoped per arm, and the seed prompt is always stored."""

from types import SimpleNamespace

from t2lgepa.data import Example
from t2lgepa.gepa_arm import (
    GepaResult,
    export_best_prompt,
    export_candidates,
    export_seed_prompt,
    load_best_prompt,
    run_gepa,
)


def _result(prompt: str, candidates=None) -> GepaResult:
    return GepaResult(
        best_prompt=prompt,
        pareto_score=0.5,
        curve=[(0, 0.4)],
        metric_calls=10,
        reflection_calls=2,
        wall_seconds=1.0,
        accepted_candidates=3,
        candidates=candidates or [],
    )


def test_two_arms_never_share_prompt_files(tmp_path):
    export_seed_prompt("seed A", tmp_path, "gsm8k", 0, "gepa_3shot")
    export_seed_prompt("seed B", tmp_path, "gsm8k", 0, "t2l_gepa_opt")
    export_best_prompt(_result("prompt A"), tmp_path, "gsm8k", 0, "gepa_3shot")
    export_best_prompt(_result("prompt B"), tmp_path, "gsm8k", 0, "t2l_gepa_opt")

    assert load_best_prompt(tmp_path, "gsm8k", 0) == "prompt A"
    assert load_best_prompt(tmp_path, "gsm8k", 0, arm="t2l_gepa_opt") == "prompt B"
    assert (tmp_path / "gepa_3shot_gsm8k_s0_seed_prompt.txt").read_text().strip() == "seed A"
    assert (tmp_path / "t2l_gepa_opt_gsm8k_s0_seed_prompt.txt").read_text().strip() == "seed B"
    assert not (tmp_path / "gepa_gsm8k_s0_best_prompt.txt").exists()


def test_candidates_export_keeps_the_whole_history(tmp_path):
    result = _result("best", candidates=[
        {"index": 0, "instruction": "seed", "val_aggregate_score": 0.4, "is_seed": True},
        {"index": 1, "instruction": "best", "val_aggregate_score": 0.5, "is_seed": False},
    ])
    path = export_candidates(result, tmp_path, "gsm8k", 0, "gepa_3shot")
    import json

    rows = json.loads(path.read_text())
    assert path.name == "gepa_3shot_gsm8k_s0_candidates.json"
    assert [r["instruction"] for r in rows] == ["seed", "best"]


def test_run_gepa_writes_arm_scoped_seed_and_curve(cfg, tmp_path):
    ex = Example(id="gsm8k:train:0", task="gsm8k", question="2+2?", answers=[],
                 answer="4", rationale=None, split="train")

    def optimize(**kwargs):
        return SimpleNamespace(best_candidate={"instruction": "better"},
                               best_val_aggregate_score=0.5,
                               discovery_eval_counts=[0], val_aggregate_scores=[0.5],
                               candidates=[{"instruction": "s"}, {"instruction": "better"}])

    run_gepa(task="gsm8k", seed=0, cfg=cfg, client=None, reflect_client=None,
             seed_prompt="s", few_shot_block=None, train=[ex], pareto=[ex],
             optimizer=optimize, out_dir=tmp_path, arm="t2l_gepa_opt")

    assert (tmp_path / "t2l_gepa_opt_gsm8k_s0_seed_prompt.txt").read_text().strip() == "s"
    assert (tmp_path / "t2l_gepa_opt_gsm8k_s0.curve.jsonl").exists()
    assert (tmp_path / "t2l_gepa_opt_gsm8k_s0_candidates.json").exists()
    assert not (tmp_path / "gepa_gsm8k_s0.curve.jsonl").exists()
