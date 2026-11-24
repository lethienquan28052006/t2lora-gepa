"""Demo service: sample an item, run the three surfaces, score when a gold answer exists."""

from __future__ import annotations

import random
import time
from dataclasses import dataclass
from pathlib import Path

from t2lgepa.client import VLLMClient
from t2lgepa.config import Config
from t2lgepa.data import Example, Splits, make_splits
from t2lgepa.scoring import extract_answer, score
from t2lgepa.webapp.arms import ARMS, SEARCHED_ARMS, build_prompt, model_for

TASKS = ("gsm8k", "arc_challenge", "boolq", "hellaswag", "winogrande")


@dataclass
class _Run:
    arm: str
    text: str
    pred: str | None
    correct: bool | None
    latency_ms: int
    tokens: int
    prompt: str
    model: str


class DemoService:
    def __init__(self, cfg: Config, results_dir: str | Path, client: VLLMClient) -> None:
        self.cfg = cfg
        self.results_dir = Path(results_dir)
        self.client = client
        self._split_cache: dict[str, Splits] = {}

    def _splits(self, task: str) -> Splits:
        if task not in self._split_cache:
            self._split_cache[task] = make_splits(task, cache_dir=self.cfg.cache_dir)
        return self._split_cache[task]

    def demos(self, task: str) -> list[Example]:
        return self._splits(task).train[:3]

    def gepa_prompt(self, task: str, arm: str = "gepa_3shot") -> str | None:
        path = self.results_dir / f"{arm}_{task}_s0_best_prompt.txt"
        if not path.exists():
            return None
        text = path.read_text()
        return text.removesuffix("\n")

    def meta(self) -> dict:
        return {
            "model": self.cfg.model_id,
            "tasks": list(self.cfg.tasks),
            "arms": list(ARMS),
            "gepa": {task: self.gepa_prompt(task) is not None for task in self.cfg.tasks},
        }

    def sample(self, task: str) -> dict:
        if task not in self.cfg.tasks:
            raise ValueError(f"unknown task {task!r}")
        example = random.choice(self._splits(task).test)
        return self.test_item(task, example.id)

    def test_item(self, task: str, example_id: str) -> dict | None:
        if task not in self.cfg.tasks:
            raise ValueError(f"unknown task {task!r}")
        example = next((item for item in self._splits(task).test if item.id == example_id), None)
        if example is None:
            return None
        return {
            "id": example.id,
            "task": example.task,
            "question": example.question,
            "options": example.answers,
            "passage": example.rationale if example.task == "boolq" else None,
            "gold": example.answer,
        }

    def _example(
        self, task: str, question: str, options: list[str], passage: str | None,
        example_id: str | None,
    ) -> tuple[Example, bool]:
        """Return the example and whether it is a scored test item."""
        if example_id:
            for candidate in self._splits(task).test:
                if candidate.id == example_id:
                    return candidate, True
        return (
            Example(
                id=example_id or f"{task}:custom",
                task=task,
                question=question,
                answers=[o for o in options if o.strip()],
                answer="",
                rationale=passage,
                split="custom",
            ),
            False,
        )

    def compare(
        self,
        task: str,
        question: str = "",
        options: list[str] | None = None,
        passage: str | None = None,
        example_id: str | None = None,
    ) -> dict:
        if task not in self.cfg.tasks:
            raise ValueError(f"unknown task {task!r}")
        example, scored = self._example(task, question, options or [], passage, example_id)
        demos = self.demos(task)
        prompts = {arm: self.gepa_prompt(task, arm) for arm in SEARCHED_ARMS}

        runs: list[_Run] = []
        skipped_arms: list[str] = []
        for arm in ARMS:
            try:
                prompt = build_prompt(arm, example, demos, prompts.get(arm))
            except ValueError:
                skipped_arms.append(arm)
                continue
            started = time.perf_counter()
            generation = self.client.generate(
                [prompt], model=model_for(arm, task, self.cfg),
                temperature=0.0, max_tokens=self.cfg.max_tokens,
            )[0]
            latency_ms = int((time.perf_counter() - started) * 1000)
            pred = extract_answer(generation.text, task)
            runs.append(
                _Run(
                    arm=arm,
                    text=generation.text,
                    pred=pred,
                    correct=score(pred, example) if scored else None,
                    latency_ms=latency_ms,
                    tokens=generation.n_tokens,
                    prompt=prompt,
                    model=model_for(arm, task, self.cfg),
                )
            )

        return {
            "task": task,
            "question": example.question,
            "options": example.answers,
            "passage": example.rationale if task == "boolq" else None,
            "gold": example.answer if scored else None,
            "arms": [run.__dict__ for run in runs],
            "skipped_arms": skipped_arms,
        }
