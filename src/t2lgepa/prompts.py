"""Prompt builders. The answer format must match what `scoring.extract_answer` expects."""

from __future__ import annotations

from t2lgepa.data import Example

_GSM8K_RULES = (
    "Solve the problem. Show your reasoning, then write the final answer on its own line "
    "as '#### <number>'."
)
_ARC_RULES = (
    "Choose the correct option. Show your reasoning, then write the final line as "
    "'The answer is (X).' with X one of A, B, C, D."
)


def _options(example: Example) -> str:
    labels = "ABCD"
    return "\n".join(
        f"({labels[i]}) {text}" for i, text in enumerate(example.answers)
    )


def zero_shot(example: Example) -> str:
    if example.task == "gsm8k":
        return f"{_GSM8K_RULES}\n\nQuestion: {example.question}\nAnswer:"
    if example.task == "arc_challenge":
        return f"{_ARC_RULES}\n\nQuestion: {example.question}\n{_options(example)}\nAnswer:"
    raise ValueError(f"unknown task {example.task!r}")


def _demo(example: Example) -> str:
    if example.task == "gsm8k":
        answer = example.rationale or f"#### {example.answer}"
        if "####" not in answer:
            answer = f"{answer}\n#### {example.answer}"
        return f"Question: {example.question}\nAnswer: {answer}"
    return f"Question: {example.question}\n{_options(example)}\nAnswer: The answer is ({example.answer})."


def three_shot(example: Example, demos: list[Example]) -> str:
    return f"{demo_block(demos)}\n\n{zero_shot(example)}"


def demo_block(demos: list[Example]) -> str:
    return "\n\n".join(_demo(d) for d in demos)
