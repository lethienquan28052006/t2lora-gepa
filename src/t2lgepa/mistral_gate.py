"""Gates for the Mistral-7B T2L run.

Two questions, deliberately separate:

* `smoke_failures` — is an adapter *alive*? A collapsed adapter (wrong LoRA scaling,
  wrong target modules) still loads and produces text, but scores at chance. This must
  be caught on 100 items, before the multi-hour grid.
* `full_failures` — does the finished grid land in the paper's regime? Direction and
  magnitude of the delta, not absolute scores, because our harness is not lm-eval.
"""

from __future__ import annotations

CHANCE: dict[str, float] = {
    "gsm8k": 0.0,
    "arc_challenge": 0.25,
    "boolq": 0.5,
    "hellaswag": 0.25,
    "winogrande": 0.5,
}


def smoke_failures(
    base: dict[str, float], adapter: dict[str, float], floor_pp: float = 15.0
) -> list[str]:
    """Fail a task when its adapter collapsed: far below base, or at/below chance."""
    failures: list[str] = []
    for task, base_score in base.items():
        score = adapter.get(task)
        if score is None:
            failures.append(f"{task}: adapter arm missing from the smoke run")
            continue
        if score < base_score - floor_pp / 100:
            failures.append(
                f"{task}: adapter {score * 100:.1f}% vs base {base_score * 100:.1f}% "
                f"(below base by more than {floor_pp:.1f}pp — collapsed adapter?)"
            )
        elif score <= CHANCE.get(task, 0.0):
            failures.append(
                f"{task}: adapter {score * 100:.1f}% is at or below chance "
                f"{CHANCE[task] * 100:.1f}%"
            )
    return failures


def full_failures(
    deltas: dict[str, float], published_mean: float = 0.126, tol_pp: float = 10.0
) -> list[str]:
    """G2 (direction on >=4/5 tasks) and G3 (mean delta close to the paper's)."""
    failures: list[str] = []
    positive = sum(1 for delta in deltas.values() if delta > 0)
    if positive < 4:
        failures.append(f"G2: only {positive}/{len(deltas)} tasks improved over base (need 4)")
    if deltas:
        mean = sum(deltas.values()) / len(deltas)
        off = (mean - published_mean) * 100
        if abs(off) > tol_pp:
            failures.append(
                f"G3: mean delta {mean * 100:+.1f}pp vs published {published_mean * 100:+.1f}pp "
                f"({off:+.1f}pp, tolerance +/-{tol_pp:.1f}pp)"
            )
    return failures
