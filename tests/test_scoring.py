import pytest

from t2lgepa.data import Example
from t2lgepa.scoring import extract_answer, normalize_number, score

GSM8K_EX = Example(
    id="gsm8k:test:0", task="gsm8k", question="q", answers=[], answer="18",
    rationale="12 + 6 = 18", split="test",
)
ARC_EX = Example(
    id="arc_challenge:test:0", task="arc_challenge", question="q",
    answers=["w", "x", "y", "z"], answer="B", rationale=None, split="test",
)


@pytest.mark.parametrize(
    "text,expected",
    [
        ("so the answer is\n#### 18", "18"),
        ("reasoning...\n#### 1,200", "1200"),
        ("blah #### -3.5.", "-3.5"),
        ("#### $720", "720"),
        ("no marker at all 42", None),
        ("", None),
    ],
)
def test_extract_gsm8k(text, expected):
    assert extract_answer(text, "gsm8k") == expected


def test_extract_prefers_last_marker():
    assert extract_answer("#### 5 then corrected #### 7", "gsm8k") == "7"


def test_score_empty_prediction_is_false_not_an_error():
    assert score(None, GSM8K_EX) is False and score("", GSM8K_EX) is False


def test_score_gsm8k_numeric_equivalence():
    assert score("18", GSM8K_EX) is True
    assert score("18.0", GSM8K_EX) is True
    assert score("1,800", GSM8K_EX) is False


def test_extract_arc_letter():
    assert extract_answer("The answer is (B).", "arc_challenge") == "B"
    assert extract_answer("no letter", "arc_challenge") is None


def test_extract_arc_falls_back_to_bare_letter():
    assert extract_answer("After checking, the result is C", "arc_challenge") == "C"


def test_arc_prompt_with_options_does_not_match_option_text():
    text = "Options: (A) w   (B) x   (C) y   (D) z\nAnswer: B"
    assert extract_answer(text, "arc_challenge") == "B"


def test_normalize_number_rejects_non_numbers():
    assert normalize_number("18") == "18"
    assert normalize_number("abc") is None
