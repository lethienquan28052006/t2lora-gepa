"""Qualitative case studies: where does each adaptation surface win or lose?"""

from __future__ import annotations

BUCKETS = ("t2l_only", "gepa_only", "both_fail", "both_pass")


def pick_cases(
    a: dict[str, dict], b: dict[str, dict], k: int = 1
) -> dict[str, list[str]]:
    shared = sorted(set(a) & set(b))
    buckets: dict[str, list[str]] = {name: [] for name in BUCKETS}
    for item_id in shared:
        left, right = bool(a[item_id]["correct"]), bool(b[item_id]["correct"])
        if left and not right:
            buckets["t2l_only"].append(item_id)
        elif right and not left:
            buckets["gepa_only"].append(item_id)
        elif left and right:
            buckets["both_pass"].append(item_id)
        else:
            buckets["both_fail"].append(item_id)
    return {name: ids[:k] for name, ids in buckets.items()}


def render_cases(
    cases: dict[str, list[str]], a: dict[str, dict], b: dict[str, dict]
) -> str:
    lines = ["# Case studies", ""]
    for bucket in BUCKETS:
        lines.append(f"## {bucket}")
        lines.append("")
        if not cases[bucket]:
            lines.append("_no examples in this bucket_")
            lines.append("")
            continue
        for item_id in cases[bucket]:
            left, right = a[item_id], b[item_id]
            lines.append(f"### {item_id}")
            lines.append("")
            lines.append(f"**Question:** {left['question']}")
            lines.append("")
            lines.append(f"**T2L output:** {left['text']}")
            lines.append("")
            lines.append(f"**GEPA output:** {right['text']}")
            lines.append("")
            lines.append(f"**Gold:** {left['gold']}")
            lines.append("")
            if left.get("rationale"):
                lines.append(f"**Reference reasoning:** {left['rationale']}")
                lines.append("")
    return "\n".join(lines)
