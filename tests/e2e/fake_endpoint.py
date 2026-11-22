"""Deterministic OpenAI-compatible endpoint used only by headless demo checks."""

from __future__ import annotations

import argparse
import json
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

MODEL = "mistralai/Mistral-7B-Instruct-v0.2"
TASKS = ("gsm8k", "arc_challenge", "boolq", "hellaswag", "winogrande")


class Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if self.path == "/v1/models":
            self._json({"data": [{"id": name} for name in
                                 [MODEL, *(f"t2l_{task}" for task in TASKS)]]})
        else:
            self._json({"error": "not found"}, 404)

    def do_POST(self) -> None:
        if self.path != "/v1/chat/completions":
            self._json({"error": "not found"}, 404)
            return
        request = json.loads(self.rfile.read(int(self.headers.get("content-length", 0))))
        model = request["model"]
        # A real deterministic behavioral difference for the seeded comparison test.
        text = "#### 260" if model.startswith("t2l_") else "#### 240"
        if "Toulouse" not in request["messages"][0]["content"]:
            text = "#### 2" if model.startswith("t2l_") else "#### 1"
        time.sleep(0.03)
        self._json({
            "choices": [{"message": {"content": text}, "finish_reason": "stop"}],
            "usage": {"completion_tokens": len(text.split())},
        })

    def _json(self, payload: dict, status: int = 200) -> None:
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_args) -> None:
        return


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=18010)
    args = parser.parse_args()
    print(f"fake endpoint on http://127.0.0.1:{args.port}", flush=True)
    ThreadingHTTPServer(("127.0.0.1", args.port), Handler).serve_forever()


if __name__ == "__main__":
    main()
