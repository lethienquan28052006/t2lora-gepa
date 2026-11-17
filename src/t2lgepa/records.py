"""Append-only result records and the index keyed by run identity."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class RunKey:
    arm: str
    task: str
    seed: int
    fingerprint: str


def append_record(path: str | Path, record: dict) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def _rows(path: str | Path) -> list[dict]:
    path = Path(path)
    if not path.exists():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            out.append(json.loads(line))
    return out


def load_results(path: str | Path) -> dict[RunKey, dict]:
    index: dict[RunKey, dict] = {}
    for row in _rows(path):
        if row.get("record_type") != "summary":
            continue
        key = RunKey(row["arm"], row["task"], int(row["seed"]), row["fingerprint"])
        index[key] = row
    return index


def load_items(path: str | Path, key: RunKey | None = None) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for row in _rows(path):
        if row.get("record_type") != "item":
            continue
        if key is not None and (
            row.get("arm"),
            row.get("task"),
            int(row.get("seed", -1)),
            row.get("fingerprint"),
        ) != (key.arm, key.task, key.seed, key.fingerprint):
            continue
        out[row["id"]] = row
    return out


def rewrite_with_summary(path: str | Path, summary: dict, items: list[dict]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [json.dumps({**summary, "record_type": "summary"}, ensure_ascii=False)]
    lines += [json.dumps({**item, "record_type": "item"}, ensure_ascii=False) for item in items]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
