"""GEPA arm: a metered adapter with a hard metric-call ceiling."""

from __future__ import annotations

import json
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from t2lgepa.client import VLLMClient
from t2lgepa.config import Config
from t2lgepa.data import Example
from t2lgepa.feedback import build_feedback
from t2lgepa.prompts import _options
from t2lgepa.scoring import extract_answer, score


class BudgetExhausted(RuntimeError):
    """A metric call was about to exceed the run's budget. The engine overshot."""


class GepaGateFailed(RuntimeError):
    pass


class MeteredMetric:
    def __init__(self, metric_fn: Callable[[str | None, Example], bool], limit: int) -> None:
        self.metric_fn = metric_fn
        self.limit = limit
        self.calls = 0

    @property
    def remaining(self) -> int:
        return self.limit - self.calls

    def reserve(self, n: int) -> None:
        if self.calls + n > self.limit:
            raise BudgetExhausted(
                f"metric calls would reach {self.calls + n}, budget is {self.limit}"
            )

    def __call__(self, example: Example, pred: str | None) -> float:
        self.reserve(1)
        self.calls += 1
        return 1.0 if self.metric_fn(pred, example) else 0.0


@dataclass(frozen=True)
class GepaResult:
    best_prompt: str
    pareto_score: float
    curve: list[tuple[int, float]]
    metric_calls: int
    reflection_calls: int
    wall_seconds: float
    accepted_candidates: int
    partial: bool = False


def _compose(instruction: str, example: Example, few_shot_block: str | None) -> str:
    parts = [few_shot_block, instruction]
    parts.append(f"Question: {example.question}")
    if example.task == "arc_challenge":
        parts.append(_options(example))
    parts.append("Answer:")
    return "\n\n".join(part for part in parts if part)


class _Adapter:
    # GEPA treats this as optional, but the engine does `adapter.propose_new_texts is not
    # None`, so the attribute has to exist. None means "use the built-in proposal".
    propose_new_texts = None

    def __init__(
        self,
        client: VLLMClient,
        model: str,
        metric: MeteredMetric,
        cfg: Config,
        few_shot_block: str | None,
    ) -> None:
        self.client = client
        self.model = model
        self.metric = metric
        self.cfg = cfg
        self.few_shot_block = few_shot_block

    def evaluate(self, batch: list[Example], candidate: dict[str, str], capture_traces: bool = False):
        from gepa.core.adapter import EvaluationBatch

        self.metric.reserve(len(batch))
        prompts = [_compose(candidate["instruction"], ex, self.few_shot_block) for ex in batch]
        gens = self.client.generate(
            prompts, model=self.model, temperature=self.cfg.rollout_temperature,
            max_tokens=self.cfg.max_tokens,
        )
        scores, outputs, trajectories = [], [], []
        for example, gen in zip(batch, gens):
            pred = extract_answer(gen.text, example.task)
            correct = bool(self.metric(example, pred))
            scores.append(1.0 if correct else 0.0)
            outputs.append({"text": gen.text, "pred": pred})
            trajectories.append(
                {
                    "example": example,
                    "text": gen.text,
                    "pred": pred,
                    "correct": correct,
                }
            )
        return EvaluationBatch(outputs=outputs, scores=scores,
                               trajectories=trajectories if capture_traces else None)

    def make_reflective_dataset(
        self, candidate: dict[str, str], eval_batch, components_to_update: Sequence[str]
    ) -> dict[str, list[dict[str, Any]]]:
        rows = []
        for traj in eval_batch.trajectories or []:
            example = traj["example"]
            rows.append(
                {
                    "Inputs": _compose("", example, self.few_shot_block).strip(),
                    "Generated Outputs": traj["text"],
                    "Feedback": build_feedback(example, traj["text"], traj["correct"]),
                }
            )
        return {component: rows for component in components_to_update}


