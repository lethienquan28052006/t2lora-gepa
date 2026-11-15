"""Bootstrap confidence intervals and the two report tables."""

from __future__ import annotations

import numpy as np


def _as_array(values) -> np.ndarray:
    return np.asarray([1.0 if v else 0.0 for v in values], dtype=float)


def bootstrap_ci(
    correct, n_boot: int = 10000, alpha: float = 0.05, seed: int = 0
) -> tuple[float, float]:
    data = _as_array(correct)
    if data.size == 0:
        return (0.0, 0.0)
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, data.size, size=(n_boot, data.size))
    means = data[idx].mean(axis=1)
    return (float(np.quantile(means, alpha / 2)), float(np.quantile(means, 1 - alpha / 2)))


def paired_bootstrap(
    a, b, n_boot: int = 10000, alpha: float = 0.05, seed: int = 0
) -> tuple[float, float]:
    left, right = _as_array(a), _as_array(b)
    if left.shape != right.shape:
        raise ValueError("paired bootstrap needs two equal-length sequences")
    diffs = left - right
    if not diffs.any() and not right.any():
        return (0.0, 0.0)
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, diffs.size, size=(n_boot, diffs.size))
    means = diffs[idx].mean(axis=1)
    return (float(np.quantile(means, alpha / 2)), float(np.quantile(means, 1 - alpha / 2)))


def accuracy_table(rows: list[dict]) -> str:
    lines = [
        "| arm | task | n | score | 95% CI |",
        "|---|---|---|---|---|",
    ]
    for row in rows:
        lines.append(
            f"| {row['arm']} | {row['task']} | {row['n']} | {row['score'] * 100:.1f}% | "
            f"[{row['lo'] * 100:.1f}, {row['hi'] * 100:.1f}] |"
        )
    return "\n".join(lines)


def cost_table(rows: list[dict]) -> str:
    lines = [
        "| arm | task | GPU seconds | generated tokens | metric calls | reflection calls |",
        "|---|---|---|---|---|---|",
    ]
    for row in rows:
        lines.append(
            f"| {row['arm']} | {row['task']} | {row.get('wall_seconds', 0):.1f} | "
            f"{row.get('generated_tokens', 0)} | {row.get('metric_calls', 0)} | "
            f"{row.get('reflection_calls', 0)} |"
        )
    return "\n".join(lines)


def summarize(items: list[dict]) -> tuple[float, float, float]:
    correct = [bool(item["correct"]) for item in items]
    score = sum(correct) / len(correct) if correct else 0.0
    lo, hi = bootstrap_ci(correct)
    return score, lo, hi
