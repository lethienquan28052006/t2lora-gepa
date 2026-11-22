
from t2lgepa.data import Example
from t2lgepa.webapp.arms import ARMS, build_prompt, model_for


def gsm(text="2+2?", answer="4"):
    return Example(id="gsm8k:test:0", task="gsm8k", question=text, answers=[],
                   answer=answer, rationale="2+2=4\n#### 4", split="test")


def mcq():
    return Example(id="hellaswag:test:0", task="hellaswag", question="A man is",
                   answers=["running", "sleeping", "eating", "driving"], answer="A",
                   rationale=None, split="test")


def test_four_methods():
    assert ARMS == ("base", "t2l_icl", "gepa_3shot", "t2l_gepa_opt")


def test_base_prompt_has_rules_and_no_demos():
    prompt = build_prompt("base", gsm(), [], None)
    assert "#### <number>" in prompt
    assert "Question: 2+2?" in prompt


def test_icl_arm_has_demo_and_options():
    prompt = build_prompt("t2l_icl", mcq(), [mcq()], None)
    assert "The answer is (A)" in prompt
    assert "(D) driving" in prompt


def test_gepa_prompt_goes_first_and_keeps_options():
    prompt = build_prompt("gepa_3shot", mcq(), [], "THINK CAREFULLY")
    assert prompt.startswith("THINK CAREFULLY")
    assert "(B) sleeping" in prompt


def test_boolq_prompt_carries_the_passage():
    ex = Example(id="boolq:test:0", task="boolq", question="is it?", answers=[],
                 answer="yes", rationale="the passage", split="test")
    assert "the passage" in build_prompt("base", ex, [], None)


def test_model_names(cfg):
    assert model_for("base", "gsm8k", cfg) == cfg.model_id
    assert model_for("t2l_icl", "gsm8k", cfg) == "t2l_gsm8k"
    assert model_for("gepa_3shot", "gsm8k", cfg) == cfg.model_id


# --- service layer ---

class FakeClient:
    def __init__(self, texts):
        self.texts = texts
        self.calls = []

    def generate(self, prompts, model, temperature=0.0, max_tokens=512):
        self.calls.append(model)
        from t2lgepa.client import Generation
        text = self.texts.get(model, "#### 4")
        return [Generation(text=text, n_tokens=7, finish_reason="stop") for _ in prompts]


def _service(tmp_path, texts=None, gepa=True):
    from t2lgepa.config import load_config
    from t2lgepa.webapp.service import DemoService

    results = tmp_path / "results"
    results.mkdir()
    if gepa:
        (results / "gepa_3shot_gsm8k_s0_best_prompt.txt").write_text("GEPA RULES")
        (results / "t2l_gepa_opt_gsm8k_s0_best_prompt.txt").write_text("OPT RULES")
    return DemoService(load_config("configs/mistral.yaml"), results,
                       FakeClient(texts or {})), results


def test_compare_returns_four_arms_with_scores(tmp_path, monkeypatch):
    svc, _ = _service(tmp_path, {"mistralai/Mistral-7B-Instruct-v0.2": "#### 4",
                                 "t2l_gsm8k": "#### 5"})
    monkeypatch.setattr(svc, "_splits", lambda task: _stub_splits())
    out = svc.compare("gsm8k", question="2+2?", options=[], example_id="gsm8k:test:0")
    arms = {a["arm"]: a for a in out["arms"]}
    assert set(arms) == set(ARMS)
    assert arms["base"]["correct"] is True
    assert arms["t2l_icl"]["correct"] is False
    assert arms["base"]["latency_ms"] >= 0


def test_missing_gepa_prompt_drops_only_that_arm(tmp_path, monkeypatch):
    svc, _ = _service(tmp_path, gepa=False)
    monkeypatch.setattr(svc, "_splits", lambda task: _stub_splits())
    out = svc.compare("gsm8k", question="2+2?", options=[], example_id="gsm8k:test:0")
    assert {a["arm"] for a in out["arms"]} == {"base", "t2l_icl"}


def test_free_text_without_options_is_not_scored(tmp_path, monkeypatch):
    svc, _ = _service(tmp_path)
    monkeypatch.setattr(svc, "_splits", lambda task: _stub_splits())
    out = svc.compare("gsm8k", question="what is 1+1?", options=[], example_id=None)
    assert out["gold"] is None
    assert all(a["correct"] is None for a in out["arms"])


def _stub_splits():
    from types import SimpleNamespace

    ex = Example(id="gsm8k:test:0", task="gsm8k", question="2+2?", answers=[],
                 answer="4", rationale=None, split="test")
    return SimpleNamespace(train=[ex], pareto=[], test=[ex])


# --- HTTP layer ---

