from t2lgepa.data import Example
from t2lgepa.prompts import demo_block, three_shot, zero_shot


def _boolq(passage="the passage text", answer="yes"):
    return Example(id="boolq:test:0", task="boolq", question="is it true?",
                   answers=[], answer=answer, rationale=passage, split="test")


def test_boolq_zero_shot_includes_the_passage():
    prompt = zero_shot(_boolq())
    assert "the passage text" in prompt
    assert "is it true?" in prompt


def test_boolq_demo_includes_the_passage_and_a_plain_answer():
    prompt = demo_block([_boolq("first passage", "no")])
    assert "first passage" in prompt
    assert "Answer: no" in prompt
    assert "The answer is" not in prompt


def test_boolq_three_shot_keeps_every_passage():
    prompt = three_shot(_boolq("test passage"), [_boolq("demo passage", "no")])
    assert "demo passage" in prompt and "test passage" in prompt


def test_rules_for_every_supported_task():
    from t2lgepa.prompts import rules_for

    for task in ("gsm8k", "arc_challenge", "boolq", "hellaswag", "winogrande"):
        rules = rules_for(task)
        assert rules and rules[0].isupper()
    assert "####" in rules_for("gsm8k")
    assert "The answer is (X)" in rules_for("winogrande")
    assert "yes" in rules_for("boolq")
