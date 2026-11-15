from types import SimpleNamespace

import pytest

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


def test_budget_trip_returns_partial_result_and_records_curve(tmp_path):
    from dataclasses import replace

    cfg = replace(load_config("configs/base.yaml"), gepa_budget=5)

    def exploding_optimizer(seed_candidate, trainset, valset, adapter, **kwargs):
        batch = list(trainset) + list(valset)
        while True:
            adapter.evaluate(batch[:3], {"instruction": "x"})

    result = run_gepa(
        task="gsm8k", seed=0, cfg=cfg, client=FakeClient(), reflect_client=FakeReflect(),
        seed_prompt=SEED_PROMPT, few_shot_block=None,
        train=[EX, EX, EX], pareto=[EX, EX, EX],
        optimizer=exploding_optimizer, out_dir=tmp_path,
    )
    assert result.partial is True
    assert result.metric_calls <= cfg.gepa_budget
    assert result.accepted_candidates == 0
    assert (tmp_path / "gepa_gsm8k_s0.curve.jsonl").exists()


def test_accepted_candidates_excludes_the_seed(tmp_path):
    cfg = load_config("configs/base.yaml")
    result = run_gepa(
        task="gsm8k", seed=0, cfg=cfg, client=FakeClient(), reflect_client=FakeReflect(),
        seed_prompt=SEED_PROMPT, few_shot_block=None, train=[EX], pareto=[EX, EX],
        optimizer=stub_optimizer, out_dir=tmp_path,
    )
    assert result.accepted_candidates == 3  # stub returns 4 candidates incl. the seed


def test_export_best_prompt_writes_the_file_the_demo_reads(tmp_path):
    from t2lgepa.gepa_arm import export_best_prompt

    result = GepaResult(
        best_prompt="Best instruction here.", pareto_score=0.6, curve=[], metric_calls=10,
        reflection_calls=2, wall_seconds=1.0, accepted_candidates=3,
    )
    path = export_best_prompt(result, tmp_path, task="gsm8k", seed=0)
    assert path.name == "gepa_gsm8k_s0_best_prompt.txt"
    assert "Best instruction here." in path.read_text()


def test_prompt_fn_uses_the_optimised_instruction():
    from t2lgepa.gepa_arm import prompt_fn_from

    fn = prompt_fn_from("OPTIMISED RULES", None)
    text = fn(EX)
    assert "OPTIMISED RULES" in text and "2+2?" in text


def test_adapter_exposes_propose_new_texts_for_the_engine():
    from t2lgepa.gepa_arm import _Adapter

    assert hasattr(_Adapter, "propose_new_texts")
    assert _Adapter.propose_new_texts is None


def test_run_gepa_disables_skip_perfect_score(tmp_path):
    cfg = load_config("configs/base.yaml")
    captured = {}

    def spy(seed_candidate, trainset, valset, adapter, **kwargs):
        captured.update(kwargs)
        return stub_optimizer(seed_candidate, trainset, valset, adapter, **kwargs)

    run_gepa("gsm8k", 0, cfg, FakeClient(), FakeReflect(), SEED_PROMPT, None,
             train=[EX], pareto=[EX, EX], optimizer=spy, out_dir=tmp_path)
    assert captured["skip_perfect_score"] is False


def test_engine_budget_leaves_room_for_one_validation_sweep(tmp_path):
    cfg = load_config("configs/base.yaml")
    captured = {}

    def spy(seed_candidate, trainset, valset, adapter, **kwargs):
        captured["max_metric_calls"] = kwargs.get("max_metric_calls")
        return stub_optimizer(seed_candidate, trainset, valset, adapter, **kwargs)

    pareto = [EX, EX, EX]
    run_gepa("gsm8k", 0, cfg, FakeClient(), FakeReflect(), SEED_PROMPT, None,
             train=[EX], pareto=pareto, optimizer=spy, out_dir=tmp_path)
    assert captured["max_metric_calls"] == cfg.gepa_budget - len(pareto)