def _app(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient

    from t2lgepa.webapp.app import create_app

    svc, _ = _service(tmp_path)
    monkeypatch.setattr(svc, "_splits", lambda task: _stub_splits())
    _app.service = svc
    return TestClient(create_app(svc))


def test_index_is_served(tmp_path, monkeypatch):
    client = _app(tmp_path, monkeypatch)
    page = client.get("/")
    assert page.status_code == 200
    assert "Mistral" in page.text


def test_meta_lists_the_five_tasks(tmp_path, monkeypatch):
    body = _app(tmp_path, monkeypatch).get("/api/meta").json()
    assert body["tasks"] == ["gsm8k", "arc_challenge", "boolq", "hellaswag", "winogrande"]
    assert body["gepa"]["gsm8k"] is True


def test_compare_rejects_unknown_task(tmp_path, monkeypatch):
    r = _app(tmp_path, monkeypatch).post("/api/compare", json={"task": "mmlu", "question": "x"})
    assert r.status_code == 400


def test_compare_returns_arms(tmp_path, monkeypatch):
    r = _app(tmp_path, monkeypatch).post(
        "/api/compare", json={"task": "gsm8k", "question": "2+2?", "example_id": "gsm8k:test:0"})
    assert r.status_code == 200
    assert len(r.json()["arms"]) == 4


def test_all_four_methods_have_their_own_prompt_and_model(cfg, tmp_path, monkeypatch):
    assert ARMS == ("base", "t2l_icl", "gepa_3shot", "t2l_gepa_opt")
    assert "OPTIMIZE ON ADAPTER" in build_prompt("t2l_gepa_opt", gsm(), [],
                                                 "OPTIMIZE ON ADAPTER")
    assert model_for("t2l_gepa_opt", "gsm8k", cfg) == "t2l_gsm8k"

    svc, results = _service(tmp_path)
    (results / "t2l_gepa_opt_gsm8k_s0_best_prompt.txt").write_text("OPTIMIZE ON ADAPTER")
    monkeypatch.setattr(svc, "_splits", lambda task: _stub_splits())
    out = svc.compare("gsm8k", question="2+2?", options=[], example_id="gsm8k:test:0")
    assert {run["arm"] for run in out["arms"]} == set(ARMS)
    optimized = next(run for run in out["arms"] if run["arm"] == "t2l_gepa_opt")
    assert optimized["model"] == "t2l_gsm8k"
    assert "OPTIMIZE ON ADAPTER" in optimized["prompt"]


def test_only_the_searched_arm_whose_prompt_is_missing_is_dropped(tmp_path, monkeypatch):
    svc, results = _service(tmp_path)
    (results / "t2l_gepa_opt_gsm8k_s0_best_prompt.txt").unlink()
    monkeypatch.setattr(svc, "_splits", lambda task: _stub_splits())
    out = svc.compare("gsm8k", question="2+2?", options=[], example_id="gsm8k:test:0")
    assert {run["arm"] for run in out["arms"]} == {"base", "t2l_icl", "gepa_3shot"}


def test_index_has_exactly_the_two_approved_views(tmp_path, monkeypatch):
    page = _app(tmp_path, monkeypatch).get("/").text
    assert 'id="playground-view"' in page
    assert 'id="prompt-view"' in page
    assert page.count("data-view=") == 2
    assert "Inside T2L" not in page
    assert "A100" not in page and "GPU 7" not in page


def test_health_checks_that_all_required_models_are_really_served(tmp_path, monkeypatch):
    client = _app(tmp_path, monkeypatch)
    checked = []
    client.app_state = None
    _app.service.client.assert_ready = lambda: checked.append(True)
    response = client.get("/api/health")
    assert response.status_code == 200
    assert checked == [True]
    assert response.json()["ok"] is True


def test_comparison_returns_503_when_the_model_endpoint_is_down(tmp_path, monkeypatch):
    from t2lgepa.client import GenerationError

    def down(*args, **kwargs):
        raise GenerationError("endpoint offline")

    client = _app(tmp_path, monkeypatch)
    _app.service.client.generate = down
    response = client.post("/api/compare", json={"task": "gsm8k", "question": "hello"})
    assert response.status_code == 503
    assert "offline" in response.json()["detail"]


def test_skipped_searched_arms_are_reported_to_the_ui(tmp_path, monkeypatch):
    svc, results = _service(tmp_path)
    (results / "t2l_gepa_opt_gsm8k_s0_best_prompt.txt").unlink()
    monkeypatch.setattr(svc, "_splits", lambda task: _stub_splits())
    out = svc.compare("gsm8k", question="2+2?", example_id="gsm8k:test:0")
    assert out["skipped_arms"] == ["t2l_gepa_opt"]


def test_canonical_delta_is_computed_from_the_run_not_hard_coded(tmp_path):
    import json

    from t2lgepa.webapp.app import canonical_note

    for arm, score in (("base", 0.50), ("t2l_icl", 0.60), ("t2l_gepa_opt", 0.65)):
        (tmp_path / f"{arm}_gsm8k_s0.jsonl").write_text(json.dumps(
            {"arm": arm, "task": "gsm8k", "seed": 0, "n": 1000, "score": score}) + "\n")
    note = canonical_note(tmp_path, ["gsm8k"])
    assert "+5.0 pp" in note
    assert "t2l_gepa_opt" in note and "t2l_icl" in note
