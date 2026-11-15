from types import SimpleNamespace

import pytest

from t2lgepa import gepa_arm
from t2lgepa.client import Generation
from t2lgepa.config import load_config
from t2lgepa.data import Example
from t2lgepa.gepa_arm import (
    BudgetExhausted,
    GepaGateFailed,
    GepaResult,
    MeteredMetric,
    assert_gate,
    run_gepa,
)
from t2lgepa.scoring import score

BASE = "google/gemma-2-2b-it"
EX = Example(
    id="gsm8k:train:0", task="gsm8k", question="2+2?", answers=[], answer="4",
    rationale="2+2 = 4", split="train",
)
SEED_PROMPT = "Solve the problem and end with #### <number>."


class FakeClient:
    def __init__(self, text="#### 99"):
        self.text = text
        self.n_calls = 0

    def generate(self, prompts, model, temperature=0.0, max_tokens=512):
        self.n_calls += len(prompts)
        return [Generation(text=self.text, n_tokens=5, finish_reason="stop") for _ in prompts]


class FakeReflect:
    def __init__(self):
        self.n_calls = 0

    def generate(self, prompts, model, temperature=0.0, max_tokens=512):
        self.n_calls += len(prompts)
        return [Generation(text="Be careful and verify arithmetic.", n_tokens=8,
                           finish_reason="stop") for _ in prompts]


def test_metered_metric_refuses_to_exceed_budget():
    metered = MeteredMetric(score, limit=3)
    for _ in range(3):
        metered(EX, "#### 4")
    with pytest.raises(BudgetExhausted):
        metered(EX, "#### 4")
    assert metered.calls == 3


def test_reserve_refuses_before_the_calls_happen():
    metered = MeteredMetric(score, limit=3)
    metered(EX, "#### 4")
    with pytest.raises(BudgetExhausted):
        metered.reserve(3)
    assert metered.calls == 1


def stub_optimizer(seed_candidate, trainset, valset, adapter, max_metric_calls, **kwargs):
    best = seed_candidate["instruction"]
    val = list(valset)
    while True:
        try:
            batch = adapter.evaluate(val[:3], {"instruction": best}, capture_traces=False)
        except BudgetExhausted:
            break
    score_mean = sum(batch.scores) / len(batch.scores)
    return SimpleNamespace(
        best_candidate={"instruction": "Be careful and verify arithmetic."},
        candidates=[{"instruction": best}, {"instruction": "Be careful and verify arithmetic."},
                    {"instruction": "Show every step."}, {"instruction": "Check the arithmetic."}],
        val_aggregate_scores=[0.4, 0.5, 0.45, 0.55],
        discovery_eval_counts=[0, 3, 6, 9],
        total_metric_calls=adapter.metric.calls,
        best_val_aggregate_score=score_mean,
    )


def test_run_gepa_stops_at_exactly_limit(tmp_path):
    cfg = load_config("configs/base.yaml")
    result = run_gepa(
        task="gsm8k",
        seed=0,
        cfg=cfg,
        client=FakeClient(),
        reflect_client=FakeReflect(),
        seed_prompt=SEED_PROMPT,
        few_shot_block=None,
        train=[EX],
        pareto=[EX, EX],
        optimizer=stub_optimizer,
        out_dir=tmp_path,
    )
    assert result.metric_calls == cfg.gepa_budget
    assert result.curve == sorted(result.curve)


def test_gate_fails_on_flat_run():
    with pytest.raises(GepaGateFailed):
        assert_gate(
            GepaResult(
                best_prompt="p", pareto_score=0.50, curve=[(10, 0.50)], metric_calls=40,
                reflection_calls=2, wall_seconds=1.0, accepted_candidates=1,
            ),
            baseline=0.50,
        )


def test_gate_passes_on_real_gain():
    assert_gate(
        GepaResult(
            best_prompt="p", pareto_score=0.60, curve=[(10, 0.5), (20, 0.6)], metric_calls=40,
            reflection_calls=3, wall_seconds=1.0, accepted_candidates=4,
        ),
        baseline=0.50,
    )


def test_reflection_calls_are_counted(tmp_path):
    cfg = load_config("configs/base.yaml")
    result = run_gepa(
        task="gsm8k", seed=0, cfg=cfg, client=FakeClient(), reflect_client=FakeReflect(),
        seed_prompt=SEED_PROMPT, few_shot_block=None, train=[EX], pareto=[EX, EX],
        optimizer=stub_optimizer, out_dir=tmp_path,
    )
    assert result.reflection_calls == 0  # the stub never reflects
    assert (tmp_path / "gepa_gsm8k_s0.curve.jsonl").exists()


def test_adapter_refuses_test_examples(tmp_path):
    cfg = load_config("configs/base.yaml")
    test_ex = Example(
        id="gsm8k:test:0", task="gsm8k", question="q", answers=[], answer="4",
        rationale="r", split="test",
    )
    with pytest.raises(ValueError):
        run_gepa(
            task="gsm8k", seed=0, cfg=cfg, client=FakeClient(), reflect_client=FakeReflect(),
            seed_prompt=SEED_PROMPT, few_shot_block=None, train=[test_ex], pareto=[EX],
            optimizer=stub_optimizer, out_dir=tmp_path,
        )
