import pytest

from t2lgepa.data import Example
from t2lgepa.feedback import build_feedback

EX = Example(
    id="gsm8k:train:0", task="gsm8k", question="Janet has 12 stickers and buys 6 more.",
    answers=[], answer="18",
    rationale="12 + 6 = 18. She has 18 stickers in total now.", split="train",
)
TEST_EX = Example(
    id="gsm8k:test:0", task="gsm8k", question="q", answers=[], answer="7",
    rationale="3 + 4 = 7", split="test",
)


def test_feedback_contains_output_gold_and_rationale():
    fb = build_feedback(EX, "#### 7", False)
    assert "#### 7" in fb and "#### 18" in fb and EX.rationale[:40] in fb


def test_feedback_truncates_rationale_but_keeps_gold_answer():
    fb = build_feedback(EX, "x", False, max_chars=120)
    assert len(fb) <= 600 and "#### 18" in fb


def test_feedback_refuses_non_train_example():
    with pytest.raises(ValueError):
        build_feedback(TEST_EX, "x", False)


def test_feedback_labels_correctness():
    assert "CORRECT" in build_feedback(EX, "#### 18", True)
    assert "INCORRECT" in build_feedback(EX, "#### 7", False)
