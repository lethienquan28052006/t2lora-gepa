"""Gate that decides whether the harness reproduces the published T2L numbers."""

from __future__ import annotations


def check_gate(
    observed: dict[str, float], expected: dict[str, float], tol_pp: float
) -> tuple[bool, list[str]]:
    messages: list[str] = []
    for arm, want in expected.items():
        if arm not in observed:
            messages.append(f"{arm}: missing from this run")
            continue
        delta_pp = (observed[arm] - want) * 100
        if abs(delta_pp) > tol_pp:
            messages.append(
                f"{arm}: {observed[arm] * 100:.2f}% vs published {want * 100:.2f}% "
                f"({delta_pp:+.2f}pp, tolerance ±{tol_pp:.1f}pp)"
            )
    return (not messages, messages)
