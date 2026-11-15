import numpy as np

from t2lgepa.analysis import accuracy_table, bootstrap_ci, cost_table, paired_bootstrap


def test_bootstrap_ci_width_shrinks_with_n():
    lo1, hi1 = bootstrap_ci([True] * 55 + [False] * 45)
    lo2, hi2 = bootstrap_ci(([True] * 55 + [False] * 45) * 4)
    assert (hi2 - lo2) < (hi1 - lo1)


def test_paired_bootstrap_detects_shift():
    lo, _ = paired_bootstrap([True] * 60 + [False] * 40, [True] * 55 + [False] * 45)
    assert lo >= 0


def test_bootstrap_ci_is_seeded():
    data = [True, False] * 50
    assert bootstrap_ci(data) == bootstrap_ci(data)


def test_paired_bootstrap_zero_when_identical():
    data = [True, False] * 50
    lo, hi = paired_bootstrap(data, data)
    assert lo == 0.0 and hi == 0.0


def test_accuracy_table_has_a_row_per_arm_with_ci():
    rows = [
        {"arm": "base", "task": "gsm8k", "score": 0.553, "lo": 0.525, "hi": 0.580, "n": 1319},
        {"arm": "t2l_icl", "task": "gsm8k", "score": 0.569, "lo": 0.541, "hi": 0.596, "n": 1319},
    ]
    table = accuracy_table(rows)
    assert "| arm |" in table and "base" in table and "55.3%" in table
    assert table.count("\n") >= 3


def test_cost_table_reports_both_surfaces():
    rows = [
        {"arm": "t2l_icl", "task": "gsm8k", "wall_seconds": 12.0, "generated_tokens": 400000,
         "metric_calls": 1319, "reflection_calls": 0},
        {"arm": "gepa_3shot", "task": "gsm8k", "wall_seconds": 3600.0, "generated_tokens": 900000,
         "metric_calls": 1500, "reflection_calls": 41},
    ]
    table = cost_table(rows)
    assert "t2l_icl" in table and "gepa_3shot" in table and "reflection" in table.lower()


def test_analysis_module_is_numpy_only():
    import sys

    assert "pandas" not in sys.modules
    assert np is not None


def test_make_tables_script_writes_tables_from_results(tmp_path):
    import json

    from make_tables import main

    results = tmp_path / "results"
    results.mkdir()
    summary = {"record_type": "summary", "arm": "base", "task": "gsm8k", "seed": 0,
               "fingerprint": "f", "n": 2, "score": 0.5, "wall_seconds": 1.0,
               "generated_tokens": 10, "metric_calls": 2, "reflection_calls": 0}
    items = [{"record_type": "item", "id": "a", "correct": True},
             {"record_type": "item", "id": "b", "correct": False}]
    (results / "base_gsm8k_s0.jsonl").write_text(
        "\n".join(json.dumps(r) for r in [summary, *items]) + "\n"
    )
    out = tmp_path / "report"
    main(["--results", str(results), "--out", str(out)])
    assert "base" in (out / "accuracy.md").read_text()
    assert "base" in (out / "cost.md").read_text()


def test_accuracy_table_shows_paired_delta_vs_base():
    rows = [
        {"arm": "base", "task": "gsm8k", "score": 0.553, "lo": 0.525, "hi": 0.580, "n": 1319,
         "delta": None, "delta_lo": None, "delta_hi": None},
        {"arm": "t2l_icl", "task": "gsm8k", "score": 0.569, "lo": 0.541, "hi": 0.596, "n": 1319,
         "delta": 0.016, "delta_lo": -0.005, "delta_hi": 0.037},
    ]
    table = accuracy_table(rows)
    assert "vs base" in table and "+1.6" in table


def test_make_tables_computes_paired_delta(tmp_path):
    import json

    from make_tables import main

    results = tmp_path / "results"

    def write(arm, correct):
        results.mkdir(exist_ok=True)
        summary = {"record_type": "summary", "arm": arm, "task": "gsm8k", "seed": 0,
                   "fingerprint": "f", "n": len(correct), "score": sum(correct) / len(correct),
                   "wall_seconds": 1.0, "generated_tokens": 10, "metric_calls": len(correct),
                   "reflection_calls": 0}
        items = [{"record_type": "item", "id": f"x{i}", "correct": bool(c)} for i, c in
                 enumerate(correct)]
        (results / f"{arm}_gsm8k_s0.jsonl").write_text(
            "\n".join(json.dumps(r) for r in [summary, *items]) + "\n"
        )

    write("base", [True, False] * 25)
    write("t2l_icl", [True, True, False, True] * 12 + [True, False] * 2)
    out = tmp_path / "report"
    main(["--results", str(results), "--out", str(out)])
    assert "vs base" in (out / "accuracy.md").read_text()


def test_tables_module_collect_is_importable_from_the_package(tmp_path):
    import json

    from t2lgepa.tables import collect

    results = tmp_path / "results"
    results.mkdir()
    summary = {"record_type": "summary", "arm": "base", "task": "gsm8k", "seed": 0,
               "fingerprint": "f", "n": 2, "score": 0.5, "wall_seconds": 1.0,
               "generated_tokens": 10, "metric_calls": 2, "reflection_calls": 0}
    items = [{"record_type": "item", "id": "a", "correct": True},
             {"record_type": "item", "id": "b", "correct": False}]
    (results / "base_gsm8k_s0.jsonl").write_text(
        "\n".join(json.dumps(r) for r in [summary, *items]) + "\n"
    )
    accuracy, cost = collect(results)
    assert accuracy[0]["arm"] == "base" and cost[0]["metric_calls"] == 2
