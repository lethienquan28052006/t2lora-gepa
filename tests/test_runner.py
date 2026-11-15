import json
from dataclasses import replace

import pytest

from t2lgepa.client import Generation
from t2lgepa.config import load_config
from t2lgepa.prompts import three_shot, zero_shot
from t2lgepa.runner import run_arm

BASE = "google/gemma-2-2b-it"
REQUIRED_FIELDS = {
    "arm", "task", "seed", "n", "score", "model_id", "adapter", "decode",
    "git_sha", "vllm_version", "torch_version", "wall_seconds",
    "generated_tokens", "metric_calls", "reflection_calls", "fingerprint",
}


class FakeClient:
    def __init__(self):
        self.n_calls = 0

    def generate(self, prompts, model, temperature=0.0, max_tokens=512):
        self.n_calls += len(prompts)
        return [Generation(text="#### 18", n_tokens=4, finish_reason="stop") for _ in prompts]


@pytest.fixture
def cfg():
    return replace(load_config("configs/base.yaml"), cache_dir="tests/fixtures")


@pytest.fixture
def fake_client():
    return FakeClient()


def test_second_run_reuses_cache(tmp_path, fake_client, cfg):
    s1 = run_arm("base", "gsm8k", 0, fake_client, zero_shot, BASE, cfg, limit=3,
                 results_dir=tmp_path)
    s2 = run_arm("base", "gsm8k", 0, fake_client, zero_shot, BASE, cfg, limit=3,
                 results_dir=tmp_path)
    assert s1.score == s2.score and fake_client.n_calls == 3


def test_record_contains_all_global_constraint_fields(tmp_path, fake_client, cfg):
    run_arm("base", "gsm8k", 0, fake_client, zero_shot, BASE, cfg, limit=3,
            results_dir=tmp_path)
    rec = json.loads((tmp_path / "base_gsm8k_s0.jsonl").read_text().splitlines()[0])
    assert REQUIRED_FIELDS <= rec.keys()


def test_raw_generations_are_persisted_for_case_studies(tmp_path, fake_client, cfg):
    run_arm("base", "gsm8k", 0, fake_client, zero_shot, BASE, cfg, limit=3,
            results_dir=tmp_path)
    assert (tmp_path / "base_gsm8k_s0.generations.jsonl").exists()


def test_limit_counts_items_and_score_matches_scorer(tmp_path, fake_client, cfg):
    summary = run_arm("base", "gsm8k", 0, fake_client, zero_shot, BASE, cfg, limit=3,
                      results_dir=tmp_path)
    assert summary.n == 3 and summary.score == 0.0  # fake always answers "18", fixtures gold 7/7/6


def test_three_shot_includes_demos(cfg):
    from t2lgepa.data import load_task

    exs = load_task("gsm8k", "test", cache_dir="tests/fixtures")
    text = three_shot(exs[0], exs[1:3])
    assert text.count("####") >= 2 and exs[0].question in text
    assert zero_shot(exs[0]) in text or exs[0].question in zero_shot(exs[0])
