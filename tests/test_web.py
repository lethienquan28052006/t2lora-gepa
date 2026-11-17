import json

import pytest

from t2lgepa.web import answer_question, build_results_payload


def _write_arm(results, arm, correct, task="gsm8k"):
    summary = {
        "record_type": "summary", "arm": arm, "task": task, "seed": 0, "fingerprint": "f",
        "n": len(correct), "score": sum(correct) / len(correct), "wall_seconds": 4.0,
        "generated_tokens": 100, "metric_calls": len(correct), "reflection_calls": 0,
        "model_id": "m", "adapter": "none", "decode": {}, "git_sha": "x",
        "vllm_version": "v", "torch_version": "t",
    }
    items = [
        {"record_type": "item", "id": f"x{i}", "correct": bool(c), "question": f"q{i}",
         "text": "t", "gold": "g"}
        for i, c in enumerate(correct)
    ]
    (results / f"{arm}_{task}_s0.jsonl").write_text(
        "\n".join(json.dumps(r) for r in [summary, *items]) + "\n"
    )


def test_payload_has_accuracy_cost_and_arms(tmp_path):
    results = tmp_path / "results"
    results.mkdir()
    _write_arm(results, "base", [True, False] * 10)
    _write_arm(results, "t2l_icl", [True] * 20)
    payload = build_results_payload(results)
    arms = {row["arm"] for row in payload["accuracy"]}
    assert arms == {"base", "t2l_icl"}
    assert payload["cost"] and payload["accuracy"][0]["n"] == 20


def test_payload_marks_missing_results_as_empty(tmp_path):
    payload = build_results_payload(tmp_path / "nope")
    assert payload["accuracy"] == [] and payload["cost"] == []


def test_answer_question_returns_three_surfaces(cfg, monkeypatch):
    calls = []

    class FakeClient:
        def __init__(self, *a, **k):
            pass

        def generate(self, prompts, model, temperature=0.0, max_tokens=512):
            calls.append(model)

            class G:
                text = f"ans-{model}"
                n_tokens = 2
                finish_reason = "stop"

            return [G() for _ in prompts]

    monkeypatch.setattr("t2lgepa.serve.VLLMClient", FakeClient)
    out = answer_question("2+2?", cfg, gepa_prompt="be careful")
    assert out["base"] and out["t2l"] and out["gepa"]
    assert any(c.startswith("t2l_") for c in calls)


def test_answer_question_rejects_empty_question(cfg):
    with pytest.raises(ValueError):
        answer_question("   ", cfg)
