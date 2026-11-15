"""Tiny local website: results tables plus a live three-surface comparison."""

from __future__ import annotations

import argparse
import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from t2lgepa.analysis import accuracy_table, cost_table
from t2lgepa.config import Config, load_config
from t2lgepa.serve import BASE_URL_DEFAULT, gepa_prompt_from_curve

REPO_ROOT = Path(__file__).resolve().parents[2]


def build_results_payload(results_dir: str | Path) -> dict:
    from t2lgepa.tables import collect

    results_dir = Path(results_dir)
    if not results_dir.exists():
        return {"accuracy": [], "cost": [], "accuracy_md": "", "cost_md": ""}
    accuracy, cost = collect(results_dir)
    return {
        "accuracy": accuracy,
        "cost": cost,
        "accuracy_md": accuracy_table(accuracy) if accuracy else "",
        "cost_md": cost_table(cost) if cost else "",
    }


def answer_question(
    question: str,
    cfg: Config,
    gepa_prompt: str | None = None,
    base_url: str = BASE_URL_DEFAULT,
    task: str = "gsm8k",
) -> dict[str, str]:
    if not question or not question.strip():
        raise ValueError("question is empty")
    from t2lgepa.serve import run_all

    outputs = run_all([question.strip()], cfg, gepa_prompt=gepa_prompt,
                      base_url=base_url, task=task)
    return {surface: values[0] for surface, values in outputs.items()}


def render_page(cfg: Config, payload: dict, gepa_prompt: str | None) -> str:
    accuracy = payload["accuracy_md"] or "_no results yet — run the grid first_"
    cost = payload["cost_md"] or "_no results yet_"
    gepa_note = (gepa_prompt[:400] + "…") if gepa_prompt else "_no GEPA prompt found in results/_"
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<title>T2L vs GEPA — {cfg.model_id}</title>
<style>
 body{{font-family:ui-sans-serif,system-ui,sans-serif;max-width:1000px;margin:2rem auto;padding:0 1rem;color:#111}}
 h1{{font-size:1.4rem}} h2{{font-size:1.1rem;margin-top:2rem}}
 table{{border-collapse:collapse;width:100%;font-size:.9rem}} td,th{{border:1px solid #ddd;padding:.35rem .5rem;text-align:left}}
 code,pre{{background:#f5f5f5;padding:.15rem .3rem;border-radius:4px;font-size:.85rem}}
 textarea{{width:100%;height:4rem;font-size:.95rem;padding:.5rem}}
 button{{margin-top:.5rem;padding:.45rem 1rem;font-size:.95rem;cursor:pointer}}
 .cols{{display:grid;grid-template-columns:1fr 1fr 1fr;gap:1rem;margin-top:1rem}}
 .card{{border:1px solid #ddd;border-radius:6px;padding:.6rem;background:#fafafa;white-space:pre-wrap;font-size:.85rem}}
 .tag{{font-weight:600;display:block;margin-bottom:.3rem}}
 .muted{{color:#666;font-size:.85rem}}
</style></head>
<body>
<h1>Text-to-LoRA vs GEPA</h1>
<p class="muted">target model <code>{cfg.model_id}</code> · reflection <code>{cfg.reflection_model}</code>
 · one hosted model, LoRA module <code>t2l_gsm8k</code></p>

<h2>Accuracy</h2>
<pre>{accuracy}</pre>

<h2>Cost</h2>
<pre>{cost}</pre>

<h2>GEPA prompt in use</h2>
<pre>{gepa_note}</pre>

<h2>Compare live</h2>
<p class="muted">The same Gemma-2-2B server answers three ways: no adaptation, weights changed (T2L LoRA), context changed (GEPA prompt).</p>
<textarea id="q">Janet has 3 apples and buys 4 more. How many apples does she have?</textarea>
<button onclick="ask()">Ask</button>
<div class="cols">
  <div class="card"><span class="tag">base</span><span id="base">—</span></div>
  <div class="card"><span class="tag">+T2L LoRA</span><span id="t2l">—</span></div>
  <div class="card"><span class="tag">+GEPA prompt</span><span id="gepa">—</span></div>
</div>
<script>
async function ask(){{
  const q = document.getElementById('q').value;
  for (const k of ['base','t2l','gepa']) document.getElementById(k).textContent = '…';
  const r = await fetch('/api/ask', {{method:'POST', headers:{{'content-type':'application/json'}},
    body: JSON.stringify({{question: q}})}});
  const d = await r.json();
  if (d.error) {{ document.getElementById('base').textContent = d.error; return; }}
  for (const k of ['base','t2l','gepa']) document.getElementById(k).textContent = d[k] || '(empty)';
}}
</script>
</body></html>"""


def make_handler(cfg: Config, results_dir: Path, gepa_prompt: str | None):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):  # keep the console quiet
            pass

        def _send(self, code: int, body: bytes, ctype: str) -> None:
            self.send_response(code)
            self.send_header("content-type", ctype)
            self.send_header("content-length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            if self.path in ("/", "/index.html"):
                payload = build_results_payload(results_dir)
                html = render_page(cfg, payload, gepa_prompt)
                self._send(200, html.encode(), "text/html; charset=utf-8")
            elif self.path == "/api/results":
                payload = build_results_payload(results_dir)
                self._send(200, json.dumps(payload).encode(), "application/json")
            else:
                self._send(404, b"not found", "text/plain")

        def do_POST(self):
            if self.path != "/api/ask":
                self._send(404, b"not found", "text/plain")
                return
            length = int(self.headers.get("content-length", 0))
            try:
                body = json.loads(self.rfile.read(length) or b"{}")
                out = answer_question(body.get("question", ""), cfg, gepa_prompt=gepa_prompt)
                self._send(200, json.dumps(out).encode(), "application/json")
            except (ValueError, RuntimeError) as exc:
                self._send(400, json.dumps({"error": str(exc)}).encode(), "application/json")

    return Handler


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/base.yaml")
    parser.add_argument("--results", default="results")
    parser.add_argument("--port", type=int, default=7860)
    args = parser.parse_args(argv)

    cfg = load_config(args.config)
    gepa_prompt = gepa_prompt_from_curve(Path(args.results))
    server = ThreadingHTTPServer(("0.0.0.0", args.port), make_handler(cfg, Path(args.results),
                                                                    gepa_prompt))
    print(f"serving on http://localhost:{args.port}  (ctrl-c to stop)")
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
