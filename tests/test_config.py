import pytest

from t2lgepa.config import load_config, run_fingerprint


def test_fingerprint_is_stable_and_order_insensitive(tmp_path):
    a = load_config("configs/base.yaml")
    b = load_config("configs/base.yaml")
    assert run_fingerprint(a) == run_fingerprint(b)
    assert len(run_fingerprint(a)) == 64


def test_base_config_matches_global_constraints():
    cfg = load_config("configs/base.yaml")
    assert cfg.model_id == "google/gemma-2-2b-it"
    assert cfg.t2l_checkpoint.endswith("gemma_2b_t2l")
    assert cfg.tasks == ("gsm8k", "arc_challenge")
    assert cfg.seeds == (0, 1, 2)
    assert cfg.gepa_budget == 1500
    assert cfg.gpu_target == 6 and cfg.gpu_reflect == 7
    assert cfg.temperature == 0.0
    assert cfg.rollout_temperature == 0.6 and cfg.rollout_top_p == 0.95
    assert cfg.smoke_limit == 300
    assert cfg.gate_tol_smoke_pp == 6.0
    assert cfg.gate_tol_full_pp == 3.0
    assert cfg.expected["gsm8k/base"] == pytest.approx(0.5527)
    assert cfg.expected["gsm8k/t2l_icl"] == pytest.approx(0.5689)


def test_fingerprint_changes_when_decode_changes(tmp_path):
    from dataclasses import replace

    cfg = load_config("configs/base.yaml")
    assert run_fingerprint(cfg) != run_fingerprint(replace(cfg, max_tokens=256))
