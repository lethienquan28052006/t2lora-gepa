# AdaptLab — Mistral-7B adaptation playground

Public: **https://cs222.lethienquan.site**

## Start / stop

```bash
./scripts/start_demo.sh              # inference endpoint + web on localhost:7860
./scripts/start_demo.sh --tunnel     # also publish cs222.lethienquan.site
# Ctrl-C stops every process the script started
```

An existing inference endpoint on `127.0.0.1:8010` or web app on `127.0.0.1:7860` is reused.
Cold start loads ~13.5 GiB of weights from Ceph, so the script waits up to 900 s
(`MODEL_WAIT_SECONDS`) and prints the vLLM log tail if the server dies or the wait expires.
Logs are in `/tmp/t2l-demo/`. The page reads the canonical run from
`/data/quan.lt/temp/t2l-mistral/runs/mistral-7b-v1/results`; override with `RUN_DIR` if needed.
The named Cloudflare tunnel routes the public hostname to port 7860.

## Two views

### Live playground

- Five benchmark selectors: GSM8K, ARC-Challenge, BoolQ, HellaSwag and WinoGrande.
- **Random test item** uses a real test item and its gold answer. A custom question gets task-
  appropriate passage/options fields and remains explicitly **UNSCORED**.
- One Run-all action compares **Base**, **T2L+ICL**, **GEPA+ICL** and **T2L×GEPA**, greedy decoded
  with the exact stored instruction/demo block and the correct API model name.
- Each response card shows the raw generation, extracted answer, correctness, latency, token
  count and a dialog with the exact full prompt. Double-clicks cannot create duplicate runs.
- The collapsible canonical results table includes the two-run caveat: the combination was +0.1 pp
  over T2L in the canonical search and +1.1 pp in the previous independent search.

### Prompt optimization

- Open directly on an examples-first gallery of the four genuinely changed prompt pairs:
  `gepa_3shot`/ARC-C and `t2l_gepa_opt`/ARC-C, BoolQ and HellaSwag. Unchanged searches are not
  presented as optimization stories.
- Each story summarizes the reviewed instruction changes, shows the full seed and best prompts,
  and offers three real held-out test cases where the matching starting-prompt baseline was wrong
  and the optimized arm was right. `icl3` is paired only with `gepa_3shot`; `t2l_icl` is paired only
  with `t2l_gepa_opt`, so weights, demos and inputs stay fixed and only the instruction changes.
- These are **selected individual corrections**, not evidence of aggregate or statistically
  significant improvement. The canonical accuracy/cost view remains the aggregate evidence.
- Expand **Explore full candidate history** to select any dataset/arm, inspect the real seed,
  stored candidates, Pareto scores/curve and best-on-`D_pareto`. Added lines are highlighted.
- If best equals seed, the raw explorer says **No better prompt found** rather than drawing a fake
  diff. A collapsible rendered example shows demos + instruction + one actual item.
- `GET /api/prompt-examples` serves the gallery from a lazily populated, per-app read-only cache.
  Missing or corrupt artifacts omit only the affected story and can leave an empty gallery without
  breaking the raw explorer or live playground. No prompts or answers are regenerated.

## Run from another checkout

The app entry point is:

```bash
.venv/bin/python -m t2lgepa.webapp.app \
  --config configs/mistral.yaml \
  --results /data/quan.lt/temp/t2l-mistral/runs/mistral-7b-v1/results \
  --base-url http://localhost:8010 --port 7860
```

It expects the OpenAI-compatible endpoint to serve `mistralai/Mistral-7B-Instruct-v0.2` and the
five `t2l_<task>` modules. `scripts/write_demo_config.py` generates the serving config.

## Headless browser checks

All tooling is installed in the gitignored `.tools/` directory; no system packages are needed.
Screenshots are written to the gitignored `artifacts/demo-checks/` directory.

```bash
npm_config_cache="$PWD/.tools/npm-cache" npm install --prefix .tools/demo-e2e playwright
PLAYWRIGHT_BROWSERS_PATH="$PWD/.tools/ms-playwright" \
  node .tools/demo-e2e/node_modules/playwright/cli.js install chromium-headless-shell

# terminal 1: deterministic fake inference, no GPU required
.venv/bin/python tests/e2e/fake_endpoint.py --port 18010

# terminal 2: real web app connected to the fake endpoint
PYTHONPATH="$PWD/src" .venv/bin/python -m t2lgepa.webapp.app \
  --base-url http://127.0.0.1:18010 \
  --results /data/quan.lt/temp/t2l-mistral/runs/mistral-7b-v1/results \
  --host 127.0.0.1 --port 17860

# terminal 3: four methods, dashboard, prompt dialogs/history, double-submit and responsive checks
node tests/e2e/check_demo.mjs
```

The browser check uses a fixed sample response only for `/api/sample`; the actual prompt builders,
comparison service and scorer still run. It asserts four response cards, scored and unscored
behavior, exact prompts, all four optimization stories, three wrong-to-right cases per story,
story/case selection, selected-case caveats, empty/malformed gallery handling, unchanged seed
handling, candidate selection, compact scores, dashboard accuracy/cost totals, incomplete and
failed result loading, keyboard operation, no horizontal mobile overflow and no JavaScript errors.

## Files

| Path | Role |
|---|---|
| `src/t2lgepa/webapp/arms.py` | Four method prompt/model mappings |
| `src/t2lgepa/webapp/service.py` | Sampling, generation and scoring |
| `src/t2lgepa/webapp/library.py` | Read-only stored GEPA histories |
| `src/t2lgepa/webapp/examples.py` | Matched prompt stories and wrong-to-right test cases |
| `src/t2lgepa/webapp/app.py` | Routes and static mount |
| `src/t2lgepa/webapp/static/` | Light two-view HTML/CSS/JS |
| `tests/e2e/` | Deterministic inference and headless-browser checks |
| `scripts/start_demo.sh` | Endpoint, web and tunnel orchestration |