def _reflection_fn(client: VLLMClient, counter: list[int]):
    def reflect(messages):
        if isinstance(messages, str):
            prompt = messages
        else:
            prompt = messages[-1]["content"] if messages else ""
            if len(messages) > 1:
                prompt = "\n\n".join(m["content"] for m in messages)
        counter.append(1)
        return client.generate([prompt], model=client.model_id, temperature=1.0, max_tokens=1024)[0].text

    return reflect


def run_gepa(
    task: str,
    seed: int,
    cfg: Config,
    client: VLLMClient,
    reflect_client: VLLMClient,
    seed_prompt: str,
    few_shot_block: str | None,
    train: list[Example],
    pareto: list[Example],
    optimizer: Callable[..., Any] | None = None,
    out_dir: str | Path | None = None,
) -> GepaResult:
    for example in [*train, *pareto]:
        if example.split == "test":
            raise ValueError(f"{example.id} is a test item; optimizers never see the test split")

    out = Path(out_dir) if out_dir is not None else Path(cfg.results_dir)
    out.mkdir(parents=True, exist_ok=True)
    curve_path = out / f"gepa_{task}_s{seed}.curve.jsonl"

    metric = MeteredMetric(score, cfg.gepa_budget)
    adapter = _Adapter(client, cfg.model_id, metric, cfg, few_shot_block)
    reflection_calls: list[int] = []

    if optimizer is None:
        from gepa import optimize as optimizer

    started = time.time()
    partial = False
    try:
        result = optimizer(
        seed_candidate={"instruction": seed_prompt},
        trainset=train,
        valset=pareto,
        adapter=adapter,
        reflection_lm=_reflection_fn(reflect_client, reflection_calls),
            max_metric_calls=max(1, cfg.gepa_budget - len(pareto)),
            skip_perfect_score=False,
            seed=seed,
        )
    except BudgetExhausted:
        # The engine overshot its own counter; we stop here and report a partial run
        # rather than fabricate a score for a search that did not finish.
        result = None
        partial = True
    wall = time.time() - started

    counts = list(getattr(result, "discovery_eval_counts", []) or [])
    scores = list(getattr(result, "val_aggregate_scores", []) or [])
    curve = sorted((int(c), float(s)) for c, s in zip(counts, scores))
    with curve_path.open("a", encoding="utf-8") as handle:
        for calls, value in curve:
            handle.write(json.dumps({"metric_calls": calls, "pareto_score": value}) + "\n")

    best = (getattr(result, "best_candidate", None) if result else None) or {
        "instruction": seed_prompt
    }
    pareto_score = float(getattr(result, "best_val_aggregate_score", 0.0) or 0.0)
    if not pareto_score and scores:
        pareto_score = float(scores[int(max(range(len(scores)), key=lambda i: scores[i]))])

    return GepaResult(
        best_prompt=best.get("instruction", seed_prompt),
        pareto_score=pareto_score,
        curve=curve,
        metric_calls=metric.calls,
        reflection_calls=len(reflection_calls),
        wall_seconds=wall,
        accepted_candidates=max(0, len(getattr(result, "candidates", []) or []) - 1),
        partial=partial,
    )


def assert_gate(result: GepaResult, baseline: float) -> None:
    gain = result.pareto_score - baseline
    if gain < 0.01:
        raise GepaGateFailed(
            f"pareto score {result.pareto_score:.3f} is not >1pp above baseline {baseline:.3f}"
        )
    if result.accepted_candidates < 3:
        raise GepaGateFailed(
            f"only {result.accepted_candidates} candidates were evaluated; the search was degenerate"
        )


def export_best_prompt(result: GepaResult, out_dir: str | Path, task: str, seed: int) -> Path:
    path = Path(out_dir) / f"gepa_{task}_s{seed}_best_prompt.txt"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(result.best_prompt + "\n", encoding="utf-8")
    return path


def prompt_fn_from(instruction: str, few_shot_block: str | None):
    def build(example: Example) -> str:
        return _compose(instruction, example, few_shot_block)

    return build
