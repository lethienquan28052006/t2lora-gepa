"""Client for the vLLM OpenAI-compatible server, with loud adapter failures."""

from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

import httpx


class AdapterNotLoaded(RuntimeError):
    """Requested LoRA name is not served. Never fall back to the base model silently."""


class GenerationError(RuntimeError):
    """The server failed a generation request after the retry."""


@dataclass(frozen=True)
class Generation:
    text: str
    n_tokens: int
    finish_reason: str


class VLLMClient:
    def __init__(
        self,
        base_url: str,
        model_id: str,
        adapters: list[str],
        timeout_s: float = 600,
        max_workers: int = 8,
        backoff_s: float = 2.0,
        api_key: str | None = None,
    ) -> None:
        base = base_url.rstrip("/")
        # Accept both "http://host:port" and an OpenAI-style "https://host/v1".
        self.base_url = base.removesuffix("/v1")
        self.model_id = model_id
        self.adapters = list(adapters)
        self._registered: set[str] = set()
        self.timeout_s = timeout_s
        self.max_workers = max_workers
        self.backoff_s = backoff_s
        self.api_key = api_key

    @property
    def served_names(self) -> set[str]:
        return {self.model_id, *self.adapters, *self._registered}

    def register(self, name: str) -> None:
        """Accept an adapter that was loaded after the client was built."""
        self._registered.add(name)

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}

    def assert_ready(self) -> None:
        try:
            resp = httpx.get(f"{self.base_url}/v1/models", timeout=30, headers=self._headers())
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            raise GenerationError(f"server not reachable at {self.base_url}: {exc}") from exc
        available = {entry["id"] for entry in resp.json().get("data", [])}
        missing = sorted(self.served_names - available)
        if missing:
            raise AdapterNotLoaded(f"server is missing models: {missing}; it serves {sorted(available)}")

    def generate(
        self,
        prompts: list[str],
        model: str,
        temperature: float = 0.0,
        max_tokens: int = 512,
    ) -> list[Generation]:
        if model not in self.served_names:
            raise AdapterNotLoaded(
                f"{model!r} is neither the base model nor a configured adapter "
                f"({sorted(self.served_names)})"
            )
        if not prompts:
            return []
        with ThreadPoolExecutor(max_workers=self.max_workers) as pool:
            return list(
                pool.map(lambda p: self._one(p, model, temperature, max_tokens), prompts)
            )

    def _one(self, prompt: str, model: str, temperature: float, max_tokens: int) -> Generation:
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        last_error: Exception | None = None
        for attempt in range(2):
            try:
                resp = httpx.post(
                    f"{self.base_url}/v1/chat/completions",
                    json=payload,
                    timeout=self.timeout_s,
                    headers=self._headers(),
                )
                resp.raise_for_status()
                body = resp.json()
                choice = body["choices"][0]
                return Generation(
                    text=choice["message"]["content"] or "",
                    n_tokens=body.get("usage", {}).get("completion_tokens", 0),
                    finish_reason=choice.get("finish_reason") or "unknown",
                )
            except (httpx.HTTPError, KeyError, IndexError) as exc:
                last_error = exc
                if attempt == 0 and self.backoff_s:
                    time.sleep(self.backoff_s)
        raise GenerationError(f"generation failed for model {model!r}: {last_error}")
