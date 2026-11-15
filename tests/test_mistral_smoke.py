import types

import mistral_smoke

from t2lgepa.config import load_config
from t2lgepa.runner import RunSummary


def _fake_runner(scores):
    def runner(arm, task, seed, client, prompt_fn, model, cfg, **kwargs):
        return RunSummary(score=scores[task][arm], n=100, wall_seconds=1.0, generated_tokens=10)

    return runner


def test_table_reports_four_arms_per_task():
    scores = {t: {"base": 0.6, "icl3": 0.6, "t2l": 0.6, "t2l_icl": 0.6} for t in mistral_smoke.TASKS}
    text, failures = mistral_smoke.render(scores)
    assert failures == []
    for task in mistral_smoke.TASKS:
        assert task in text
    assert text.count("t2l_icl") >= 1


def test_collapsed_adapter_fails_the_run(monkeypatch, tmp_path):
    cfg = load_config("configs/mistral.yaml")
    monkeypatch.setattr(mistral_smoke, "make_splits",
                        lambda task, cache_dir: types.SimpleNamespace(train=[]))
    scores = {t: {"base": 0.6, "icl3": 0.6, "t2l": 0.05, "t2l_icl": 0.05} for t in mistral_smoke.TASKS}
    monkeypatch.setattr(mistral_smoke, "run_arm", _fake_runner(scores))
    code = mistral_smoke.run(cfg, client=object(), limit=100, out_dir=tmp_path)
    assert code == 1


def test_healthy_adapters_pass(monkeypatch, tmp_path):
    cfg = load_config("configs/mistral.yaml")
    monkeypatch.setattr(mistral_smoke, "make_splits",
                        lambda task, cache_dir: types.SimpleNamespace(train=[]))
    scores = {t: {"base": 0.6, "icl3": 0.62, "t2l": 0.65, "t2l_icl": 0.70} for t in mistral_smoke.TASKS}
    monkeypatch.setattr(mistral_smoke, "run_arm", _fake_runner(scores))
    code = mistral_smoke.run(cfg, client=object(), limit=100, out_dir=tmp_path)
    assert code == 0
