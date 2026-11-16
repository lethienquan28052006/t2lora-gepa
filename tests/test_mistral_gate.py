from t2lgepa.mistral_gate import CHANCE, full_failures, smoke_failures


def test_collapsed_adapter_is_caught():
    base = {"gsm8k": 0.62, "boolq": 0.70}
    adapter = {"gsm8k": 0.04, "boolq": 0.51}
    assert len(smoke_failures(base, adapter)) == 2


def test_working_adapter_passes_even_when_below_base():
    base = {"gsm8k": 0.62, "boolq": 0.70}
    adapter = {"gsm8k": 0.55, "boolq": 0.72}
    assert smoke_failures(base, adapter) == []


def test_adapter_must_beat_chance_even_when_base_is_low():
    base = {"hellaswag": 0.10}
    adapter = {"hellaswag": 0.24}
    assert len(smoke_failures(base, adapter)) == 1


def test_direction_needs_four_of_five():
    assert full_failures({"a": 0.14, "b": 0.13, "c": 0.12, "d": 0.13, "e": 0.11}) == []
    assert len(full_failures({"a": 0.20, "b": 0.20, "c": -0.03, "d": -0.04, "e": 0.25})) == 1


def test_magnitude_outside_band_fails():
    assert full_failures({f"t{i}": 0.126 for i in range(5)}) == []
    assert len(full_failures({f"t{i}": 0.30 for i in range(5)})) == 1


def test_chance_by_task_shape():
    assert CHANCE["boolq"] == 0.5
    assert CHANCE["arc_challenge"] == 0.25
    assert CHANCE["gsm8k"] == 0.0


def test_adapter_alive_if_either_arm_is_healthy():
    base = {"winogrande": 0.65}
    zero = {"winogrande": 0.39}
    with_demos = {"winogrande": 0.71}
    assert smoke_failures(base, zero, with_demos) == []


def test_both_arms_low_means_collapsed():
    base = {"winogrande": 0.65}
    zero = {"winogrande": 0.30}
    with_demos = {"winogrande": 0.32}
    assert len(smoke_failures(base, zero, with_demos)) == 1
