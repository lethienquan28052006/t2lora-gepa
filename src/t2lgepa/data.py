"""Canonical example schema, task loading (cached as JSONL) and leakage-safe splits."""

from __future__ import annotations

import json
import random
from dataclasses import dataclass
from pathlib import Path

TASKS = ("gsm8k", "arc_challenge")


@dataclass(frozen=True)
class Example:
    id: str
    task: str
    question: str
    answers: list[str]
    answer: str
    rationale: str | None
    split: str


@dataclass(frozen=True)
class Splits:
    train: list[Example]
    pareto: list[Example]
    test: list[Example]


class LeakageError(RuntimeError):
    pass


def map_row(task: str, split: str, index: int, row: dict) -> Example:
    if task == "gsm8k":
        rationale, _, answer = row["answer"].rpartition("####")
        return Example(
            id=f"gsm8k:{split}:{index}",
            task=task,
            question=row["question"],
            answers=[],
            answer=answer.strip() or rationale.strip(),
            rationale=rationale.strip() or None,
            split=split,
        )
    if task in ("arc_challenge", "arc_easy"):
        labels = list(row["choices"]["label"])
        texts = list(row["choices"]["text"])
        answer = row["answerKey"]
        if answer not in labels and answer.isdigit():
            answer = labels[int(answer)]
        return Example(
            id=f"{task}:{split}:{index}",
            task=task,
            question=row["question"],
            answers=texts,
            answer=answer,
            rationale=None,
            split=split,
        )
    if task == "boolq":
        return Example(
            id=f"{task}:{split}:{index}",
            task=task,
            question=row["question"],
            answers=[],
            answer="yes" if row["answer"] else "no",
            rationale=row.get("passage"),
            split=split,
        )
    if task == "piqa":
        return Example(
            id=f"{task}:{split}:{index}",
            task=task,
            question=row["goal"],
            answers=[row["sol1"], row["sol2"]],
            answer="AB"[int(row["label"])],
            rationale=None,
            split=split,
        )
    if task == "winogrande":
        return Example(
            id=f"{task}:{split}:{index}",
            task=task,
            question=row["sentence"],
            answers=[row["option1"], row["option2"]],
            answer="AB"[int(row["answer"]) - 1],
            rationale=None,
            split=split,
        )
    if task == "hellaswag":
        return Example(
            id=f"{task}:{split}:{index}",
            task=task,
            question=row["ctx"],
            answers=[e.strip() for e in row["endings"]],
            answer="ABCD"[int(row["label"])],
            rationale=None,
            split=split,
        )
    if task == "openbookqa":
        return Example(
            id=f"{task}:{split}:{index}",
            task=task,
            question=row["question_stem"],
            answers=list(row["choices"]["text"]),
            answer=row["answerKey"],
            rationale=None,
            split=split,
        )
    raise ValueError(f"unknown task {task!r}")


def _cache_path(cache_dir: str | Path, task: str, split: str) -> Path:
    return Path(cache_dir) / f"{task}_{split}.jsonl"


def _download(task: str, split: str) -> list[dict]:
    from datasets import load_dataset

    if task == "gsm8k":
        ds = load_dataset("openai/gsm8k", "main", split=split)
    elif task == "arc_challenge":
        ds = load_dataset("allenai/ai2_arc", "ARC-Challenge", split=split)
    elif task == "arc_easy":
        ds = load_dataset("allenai/ai2_arc", "ARC-Easy", split=split)
    elif task == "boolq":
        ds = load_dataset("google/boolq", split=split)
    elif task == "piqa":
        ds = load_dataset("ybisk/piqa", split=split)
    elif task == "winogrande":
        ds = load_dataset("allenai/winogrande", "winogrande_xl", split=split)
    elif task == "hellaswag":
        ds = load_dataset("Rowan/hellaswag", split=split)
    elif task == "openbookqa":
        ds = load_dataset("allenai/openbookqa", "main", split=split)
    else:
        raise ValueError(f"unknown task {task!r}")
    return list(ds)


def load_task(task: str, split: str, cache_dir: str = "data") -> list[Example]:
    path = _cache_path(cache_dir, task, split)
    examples = _read_cache(path)
    if examples is None:
        examples = _rebuild_cache(task, split, path)
    return examples


def _read_cache(path: Path) -> list[Example] | None:
    if not path.exists():
        return None
    out: list[Example] = []
    try:
        for line in path.read_text().splitlines():
            if line.strip():
                out.append(Example(**json.loads(line)))
    except (json.JSONDecodeError, TypeError):
        return None
    return out


def _rebuild_cache(task: str, split: str, path: Path) -> list[Example]:
    rows = _download(task, split)
    path.parent.mkdir(parents=True, exist_ok=True)
    examples = [map_row(task, split, i, row) for i, row in enumerate(rows)]
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(
        "\n".join(json.dumps(ex.__dict__, ensure_ascii=False) for ex in examples) + "\n"
    )
    tmp.replace(path)
    return examples


def make_splits(
    task: str = "gsm8k",
    n_train: int = 150,
    n_pareto: int = 300,
    seed: int = 0,
    cache_dir: str = "data",
) -> Splits:
    pool = list(load_task(task, "train", cache_dir=cache_dir))
    test = load_task(task, "test", cache_dir=cache_dir)
    test_questions = {" ".join(ex.question.lower().split()) for ex in test}
    pool = [ex for ex in pool if " ".join(ex.question.lower().split()) not in test_questions]
    random.Random(seed).shuffle(pool)
    if len(pool) < n_train + n_pareto:
        raise ValueError(f"{task} train has {len(pool)} usable items, need {n_train + n_pareto}")
    splits = Splits(
        train=pool[:n_train],
        pareto=pool[n_train : n_train + n_pareto],
        test=test,
    )
    assert_no_leakage(splits)
    return splits


def assert_no_leakage(splits: Splits) -> None:
    train = {ex.id for ex in splits.train}
    pareto = {ex.id for ex in splits.pareto}
    test = {ex.id for ex in splits.test}
    bad = sorted((train & test) | (pareto & test) | (train & pareto))
    if bad:
        raise LeakageError(f"ids appear in more than one split: {bad[:10]}")

    def norm(question: str) -> str:
        return " ".join(question.lower().split())

    train_q = {norm(ex.question) for ex in splits.train}
    pareto_q = {norm(ex.question) for ex in splits.pareto}
    test_q = {norm(ex.question) for ex in splits.test}
    shared_q = sorted((train_q & test_q) | (pareto_q & test_q) | (train_q & pareto_q))
    if shared_q:
        raise LeakageError(
            f"the same question appears in more than one split: {[q[:60] for q in shared_q[:5]]}"
        )
