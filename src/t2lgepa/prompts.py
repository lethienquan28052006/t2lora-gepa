"""Prompt builders. The answer format must match what `scoring.extract_answer` expects."""

from __future__ import annotations

from t2lgepa.data import Example

_GSM8K_RULES = (
    "Solve the problem. Show your reasoning, then write the final answer on its own line "
    "as '#### <number>'."
)
_ARC_RULES = (
    "Choose the correct option. Show your reasoning, then write the final line as "
    "'The answer is (X).' with X one of the given letters."
)
_BOOLQ_RULES = "Read the passage and answer the question with 'yes' or 'no'."
MCQ_TASKS = ("arc_challenge", "arc_easy", "openbookqa", "hellaswag", "piqa", "winogrande")


def _options(example: Example) -> str:
    labels = "ABCDEFGH"
    return "\n".join(
        f"({labels[i]}) {text}" for i, text in enumerate(example.answers)
    )


def rules_for(task: str) -> str:
    """The instruction block for a task, independent of any single example.

    GEPA optimises this text, so it must not carry a leftover answer format from another
    task: a GSM8K-shaped seed on a multiple-choice task poisons the whole search.
    """
    if task == "gsm8k":
        return _GSM8K_RULES
    if task in MCQ_TASKS:
        return _ARC_RULES
    if task == "boolq":
        return _BOOLQ_RULES
    raise ValueError(f"unknown task {task!r}")


def zero_shot(example: Example) -> str:
    if example.task == "gsm8k":
        return f"{_GSM8K_RULES}\n\nQuestion: {example.question}\nAnswer:"
    if example.task in MCQ_TASKS:
        return f"{_ARC_RULES}\n\nQuestion: {example.question}\n{_options(example)}\nAnswer:"
    if example.task == "boolq":
        return (
            f"{_BOOLQ_RULES}\n\nPassage: {example.rationale}\n\n"
            f"Question: {example.question}\nAnswer:"
        )
    raise ValueError(f"unknown task {example.task!r}")


def _demo(example: Example) -> str:
    if example.task == "gsm8k":
        answer = example.rationale or f"#### {example.answer}"
        if "####" not in answer:
            answer = f"{answer}\n#### {example.answer}"
        return f"Question: {example.question}\nAnswer: {answer}"
    if example.task == "boolq":
        return (
            f"Passage: {example.rationale}\n\nQuestion: {example.question}\n"
            f"Answer: {example.answer}"
        )
    return f"Question: {example.question}\n{_options(example)}\nAnswer: The answer is ({example.answer})."


def three_shot(example: Example, demos: list[Example]) -> str:
    return f"{demo_block(demos)}\n\n{zero_shot(example)}"


def demo_block(demos: list[Example]) -> str:
    return "\n\n".join(_demo(d) for d in demos)
