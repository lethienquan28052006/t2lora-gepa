
from t2lgepa.data import Example
from t2lgepa.webapp.arms import ARMS, build_prompt, model_for


def gsm(text="2+2?", answer="4"):
    return Example(id="gsm8k:test:0", task="gsm8k", question=text, answers=[],
                   answer=answer, rationale="2+2=4\n#### 4", split="test")


def mcq():
    return Example(id="hellaswag:test:0", task="hellaswag", question="A man is",
                   answers=["running", "sleeping", "eating", "driving"], answer="A",
                   rationale=None, split="test")


def test_three_arms():
    assert ARMS == ("base", "t2l_icl", "gepa")


def test_base_prompt_has_rules_and_no_demos():
    prompt = build_prompt("base", gsm(), [], None)
    assert "#### <number>" in prompt
    assert "Question: 2+2?" in prompt


def test_icl_arm_has_demo_and_options():
    prompt = build_prompt("t2l_icl", mcq(), [mcq()], None)
    assert "The answer is (A)" in prompt
    assert "(D) driving" in prompt


def test_gepa_prompt_goes_first_and_keeps_options():
    prompt = build_prompt("gepa", mcq(), [], "THINK CAREFULLY")
    assert prompt.startswith("THINK CAREFULLY")
    assert "(B) sleeping" in prompt


def test_boolq_prompt_carries_the_passage():
    ex = Example(id="boolq:test:0", task="boolq", question="is it?", answers=[],
                 answer="yes", rationale="the passage", split="test")
    assert "the passage" in build_prompt("base", ex, [], None)


def test_model_names(cfg):
    assert model_for("base", "gsm8k", cfg) == cfg.model_id
    assert model_for("t2l_icl", "gsm8k", cfg) == "t2l_gsm8k"
    assert model_for("gepa", "gsm8k", cfg) == cfg.model_id


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
        (results / "gepa_gsm8k_s0_best_prompt.txt").write_text("GEPA RULES")
    return DemoService(load_config("configs/mistral.yaml"), results,
                       FakeClient(texts or {})), results


def test_compare_returns_three_arms_with_scores(tmp_path, monkeypatch):
    svc, _ = _service(tmp_path, {"mistralai/Mistral-7B-Instruct-v0.2": "#### 4",
                                 "t2l_gsm8k": "#### 5"})
    monkeypatch.setattr(svc, "_splits", lambda task: _stub_splits())
    out = svc.compare("gsm8k", question="2+2?", options=[], example_id="gsm8k:test:0")
    arms = {a["arm"]: a for a in out["arms"]}
    assert set(arms) == {"base", "t2l_icl", "gepa"}
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
    assert len(r.json()["arms"]) == 3
