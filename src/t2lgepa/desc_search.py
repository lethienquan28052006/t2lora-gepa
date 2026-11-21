"""Search the *description* space instead of the prompt space.

GEPA proposes text; T2L turns that text into a LoRA; the LoRA is loaded into vLLM and scored.
The hypernetwork is frozen — nothing is trained here, the search only moves its input.

Public pieces:

* `AdapterWorker` — long-lived subprocess that keeps the hypernetwork warm.
* `LoRARegistry` — loads/unloads adapters in a running vLLM server by HTTP.
* `DescriptionAdapter` — the object `gepa.optimize` drives.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

import httpx

from t2lgepa.client import VLLMClient
from t2lgepa.config import Config
from t2lgepa.data import Example
from t2lgepa.feedback import build_feedback
from t2lgepa.gepa_arm import MeteredMetric
from t2lgepa.prompts import three_shot
from t2lgepa.scoring import extract_answer


def adapter_name(description: str) -> str:
    """Stable, filesystem-safe id for a description."""
    return "desc_" + hashlib.sha1(description.strip().encode()).hexdigest()[:10]


class AdapterWorker:
    """Keeps the frozen hypernetwork loaded and answers one description at a time."""

    def __init__(
        self,
        checkpoint: str,
        out_dir: str | Path,
        python: str = sys.executable,
        script: str | Path = Path("scripts/adapter_worker.py"),
        cwd: str | Path = "vendor/text-to-lora",
    ) -> None:
        self.checkpoint = checkpoint
        self.out_dir = Path(out_dir)
        self.python = python
        self.script = Path(script).resolve()
        self.cwd = Path(cwd)
        self.proc: subprocess.Popen[str] | None = None

    def start(self) -> None:
        self.out_dir.mkdir(parents=True, exist_ok=True)
        self.proc = subprocess.Popen(
            [self.python, str(self.script), "--checkpoint", self.checkpoint,
             "--out", str(self.out_dir)],
            cwd=str(self.cwd), stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True, bufsize=1,
        )
        self._read()  # {"ready": true}

    def _read(self) -> dict:
        assert self.proc is not None and self.proc.stdout is not None
        while True:
            line = self.proc.stdout.readline()
            if not line:
                assert self.proc.stderr is not None
                raise RuntimeError(f"adapter worker died: {self.proc.stderr.read()[-2000:]}")
            if line.lstrip().startswith("{"):
                return json.loads(line)

    def generate(self, description: str) -> Path:
        assert self.proc is not None and self.proc.stdin is not None
        name = adapter_name(description)
        self.proc.stdin.write(json.dumps({"id": name, "description": description}) + "\n")
        self.proc.stdin.flush()
        reply = self._read()
        return Path(reply["path"])

    def stop(self) -> None:
        if self.proc is not None:
            self.proc.stdin.close() if self.proc.stdin else None
            self.proc.terminate()
            try:
                self.proc.wait(timeout=30)
            except subprocess.TimeoutExpired:
                self.proc.kill()
            self.proc = None


class LoRARegistry:
    """Loads and unloads adapters on a live vLLM server (`/v1/load_lora_adapter`)."""

    def __init__(self, base_url: str, api_key: str | None = None, timeout_s: float = 180) -> None:
        self.base_url = base_url.rstrip("/").removesuffix("/v1")
        self.headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
        self.timeout_s = timeout_s
        self.loaded: set[str] = set()

    def load(self, name: str, path: str | Path) -> None:
        if name in self.loaded:
            return
        resp = httpx.post(
            f"{self.base_url}/v1/load_lora_adapter",
            json={"lora_name": name, "lora_path": str(path)},
            headers=self.headers, timeout=self.timeout_s,
        )
        if resp.status_code >= 400:
            if "already been loaded" in resp.text:
                self.loaded.add(name)
                return
            raise RuntimeError(f"load_lora_adapter failed ({resp.status_code}): {resp.text[:300]}")
        self.loaded.add(name)

    def unload(self, name: str) -> None:
        if name not in self.loaded:
            return
        with httpx.Client(headers=self.headers, timeout=self.timeout_s) as client:
            resp = client.post(f"{self.base_url}/v1/unload_lora_adapter",
                               json={"lora_name": name})
        if resp.status_code >= 400:
            raise RuntimeError(f"unload_lora_adapter failed ({resp.status_code}): {resp.text[:300]}")
        self.loaded.discard(name)


def clean_description(reply: str) -> str:
    """Strip fences, quotes and list prefixes a chat model likes to add."""
    text = reply.strip()
    for marker in ("```text", "```"):
        text = text.removeprefix(marker)
    text = text.strip("`").strip().strip('"').strip()
    if text.lower().startswith("description:"):
        text = text.split(":", 1)[1].strip()
    return text.strip()


def build_description_prompt(description: str, rows: Sequence[dict[str, Any]]) -> str:
    evidence = "\n\n".join(
        f"Input:\n{row.get('Inputs', '')}\n\nModel output:\n{row.get('Generated Outputs', '')}"
        f"\n\nFeedback:\n{row.get('Feedback', '')}"
        for row in rows[:6]
    )
    return f"""You are improving the natural-language task description that a Text-to-LoRA
