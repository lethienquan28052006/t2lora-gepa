from t2lgepa.gate import check_gate


def test_full_gate_tolerance_is_three_points():
    ok, msgs = check_gate(
        {"base": 0.5527, "t2l_icl": 0.5989},
        {"base": 0.5527, "t2l_icl": 0.5689},
        3.0,
    )
    assert ok is False and any("t2l_icl" in m for m in msgs)


def test_smoke_gate_tolerance_is_six_points():
    ok, _ = check_gate({"base": 0.60}, {"base": 0.5527}, 6.0)
    assert ok is True


def test_gate_reports_missing_arms():
    ok, msgs = check_gate({"base": 0.55}, {"base": 0.5527, "t2l_icl": 0.5689}, 3.0)
    assert ok is False and any("t2l_icl" in m for m in msgs)


def test_gate_passes_when_every_arm_is_inside_tolerance():
    ok, msgs = check_gate({"base": 0.5627}, {"base": 0.5527}, 3.0)
    assert ok is True and msgs == []
