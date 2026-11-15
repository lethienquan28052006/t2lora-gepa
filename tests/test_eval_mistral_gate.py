import eval_mistral_gate as gate


def _rows(deltas):
    rows = [{"arm": "base", "task": t, "delta": None} for t in deltas]
    rows += [{"arm": "t2l_icl", "task": t, "delta": d} for t, d in deltas.items()]
    return rows, []


def test_deltas_are_read_from_t2l_icl_rows():
    rows, cost = _rows({"gsm8k": 0.03, "boolq": 0.10})
    assert gate.deltas(rows) == {"gsm8k": 0.03, "boolq": 0.10}


def test_main_passes_when_gates_hold(monkeypatch, tmp_path):
    monkeypatch.setattr(gate, "collect", lambda path: _rows(
        {t: 0.126 for t in ("gsm8k", "arc_challenge", "boolq", "hellaswag", "winogrande")}))
    assert gate.main(["--results", str(tmp_path)]) == 0


def test_main_fails_when_the_mean_is_far_from_published(monkeypatch, tmp_path):
    monkeypatch.setattr(gate, "collect", lambda path: _rows(
        {t: 0.40 for t in ("gsm8k", "arc_challenge", "boolq", "hellaswag", "winogrande")}))
    assert gate.main(["--results", str(tmp_path)]) == 1
