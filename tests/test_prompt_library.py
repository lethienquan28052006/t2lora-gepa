import json

import pytest
from fastapi.testclient import TestClient

from t2lgepa.webapp.app import create_app
from t2lgepa.webapp.library import PromptLibrary


def _history(tmp_path, best="The improved instruction"):
    stem = tmp_path / "t2l_gepa_opt_hellaswag_s0"
    (tmp_path / f"{stem.name}_seed_prompt.txt").write_text("Seed instruction\n")
    (tmp_path / f"{stem.name}_best_prompt.txt").write_text(best + "\n")
    (tmp_path / f"{stem.name}_candidates.json").write_text(json.dumps([
        {"index": 0, "instruction": "Seed instruction", "val_aggregate_score": 0.61,
         "is_seed": True},
        {"index": 1, "instruction": "The improved instruction", "val_aggregate_score": 0.67,
         "is_seed": False},
        {"index": 2, "instruction": "A rejected instruction", "val_aggregate_score": 0.64,
         "is_seed": False},
    ]))
    (tmp_path / f"{stem.name}.curve.jsonl").write_text(
        '{"metric_calls": 300, "pareto_score": 0.61}\n'
        '{"metric_calls": 1000, "pareto_score": 0.67}\n')


def test_history_returns_real_seed_candidates_best_and_curve(tmp_path):
    _history(tmp_path)
    result = PromptLibrary(tmp_path).history("hellaswag", "t2l_gepa_opt")

    assert result["seed"] == "Seed instruction"
    assert result["best"] == "The improved instruction"
    assert result["unchanged"] is False
    assert result["best_index"] == 1
    assert [c["index"] for c in result["candidates"]] == [0, 1, 2]
    assert result["candidates"][2]["val_aggregate_score"] == 0.64
    assert result["curve"] == [{"metric_calls": 300, "pareto_score": 0.61},
                               {"metric_calls": 1000, "pareto_score": 0.67}]


def test_unchanged_prompt_is_explicit_instead_of_fabricating_a_diff(tmp_path):
    _history(tmp_path, best="Seed instruction")
    result = PromptLibrary(tmp_path).history("hellaswag", "t2l_gepa_opt")
    assert result["unchanged"] is True
    assert result["best_index"] == 0


def test_missing_history_fails_loudly(tmp_path):
    with pytest.raises(ValueError, match="no stored prompt history"):
        PromptLibrary(tmp_path).history("hellaswag", "gepa_3shot")


def test_api_rejects_an_unsearched_arm(tmp_path):
    client = TestClient(create_app(object(), results_dir=tmp_path))
    response = client.get("/api/prompt-library", params={"task": "gsm8k", "arm": "base"})
    assert response.status_code == 400
    assert "arm" in response.json()["detail"]


def test_api_serves_a_real_history(tmp_path):
    _history(tmp_path)
    client = TestClient(create_app(object(), results_dir=tmp_path))
    response = client.get("/api/prompt-library",
                          params={"task": "hellaswag", "arm": "t2l_gepa_opt"})
    assert response.status_code == 200
    assert response.json()["best_index"] == 1
    assert response.json()["unchanged"] is False
