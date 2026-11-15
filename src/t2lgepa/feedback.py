"""Textual feedback handed to GEPA's reflection LM, built from the train split only."""

from __future__ import annotations

from t2lgepa.data import Example


def build_feedback(example: Example, pred_text: str, correct: bool, max_chars: int = 1200) -> str:
    if example.split == "test":
        raise ValueError(
            f"refusing to build feedback for test example {example.id}: the test split is never "
            "visible to an optimizer"
        )
    verdict = "CORRECT" if correct else "INCORRECT"
    rationale = (example.rationale or "(no reference reasoning available)")[:max_chars]
    pred = (pred_text or "(empty generation)").strip()
    return (
        f"Verdict: {verdict}\n"
        f"Model output:\n{pred}\n\n"
        f"Gold final answer:\n#### {example.answer}\n\n"
        f"Reference reasoning:\n{rationale}"
    )
