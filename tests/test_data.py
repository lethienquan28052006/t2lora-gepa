import json

import pytest

from t2lgepa.data import (
    Example,
    LeakageError,
    Splits,
    assert_no_leakage,
    load_task,
    make_splits,
    map_row,
)


def test_load_task_maps_gsm8k_fields():
    ex = load_task("gsm8k", "test", cache_dir="tests/fixtures")[0]
    assert ex.task == "gsm8k" and ex.answer and ex.rationale and ex.split == "test"


def test_make_splits_is_disjoint_and_deterministic(tmp_path):
    rows = [
        {
            "id": f"gsm8k:train:{i}",
            "task": "gsm8k",
            "question": f"q{i}",
            "answers": [],
            "answer": str(i),
            "rationale": None,
            "split": "train",
        }
        for i in range(600)
    ]
    (tmp_path / "gsm8k_train.jsonl").write_text("\n".join(json.dumps(r) for r in rows))
    (tmp_path / "gsm8k_test.jsonl").write_text(
        json.dumps({**rows[0], "id": "gsm8k:test:0", "split": "test",
                    "question": "a question only in the test split"})
    )

    s1 = make_splits(seed=0, cache_dir=tmp_path)
    s2 = make_splits(seed=0, cache_dir=tmp_path)

    assert [e.id for e in s1.train] == [e.id for e in s2.train]
    assert len(s1.train) == 150 and len(s1.pareto) == 300
    assert len({e.id for e in s1.train} | {e.id for e in s1.pareto}) == 450


def test_make_splits_differs_by_seed(tmp_path):
    rows = [
        {
            "id": f"gsm8k:train:{i}",
            "task": "gsm8k",
            "question": f"q{i}",
            "answers": [],
            "answer": str(i),
            "rationale": None,
            "split": "train",
        }
        for i in range(600)
    ]
    (tmp_path / "gsm8k_train.jsonl").write_text("\n".join(json.dumps(r) for r in rows))
    (tmp_path / "gsm8k_test.jsonl").write_text(
        json.dumps({**rows[0], "id": "gsm8k:test:0", "split": "test",
                    "question": "a question only in the test split"})
    )
    assert [e.id for e in make_splits(seed=0, cache_dir=tmp_path).train] != [
        e.id for e in make_splits(seed=1, cache_dir=tmp_path).train
    ]


def test_assert_no_leakage_raises_on_overlap():
    ex = Example(
        id="gsm8k:test:0", task="gsm8k", question="q", answers=[], answer="7",
        rationale=None, split="test",
    )
    with pytest.raises(LeakageError) as err:
        assert_no_leakage(Splits(train=[ex], pareto=[], test=[ex]))
    assert "gsm8k:test:0" in str(err.value)


def test_map_row_gsm8k_splits_rationale_and_answer():
    ex = map_row("gsm8k", "train", 3, {"question": "1+1?", "answer": "1+1 = 2\n#### 2"})
    assert ex.id == "gsm8k:train:3"
    assert ex.answer == "2" and ex.rationale == "1+1 = 2"
    assert ex.answers == []


def test_map_row_arc_returns_four_options():
    ex = map_row(
        "arc_challenge",
        "test",
        0,
        {
            "question": "Which?",
            "choices": {"label": ["A", "B", "C", "D"], "text": ["w", "x", "y", "z"]},
            "answerKey": "C",
        },
    )
    assert ex.answers == ["w", "x", "y", "z"]
    assert ex.answer == "C" and ex.rationale is None


def test_leakage_detected_by_question_text_even_with_different_ids():
    train = Example(id="gsm8k:train:1", task="gsm8k", question="Janet has 3 apples.",
                    answers=[], answer="7", rationale=None, split="train")
    test = Example(id="gsm8k:test:999", task="gsm8k", question="  janet has 3 apples. ",
                   answers=[], answer="7", rationale=None, split="test")
    with pytest.raises(LeakageError, match="question"):
        assert_no_leakage(Splits(train=[train], pareto=[], test=[test]))


def test_corrupt_cache_is_rebuilt_not_returned(tmp_path, monkeypatch):
    (tmp_path / "gsm8k_test.jsonl").write_text('{"id": "broken", "question": "trunc')
    rows = [{"question": "1+1?", "answer": "1+1 = 2\n#### 2"}]
    calls = {"n": 0}

    def fake_download(task, split):
        calls["n"] += 1
        return rows

    monkeypatch.setattr("t2lgepa.data._download", fake_download)
    examples = load_task("gsm8k", "test", cache_dir=tmp_path)
    assert calls["n"] == 1 and len(examples) == 1 and examples[0].answer == "2"


def test_cache_write_is_atomic(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "t2lgepa.data._download",
        lambda task, split: [{"question": "q", "answer": "#### 3"}],
    )
    load_task("gsm8k", "test", cache_dir=tmp_path)
    assert not list(tmp_path.glob("*.tmp"))
    assert (tmp_path / "gsm8k_test.jsonl").read_text().endswith("\n")


def test_make_splits_drops_train_items_that_duplicate_a_test_question(tmp_path):
    import json as _json

    rows = [
        {"id": f"gsm8k:train:{i}", "task": "gsm8k", "question": f"unique q{i}", "answers": [],
         "answer": str(i), "rationale": None, "split": "train"}
        for i in range(500)
    ]
    rows[0]["question"] = "duplicated question"
    (tmp_path / "gsm8k_train.jsonl").write_text("\n".join(_json.dumps(r) for r in rows))
    (tmp_path / "gsm8k_test.jsonl").write_text(_json.dumps(
        {**rows[1], "id": "gsm8k:test:0", "split": "test", "question": "duplicated question"}
    ))
    splits = make_splits(seed=0, cache_dir=tmp_path)
    assert all(ex.question != "duplicated question" for ex in splits.train + splits.pareto)
