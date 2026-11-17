# Mistral demo web — Implementation Plan

> **For agentic workers:** execute task by task, TDD for the Python modules.

**Goal:** A FastAPI + static-JS page that compares Base / T2L+ICL / GEPA+ICL on Mistral, plus one script that starts vLLM, the web app and the cloudflared tunnel.

**Architecture:** `src/t2lgepa/webapp/` holds three layers: `arms.py` (pure prompt construction), `service.py` (samples, calls vLLM, scores), `app.py` (HTTP). Static assets in `webapp/static/`. `scripts/start_demo.sh` orchestrates processes.

**Tech Stack:** FastAPI, uvicorn, existing `VLLMClient`, vLLM 0.31, cloudflared named tunnel.

**Spec:** `docs/superpowers/specs/2026-11-17-mistral-demo-web-design.md`

## Global Constraints

- GPU 7 only. Demo server at `gpu_memory_utilization: 0.35`.
- Web port 7860. Tunnel hostname `cs222.lethienquan.site`.
- Never crash on a missing GEPA prompt or a malformed item: degrade to fewer cards.
- One shared answer extractor (`scoring.extract_answer`) for every arm.

---

### Task 1: Prompt construction per arm

**Files:** create `src/t2lgepa/webapp/__init__.py`, `src/t2lgepa/webapp/arms.py`; test `tests/test_webapp.py`
**Produces:** `ARMS = ("base", "t2l_icl", "gepa")`, `build_prompt(arm, example, demos, gepa_prompt) -> str`, `model_for(arm, task, cfg) -> str`

- [ ] Test: base prompt contains the rules and no demos; t2l_icl contains a demo and `(A)` options for mcq; gepa puts the GEPA text first and still renders options; boolq includes the passage.
- [ ] Implement with `zero_shot`, `three_shot`, `demo_block`, `question_block`, `_compose`.
- [ ] Run tests, commit.

### Task 2: Service layer

**Files:** `src/t2lgepa/webapp/service.py`; test as above.
**Produces:** `DemoService(cfg, results_dir, client)` with `meta()`, `sample(task)`, `compare(task, question, options, example_id) -> dict`
**Consumes:** `build_prompt`, `model_for`, `extract_answer`, `score`.

- [ ] Test: `sample` returns a test item with gold; `compare` returns one entry per arm with `text/min, lat_ms, tokens, correct`; a missing GEPA file drops only that arm; free-text with no options still works.
- [ ] Implement, with a per-task split cache.
- [ ] Commit.

### Task 3: HTTP app + frontend

**Files:** `src/t2lgepa/webapp/app.py`, `static/index.html`, `static/app.js`, `static/style.css`
**Produces:** `create_app(cfg, client) -> FastAPI`; routes `GET /`, `GET /api/meta`, `GET /api/sample`, `POST /api/compare`, `GET /api/results`.

- [ ] Test: `TestClient` returns 200 for `/`, meta lists five tasks, compare rejects an unknown task with 400.
- [ ] Implement backend, then the page: task tabs, question/options boxes, sample button, three result cards, prompt accordions, results tab.
- [ ] Commit.

### Task 4: One-command start

**Files:** `scripts/start_demo.sh`, `scripts/serve_demo_config.py` (writes the yaml with 0.35)
- [ ] Script starts vLLM on GPU 7, waits for `/v1/models` to list 6 ids, starts uvicorn on 7860, traps INT/TERM to kill both, and optionally starts the tunnel with `--tunnel`.
- [ ] Verify by running it and curling both ports.
- [ ] Commit.

### Task 5: Tunnel + DNS

- [ ] Add the `cs222.lethienquan.site → http://localhost:7860` ingress rule above the 404 rule, keeping every existing host.
- [ ] `cloudflared tunnel route dns 68bc1088 cs222.lethienquan.site`.
- [ ] Start the tunnel, verify `curl https://cs222.lethienquan.site/api/meta`.

### Task 6: End-to-end check

- [ ] Sample an item, compare on gsm8k and hellaswag, confirm three answers and scores.
- [ ] Confirm the public URL serves the page and the API.
