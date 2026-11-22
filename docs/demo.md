# AdaptLab — Mistral-7B adaptation playground

Public: **https://cs222.lethienquan.site**

## Start / stop

```bash
./scripts/start_demo.sh              # inference endpoint + web on localhost:7860
./scripts/start_demo.sh --tunnel     # also publish cs222.lethienquan.site
# Ctrl-C stops every process the script started
```

An existing inference endpoint on `127.0.0.1:8010` or web app on `127.0.0.1:7860` is reused.
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

- Select dataset and either `gepa_3shot` or `t2l_gepa_opt`.
- Inspect the real seed instruction, stored candidate list, Pareto scores/curve, selected
  instruction and best-on-`D_pareto`. Added lines are highlighted against the seed.
- If best equals seed, the page says **No better prompt found** rather than drawing a fake diff.
- A collapsible rendered example shows demos + instruction + one actual item.
- Nothing is regenerated: this view only reads the stored GEPA artifacts.

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
behavior, exact prompts, unchanged seed handling, candidate selection, compact scores, dashboard
accuracy/cost totals, incomplete and failed result loading, no horizontal mobile overflow and no
JavaScript page errors.

## Files

| Path | Role |
|---|---|
| `src/t2lgepa/webapp/arms.py` | Four method prompt/model mappings |
| `src/t2lgepa/webapp/service.py` | Sampling, generation and scoring |
| `src/t2lgepa/webapp/library.py` | Read-only stored GEPA histories |
| `src/t2lgepa/webapp/app.py` | Routes and static mount |
| `src/t2lgepa/webapp/static/` | Light two-view HTML/CSS/JS |
| `tests/e2e/` | Deterministic inference and headless-browser checks |
| `scripts/start_demo.sh` | Endpoint, web and tunnel orchestration |
