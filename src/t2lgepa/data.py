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
    if task == "arc_challenge":
        labels = list(row["choices"]["label"])
        texts = list(row["choices"]["text"])
        answer = row["answerKey"]
        if answer not in labels and answer.isdigit():
            answer = labels[int(answer)]
        return Example(
            id=f"arc_challenge:{split}:{index}",
            task=task,
            question=row["question"],
            answers=texts,
            answer=answer,
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
    else:
        raise ValueError(f"unknown task {task!r}")
    return list(ds)


def load_task(task: str, split: str, cache_dir: str = "data") -> list[Example]:
    path = _cache_path(cache_dir, task, split)
    if not path.exists():
        rows = _download(task, split)
        path.parent.mkdir(parents=True, exist_ok=True)
        examples = [map_row(task, split, i, row) for i, row in enumerate(rows)]
        path.write_text(
            "\n".join(json.dumps(ex.__dict__, ensure_ascii=False) for ex in examples) + "\n"
        )
    out = []
    for line in path.read_text().splitlines():
        if line.strip():
            out.append(Example(**json.loads(line)))
    return out


def make_splits(
    task: str = "gsm8k",
    n_train: int = 150,
    n_pareto: int = 300,
    seed: int = 0,
    cache_dir: str = "data",
) -> Splits:
    pool = list(load_task(task, "train", cache_dir=cache_dir))
    random.Random(seed).shuffle(pool)
    if len(pool) < n_train + n_pareto:
        raise ValueError(f"{task} train has {len(pool)} items, need {n_train + n_pareto}")
    splits = Splits(
        train=pool[:n_train],
        pareto=pool[n_train : n_train + n_pareto],
        test=load_task(task, "test", cache_dir=cache_dir),
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
