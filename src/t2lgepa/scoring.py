"""One answer extractor and one scorer, shared by every arm."""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation

from t2lgepa.data import Example

_GSM8K_MARKER = re.compile(r"####\s*([^\n]+)")
_NUMBER_TOKEN = re.compile(r"-?\$?\d[\d,]*(?:\.\d+)?")
_FRAC = re.compile(r"\\frac\{([-\d.]+)\}\{([-\d.]+)\}")
_ARC_CUE = re.compile(r"(?:answer|option|choice)\s*(?:is|:|=)?\s*\(?([A-D])\)?", re.IGNORECASE)
_ARC_PAREN = re.compile(r"\(([A-D])\)")
_ARC_BARE = re.compile(r"(?<![A-Za-z])([A-D])(?![A-Za-z])")
_YES_NO = re.compile(r"\b(yes|no)\b")
MCQ_TASKS = ("arc_challenge", "arc_easy", "openbookqa", "hellaswag", "piqa", "winogrande")


def normalize_number(s: str) -> str | None:
    cleaned = s.strip().strip("$").replace(",", "").strip().rstrip(".").strip()
    try:
        value = Decimal(cleaned)
    except (InvalidOperation, ValueError):
        return None
    text = format(value, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text


def extract_answer(text: str, task: str) -> str | None:
    if not text or not text.strip():
        return None
    if task == "gsm8k":
        segments = text.split("####")[1:]
        for trailing in reversed(segments):
            trailing = trailing.split("\n")[0]
            frac = _FRAC.search(trailing)
            if frac:
                return normalize_number(str(Decimal(frac.group(1)) / Decimal(frac.group(2))))
            cleaned = trailing.replace("$", "").replace("{", "").replace("}", "")
            tokens = _NUMBER_TOKEN.findall(cleaned)
            if tokens:
                value = normalize_number(tokens[0])
                if value is not None:
                    return value
        # lm-eval style fallback: no marker, so take the last number in the response.
        tail = text.replace("$", "").replace("{", "").replace("}", "").split("\n")[-1]
        tokens = _NUMBER_TOKEN.findall(tail) or _NUMBER_TOKEN.findall(
            text.replace("$", "").replace("{", "").replace("}", "")
        )
        if tokens:
            return normalize_number(tokens[-1])
        return None
    if task == "boolq":
        found = _YES_NO.findall(text.lower())
        return found[-1] if found else None
    if task in MCQ_TASKS:
        for pattern in (_ARC_CUE, _ARC_PAREN, _ARC_BARE):
            found = pattern.findall(text)
            if found:
                return found[-1].upper()
        return None
    raise ValueError(f"unknown task {task!r}")


def score(pred: str | None, example: Example) -> bool:
    if pred is None or not str(pred).strip():
        return False
    if example.task == "gsm8k":
        left = normalize_number(str(pred))
        right = normalize_number(example.answer)
        return left is not None and right is not None and Decimal(left) == Decimal(right)
    if example.task == "boolq":
        return str(pred).strip().lower() == example.answer.strip().lower()
    if example.task in MCQ_TASKS:
        return str(pred).strip().upper() == example.answer.strip().upper()
    raise ValueError(f"unknown task {example.task!r}")
