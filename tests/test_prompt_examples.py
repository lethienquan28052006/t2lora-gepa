import json

import pytest
from fastapi.testclient import TestClient

from t2lgepa.data import Example, Splits
from t2lgepa.webapp.app import create_app
from t2lgepa.webapp.examples import PromptExampleLibrary
from t2lgepa.webapp.service import DemoService

PAIRS = (
    ("arc_challenge", "gepa_3shot", "icl3"),
    ("arc_challenge", "t2l_gepa_opt", "t2l_icl"),
    ("boolq", "t2l_gepa_opt", "t2l_icl"),
    ("hellaswag", "t2l_gepa_opt", "t2l_icl"),
)


def _write_prompts(results, task, arm, changed=True):
    stem = results / f"{arm}_{task}_s0"
    seed = "Follow the original instruction"
    best = "Use the evidence and follow the exact answer format" if changed else seed
    (results / f"{stem.name}_seed_prompt.txt").write_text(seed + "\n")
    (results / f"{stem.name}_best_prompt.txt").write_text(best + "\n")


def _item(task, arm, index, correct, pred=None, suffix=""):
    answer = "A" if task != "boolq" else "yes"
    return {
        "record_type": "item", "arm": arm, "task": task, "seed": 0,
        "fingerprint": "test-fingerprint", "id": f"{task}:test:{index}",
        "question": f"Stored question {index}{suffix}",
        "text": f"Generation from {arm} for item {index}{suffix}",
        "pred": pred or (answer if correct else "wrong"),
        "gold": answer, "rationale": "Stored passage" if task == "boolq" else None,
        "correct": correct, "finish_reason": "stop",
    }


def _write_records(results, task, arm, rows):
    summary = {
        "record_type": "summary", "arm": arm, "task": task, "seed": 0,
        "fingerprint": "test-fingerprint", "n": len(rows), "score": 0.5,
    }
    path = results / f"{arm}_{task}_s0.jsonl"
    path.write_text("\n".join(json.dumps(row) for row in [summary, *rows]) + "\n")


def _make_changed_pair(results, task, arm, baseline_arm, count=1):
    _write_prompts(results, task, arm)
    before = [_item(task, baseline_arm, i, False) for i in range(count)]
    after = [_item(task, arm, i, True) for i in range(count)]
    _write_records(results, task, baseline_arm, before)
    _write_records(results, task, arm, after)


def test_stories_use_matching_baselines_and_only_real_wrong_to_right_cases(tmp_path):
    for pair in PAIRS:
        _make_changed_pair(tmp_path, *pair)

    stories = PromptExampleLibrary(tmp_path).stories()

    assert [(s["task"], s["arm"], s["baseline_arm"]) for s in stories] == list(PAIRS)
    assert all(len(s["changes"]) >= 2 for s in stories)
    assert stories[0]["seed"] == "Follow the original instruction"
    assert stories[0]["best"] == "Use the evidence and follow the exact answer format"
    case = stories[0]["cases"][0]
    assert case["before"] == {
        "text": "Generation from icl3 for item 0", "pred": "wrong", "correct": False,
    }
    assert case["after"]["correct"] is True
    assert case["gold"] == "A"


def test_unchanged_prompt_never_becomes_an_optimization_story(tmp_path):
    task, arm, baseline = PAIRS[0]
    _make_changed_pair(tmp_path, task, arm, baseline)
    _write_prompts(tmp_path, task, arm, changed=False)

    assert PromptExampleLibrary(tmp_path).stories() == []


def test_cases_are_deterministic_limited_and_exclude_other_transitions(tmp_path):
    task, arm, baseline = PAIRS[0]
    _write_prompts(tmp_path, task, arm)
    before = [
        _item(task, baseline, 3, False), _item(task, baseline, 1, True),
        _item(task, baseline, 0, False), _item(task, baseline, 2, False),
        _item(task, baseline, 4, False),
    ]
    after = [
        _item(task, arm, 0, True), _item(task, arm, 1, False),
        _item(task, arm, 2, True), _item(task, arm, 3, True),
        _item(task, arm, 4, False),
    ]
    _write_records(tmp_path, task, baseline, before)
    _write_records(tmp_path, task, arm, after)

    stories = PromptExampleLibrary(tmp_path).stories()

    assert [case["id"] for case in stories[0]["cases"]] == [
        f"{task}:test:0", f"{task}:test:2", f"{task}:test:3",
    ]
    assert all(case["before"]["correct"] is False for case in stories[0]["cases"])
    assert all(case["after"]["correct"] is True for case in stories[0]["cases"])


def test_duplicate_records_use_latest_values_for_both_arms(tmp_path):
    task, arm, baseline = PAIRS[0]
    _write_prompts(tmp_path, task, arm)
    _write_records(tmp_path, task, baseline, [
        _item(task, baseline, 0, False, suffix=" old"),
        _item(task, baseline, 0, True, suffix=" latest"),
        _item(task, baseline, 1, False),
    ])
    _write_records(tmp_path, task, arm, [
        _item(task, arm, 0, True),
        _item(task, arm, 1, False, suffix=" old"),
        _item(task, arm, 1, True, suffix=" latest"),
    ])

    cases = PromptExampleLibrary(tmp_path).stories()[0]["cases"]

    assert [case["id"] for case in cases] == [f"{task}:test:1"]
    assert cases[0]["before"]["text"].endswith("item 1")
    assert cases[0]["after"]["text"].endswith("latest")