hypernetwork turns into a LoRA adapter.

Current description:
{description}

Evidence from the adapted model on training items:

{evidence}

Write a NEW task description that would produce an adapter which fixes the failures above.
Rules:
- 2 to 5 sentences, plain prose, no lists, no markdown.
- Describe the task, the required answer format, and the reasoning skill involved.
- Do not mention specific example questions or answers.
- Reply with the description only.
"""


class DescriptionAdapter:
    """GEPA adapter whose candidate is a task description, not an instruction."""

    propose_new_texts = None

    def __init__(
        self,
        client: VLLMClient,
        cfg: Config,
        metric: MeteredMetric,
        make_adapter: Callable[[str], tuple[str, Path]],
        registry: LoRARegistry,
        train_demos: list[Example] | None = None,
        reflect: Callable[[str], str] | None = None,
    ) -> None:
        self.client = client
        self.cfg = cfg
        self.metric = metric
        self.make_adapter = make_adapter
        self.registry = registry
        self.current: str | None = None
        self.train_demos = train_demos or []
        self.reflect = reflect

    def model_for(self, description: str) -> str:
        name, path = self.make_adapter(description)
        if name != self.current:
            self.registry.load(name, path)
            if hasattr(self.client, "register"):
                self.client.register(name)
            self.current = name
        return name

    def evaluate(self, batch: list[Example], candidate: dict[str, str],
                 capture_traces: bool = False):
        from gepa.core.adapter import EvaluationBatch

        self.metric.reserve(len(batch))
        model = self.model_for(candidate["instruction"])
        prompts = [three_shot(ex, self.train_demos) for ex in batch]
        gens = self.client.generate(prompts, model=model,
                                    temperature=self.cfg.rollout_temperature,
                                    max_tokens=self.cfg.max_tokens)
        scores, outputs, trajectories = [], [], []
        for example, gen in zip(batch, gens):
            pred = extract_answer(gen.text, example.task)
            correct = bool(self.metric(example, pred))
            scores.append(1.0 if correct else 0.0)
            outputs.append({"text": gen.text, "pred": pred})
            trajectories.append({"example": example, "text": gen.text, "pred": pred,
                                 "correct": correct})
        return EvaluationBatch(outputs=outputs, scores=scores,
                               trajectories=trajectories if capture_traces else None)

    def propose_new_texts(self, candidate: dict[str, str], reflective_dataset,
                          components_to_update: Sequence[str]) -> dict[str, str]:
        """Ask the reflector for a new *task description*, not a new prompt.

        GEPA's built-in proposer treats the candidate as the instruction that produced the
        sampled outputs; a task description is a different object and the reflector declines
        to rewrite it. This proposer states the job explicitly.
        """
        if self.reflect is None:
            return {}
        rows = list(reflective_dataset.get("instruction", []))
        reply = self.reflect(build_description_prompt(candidate["instruction"], rows))
        new = clean_description(reply)
        if not new or new.strip() == candidate["instruction"].strip():
            return {}
        return {component: new for component in components_to_update}

    def make_reflective_dataset(self, candidate: dict[str, str], eval_batch,
                                components_to_update: Sequence[str]) -> dict[str, list[dict[str, Any]]]:
        rows = []
        for traj in eval_batch.trajectories or []:
            example = traj["example"]
            rows.append({
                "Inputs": three_shot(example, self.train_demos).strip(),
                "Generated Outputs": traj["text"],
                "Feedback": build_feedback(example, traj["text"], traj["correct"]),
            })
        return {component: rows for component in components_to_update}
