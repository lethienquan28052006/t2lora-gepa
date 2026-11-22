"""Build the report tables (accuracy, paired CIs, cost, prompts) from one run directory."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from t2lgepa.analysis import paired_bootstrap
from t2lgepa.config import load_config
from t2lgepa.runner import read_summary

ARMS = ("base", "icl3", "t2l", "t2l_icl", "gepa_3shot", "t2l_gepa_opt")
GEPA_ARMS = ("gepa_3shot", "t2l_gepa_opt")


def _items(run_dir: Path, arm: str, task: str) -> dict[str, bool]:
    path = run_dir / f"{arm}_{task}_s0.jsonl"
    if not path.exists():
        return {}
    rows = path.read_text().splitlines()[1:]
    return {json.loads(line)["id"]: bool(json.loads(line)["correct"]) for line in rows}


def _paired(a: dict[str, bool], b: dict[str, bool]) -> tuple[float, float, float, int] | None:
    ids = sorted(set(a) & set(b))
    if not ids:
        return None
    x, y = [a[i] for i in ids], [b[i] for i in ids]
    low, high = paired_bootstrap(x, y)
    return sum(x) / len(x) - sum(y) / len(y), low, high, len(ids)


def _load(run_dir: Path, arm: str, task: str) -> dict | None:
    path = run_dir / f"{arm}_{task}_s0.jsonl"
    return read_summary(path) if path.exists() else None


def accuracy_table(run_dir: Path, tasks: list[str], max_eval_items: int = 1000) -> str:
    lines = ["| task | " + " | ".join(ARMS) + " |", "|---|" + "---|" * len(ARMS)]
    totals = {arm: [0.0, 0] for arm in ARMS}
    for task in tasks:
        row = []
        for arm in ARMS:
            summary = _load(run_dir, arm, task)
            if summary is None:
                row.append("—")
                continue
            full = summary["n"] >= max_eval_items
            row.append(f"{summary['score'] * 100:.1f}" if full
                       else f"{summary['score'] * 100:.1f} (n={summary['n']})")
            if full:
                totals[arm][0] += summary["score"]
                totals[arm][1] += 1
        lines.append(f"| {task} | " + " | ".join(row) + " |")
    means = {arm: (total / count if count else 0.0) for arm, (total, count) in totals.items()}
    lines.append("| **mean** | " + " | ".join(
        f"**{means[a] * 100:.1f}**" + ("" if totals[a][1] == len(tasks) else "*") for a in ARMS)
        + " |")
    deltas = " | ".join(f"{(means[a] - means['base']) * 100:+.1f}" for a in ARMS)
    lines.append(f"| **mean Δ vs base** | {deltas} |")
    partial = [f"{a}: {totals[a][1]}/{len(tasks)}" for a in ARMS if totals[a][1] != len(tasks)]
    if partial:
        lines.append("\n\\* mean over complete tasks only — " + ", ".join(partial))
    return "\n".join(lines)


def ci_table(run_dir: Path, tasks: list[str], reference: str) -> str:
    out = [(f"Paired bootstrap vs `{reference}` (95% CI, identical item ids). "
            "`n` is the number of paired items; it drops below 1,000 only if a run is incomplete."),
           "", "| arm | task | Δ pp | 95% CI | n |", "|---|---|---|---|---|"]
    for arm in ARMS:
        if arm == reference:
            continue
        for task in tasks:
            pair = _paired(_items(run_dir, arm, task), _items(run_dir, reference, task))
            if pair is None:
                out.append(f"| {arm} | {task} | — | — | 0 |")
                continue
            delta, low, high, n = pair
            out.append(f"| {arm} | {task} | {delta * 100:+.1f} | "
                       f"[{low * 100:+.1f}, {high * 100:+.1f}] | {n} |")
    return "\n".join(out)


def cost_table(run_dir: Path, tasks: list[str]) -> str:
    out = [("Wall time covers search + final test. Tokens are metered for the final greedy test "
            "pass only (search rollouts are not metered). `search calls` are optimiser rollouts; "
            "`test calls` are the held-out evaluations every arm performs."), "",
           "| arm | task | wall s | final-test tokens | search calls | test calls | reflection |",
           "|---|---|---|---|---|---|---|"]
    for arm in ARMS:
        for task in tasks:
            job = run_dir / f"{arm}_{task}_s0.job.json"
            summary = _load(run_dir, arm, task)
            record = json.loads(job.read_text()) if job.exists() else {}
            out.append(f"| {arm} | {task} | {record.get('wall_seconds', 0):.0f} | "
                       f"{summary.get('generated_tokens', 0) if summary else 0} | "
                       f"{record.get('metric_calls', 0)} | "
                       f"{summary.get('n', 0) if summary else 0} | "
                       f"{record.get('reflection_calls', 0)} |")
    return "\n".join(out)


def prompts_doc(run_dir: Path, tasks: list[str]) -> str:
    out = ["# Seed vs optimised instructions, per GEPA arm", "",
           "Files: `<arm>_<task>_s0_seed_prompt.txt` and `<arm>_<task>_s0_best_prompt.txt`.",
           "Full candidate history: `<arm>_<task>_s0_candidates.json`; rendered prompt with demos:",
           "`<arm>_<task>_s0_rendered_example.txt`."]
    for task in tasks:
        for arm in GEPA_ARMS:
            out.append(f"\n## {arm} — {task}\n")
            for kind in ("seed", "best"):
                path = run_dir / f"{arm}_{task}_s0_{kind}_prompt.txt"
                text = path.read_text().strip() if path.exists() else "(not found)"
                out.append(f"### {kind} ({len(text)} chars)\n\n```text\n{text}\n```\n")
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/mistral.yaml")
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)

    cfg = load_config(args.config)
    run_dir, out = Path(args.run_dir), Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    tasks = list(cfg.tasks)
    (out / "accuracy.md").write_text(accuracy_table(run_dir, tasks, cfg.max_eval_items) + "\n")
    (out / "cost.md").write_text(cost_table(run_dir, tasks) + "\n")
    (out / "paired_ci.md").write_text(ci_table(run_dir, tasks, "base") + "\n\n"
                                      + ci_table(run_dir, tasks, "t2l_icl") + "\n")
    (out / "prompts.md").write_text(prompts_doc(run_dir, tasks) + "\n")
    print(accuracy_table(run_dir, tasks))
    print(f"\nwrote {out}/{{accuracy,cost,paired_ci,prompts}}.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