def test_lookup_enriches_options_and_boolq_passage_with_dataset_values(tmp_path):
    def lookup(task, example_id):
        if task == "boolq":
            return {"question": "Dataset question", "options": [],
                    "passage": "Dataset passage", "gold": "yes"}
        return {"question": "Dataset science question", "options": ["one", "two"],
                "passage": None, "gold": "A"}

    _make_changed_pair(tmp_path, *PAIRS[0])
    _make_changed_pair(tmp_path, *PAIRS[2])
    stories = PromptExampleLibrary(tmp_path, item_lookup=lookup).stories()

    arc_case = stories[0]["cases"][0]
    assert arc_case["question"] == "Dataset science question"
    assert arc_case["options"] == ["one", "two"]
    boolq_case = stories[1]["cases"][0]
    assert boolq_case["question"] == "Dataset question"
    assert boolq_case["passage"] == "Dataset passage"


def test_missing_lookup_and_corrupt_other_story_fall_back_without_global_failure(tmp_path):
    _make_changed_pair(tmp_path, *PAIRS[0])
    _make_changed_pair(tmp_path, *PAIRS[2])
    corrupt = tmp_path / "t2l_gepa_opt_boolq_s0.jsonl"
    corrupt.write_text('{"record_type":"summary"}\n{not json}\n')

    stories = PromptExampleLibrary(tmp_path, item_lookup=lambda *_: None).stories()

    assert [(story["task"], story["arm"]) for story in stories] == [
        ("arc_challenge", "gepa_3shot"),
    ]
    case = stories[0]["cases"][0]
    assert case["question"] == "Stored question 0"
    assert case["options"] == []
    assert case["passage"] is None


@pytest.mark.parametrize("malformed_line", ["null", "[]", '"corrupt"'])
def test_non_object_json_is_isolated_to_the_corrupt_story(tmp_path, malformed_line):
    _make_changed_pair(tmp_path, *PAIRS[0])
    _make_changed_pair(tmp_path, *PAIRS[2])
    (tmp_path / "t2l_gepa_opt_boolq_s0.jsonl").write_text(
        '{"record_type":"summary"}\n' + malformed_line + "\n"
    )

    stories = PromptExampleLibrary(tmp_path).stories()

    assert [(story["task"], story["arm"]) for story in stories] == [
        ("arc_challenge", "gepa_3shot"),
    ]


def test_demo_service_test_item_returns_stored_fields_or_none(cfg, tmp_path):
    service = DemoService(cfg, tmp_path, object())
    example = Example(
        id="boolq:test:7", task="boolq", question="Is this supported?",
        answers=[], answer="yes", rationale="A supporting passage", split="test",
    )
    service._split_cache["boolq"] = Splits(train=[], pareto=[], test=[example])

    assert service.test_item("boolq", example.id) == {
        "id": example.id, "task": "boolq", "question": "Is this supported?",
        "options": [], "passage": "A supporting passage", "gold": "yes",
    }
    assert service.test_item("boolq", "boolq:test:missing") is None
    with pytest.raises(ValueError, match="unknown task"):
        service.test_item("not-a-task", "anything")


def test_api_serves_real_story_and_transitions(tmp_path):
    _make_changed_pair(tmp_path, *PAIRS[0])
    client = TestClient(create_app(object(), results_dir=tmp_path))

    response = client.get("/api/prompt-examples")

    assert response.status_code == 200
    story = response.json()["stories"][0]
    assert story["baseline_arm"] == "icl3"
    assert story["cases"][0]["before"]["correct"] is False
    assert story["cases"][0]["after"]["correct"] is True


def test_api_incomplete_gallery_does_not_break_meta_or_raw_history(cfg, tmp_path):
    task, arm, _ = PAIRS[0]
    _write_prompts(tmp_path, task, arm)
    (tmp_path / f"{arm}_{task}_s0_candidates.json").write_text("[]\n")
    service = DemoService(cfg, tmp_path, object())
    client = TestClient(create_app(service, results_dir=tmp_path))

    assert client.get("/api/prompt-examples").json() == {"stories": []}
    assert client.get("/api/meta").status_code == 200
    history = client.get("/api/prompt-library", params={"task": task, "arm": arm})
    assert history.status_code == 200
    assert history.json()["seed"] == "Follow the original instruction"


def test_api_non_object_json_does_not_suppress_healthy_story(tmp_path):
    _make_changed_pair(tmp_path, *PAIRS[0])
    _make_changed_pair(tmp_path, *PAIRS[2])
    (tmp_path / "t2l_gepa_opt_boolq_s0.jsonl").write_text(
        '{"record_type":"summary"}\nnull\n[]\n'
    )
    client = TestClient(create_app(object(), results_dir=tmp_path))

    response = client.get("/api/prompt-examples")

    assert response.status_code == 200
    assert [story["id"] for story in response.json()["stories"]] == [
        "gepa-arc-challenge",
    ]
