from demo_smoke import prompt_for, sample_for

from t2lgepa.prompts import rules_for, zero_shot


def test_manifest_prompt_matches_the_harness_zero_shot():
    ex = sample_for("gsm8k")
    version = {"prompt": {"instruction": rules_for("gsm8k"), "demo_block": None}}
    assert prompt_for(version, ex) == zero_shot(ex)


def test_manifest_prompt_with_demos_matches_three_shot():
    ex = sample_for("winogrande")
    demos = [sample_for("winogrande")]
    version = {"prompt": {"instruction": rules_for("winogrande"),
                          "demo_block": "\n\n".join(
                              f"Question: {d.question}\nAnswer: The answer is (A)." for d in demos)}}
    assert prompt_for(version, ex).endswith(zero_shot(ex))
    assert prompt_for(version, ex).count("Question:") == 2


def test_missing_instruction_is_refused_not_silently_dropped():
    import pytest

    ex = sample_for("gsm8k")
    with pytest.raises(ValueError):
        prompt_for({"version_id": "v2-gepa-gsm8k",
                    "prompt": {"instruction": None, "demo_block": "demo"}}, ex)
