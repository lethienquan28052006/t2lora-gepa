from t2lgepa.cases import pick_cases, render_cases

A = {  # t2l
    "x1": {"correct": True, "question": "q1", "text": "t2l ok", "gold": "7", "rationale": "3+4"},
    "x2": {"correct": False, "question": "q2", "text": "t2l bad", "gold": "8", "rationale": "4+4"},
    "x3": {"correct": True, "question": "q3", "text": "t2l ok", "gold": "9", "rationale": "5+4"},
    "x4": {"correct": False, "question": "q4", "text": "t2l bad", "gold": "10", "rationale": "5+5"},
}
B = {  # gepa
    "x1": {"correct": False, "question": "q1", "text": "gepa bad", "gold": "7", "rationale": "3+4"},
    "x2": {"correct": True, "question": "q2", "text": "gepa ok", "gold": "8", "rationale": "4+4"},
    "x3": {"correct": True, "question": "q3", "text": "gepa ok", "gold": "9", "rationale": "5+4"},
    "x4": {"correct": False, "question": "q4", "text": "gepa bad", "gold": "10", "rationale": "5+5"},
}


def test_buckets_are_disjoint_and_correct():
    got = pick_cases(A, B)
    assert set(got) == {"t2l_only", "gepa_only", "both_fail", "both_pass"}
    assert all(A[i]["correct"] and not B[i]["correct"] for i in got["t2l_only"])
    assert not (set(got["t2l_only"]) & set(got["both_pass"]))


def test_bucket_membership():
    got = pick_cases(A, B)
    assert got["t2l_only"] == ["x1"]
    assert got["gepa_only"] == ["x2"]
    assert got["both_fail"] == ["x4"]
    assert got["both_pass"] == ["x3"]


def test_k_limits_and_is_deterministic():
    got = pick_cases(A, B, k=1)
    assert got == pick_cases(A, B, k=1)
    assert all(len(v) <= 1 for v in got.values())


def test_render_cases_contains_both_outputs_and_gold():
    text = render_cases(pick_cases(A, B), A, B)
    assert "t2l ok" in text and "gepa bad" in text and "3+4" in text
    assert "t2l_only" in text
