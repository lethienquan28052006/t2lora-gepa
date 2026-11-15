import json

from t2lgepa.records import RunKey, append_record, load_results


def test_append_and_load_roundtrip(tmp_path):
    path = tmp_path / "x.jsonl"
    append_record(path, {"record_type": "summary", "arm": "base", "score": 0.5})
    append_record(path, {"record_type": "item", "id": "gsm8k:test:0"})
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    assert [r["record_type"] for r in rows] == ["summary", "item"]


def test_load_results_keys_on_runkey(tmp_path):
    path = tmp_path / "x.jsonl"
    append_record(
        path,
        {"record_type": "summary", "arm": "base", "task": "gsm8k", "seed": 0,
         "fingerprint": "abc", "score": 0.5, "n": 5},
    )
    index = load_results(path)
    assert RunKey("base", "gsm8k", 0, "abc") in index
    assert index[RunKey("base", "gsm8k", 0, "abc")]["score"] == 0.5


def test_load_results_ignores_other_fingerprints(tmp_path):
    path = tmp_path / "x.jsonl"
    append_record(
        path,
        {"record_type": "summary", "arm": "base", "task": "gsm8k", "seed": 0,
         "fingerprint": "old", "score": 0.5, "n": 5},
    )
    assert RunKey("base", "gsm8k", 0, "new") not in load_results(path)
