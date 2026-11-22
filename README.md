# T2L vs GEPA — adapting Mistral-7B, and what happens when you combine them

Four configurations of one model, measured on the same five benchmarks, the same 3-shot demo
block, the same answer extractor and the same greedy decoding — every one of them called through
a single OpenAI-compatible API endpoint:

| version | what it is | what changes |
|---|---|---|
| `v0-base` | Mistral-7B, zero-shot | nothing |
| `v1-t2l` | **T2L**: a frozen hypernetwork turns a task description into a LoRA in one forward pass | the weights |
| `v2-gepa` | **GEPA**: reflective prompt evolution on the base model | the instruction |
| `v3-t2l-gepa` | **T2L + GEPA**: the adapter is frozen and GEPA searches the instruction *while the adapter answers* | both, coupled |

`icl3` (base + 3-shot) and `t2l` (adapter, zero-shot) are kept as controls. All prompts —
seed, optimised, full candidate history — and all adapter weights are stored in a versioned
artifact bundle, ready for a version-switching demo (see below).

**Canonical run: `mistral-7b-v1`, 2026-11-22.** Full write-up:
[`docs/report/mistral-api-v1/report.md`](docs/report/mistral-api-v1/report.md).

---

## Results — Mistral-7B-Instruct-v0.2 (run `mistral-7b-v1`)

Five benchmarks from T2L's suite, 1,000 test items each, greedy decoding, seed 0.
T2L checkpoint `trained_t2l/mistral_7b_t2l`, GEPA reflection via hosted `deepseek-v4.1-flash`.

| task | base | icl3 | t2l (0-shot) | t2l_icl | gepa_3shot | **t2l_gepa_opt** |
|---|---|---|---|---|---|---|
| gsm8k | 47.8 | 40.2 | 39.1 | 48.4 | 39.8 | 48.0 |
| arc_challenge | 74.2 | **74.3** | 70.7 | 73.7 | 72.8 | **74.3** |
| boolq | 82.7 | 83.3 | 85.1 | **86.0** | 83.3 | 85.2 |
| hellaswag | 48.2 | 54.7 | 61.7 | 64.2 | 55.0 | **64.7** |
| winogrande | 59.4 | 62.3 | 28.1 | 64.2 | 62.2 | **64.7** |
| **mean** | 62.5 | 63.0 | 56.9 | 67.3 | 62.6 | **67.4** |
| **mean Δ vs base** | | +0.5 | −5.5 | +4.8 | +0.2 | **+4.9** |

T2L against base, paired 95% CI: HellaSwag +16.0 [+12.7, +19.4], WinoGrande +4.8 [+1.5, +8.1],
BoolQ +3.3 [+1.6, +5.1]; GSM8K and ARC-Challenge are flat.

### T2L + GEPA: small and seed-dependent

| task | t2l_icl | **t2l_gepa_opt** | Δ |
|---|---|---|---|
| gsm8k | 48.4 | 48.0 | −0.4 |
| arc_challenge | 73.7 | 74.3 | +0.6 |
| boolq | 86.0 | 85.2 | −0.8 |
| hellaswag | 64.2 | 64.7 | +0.5 |
| winogrande | 64.2 | 64.7 | +0.5 |
| **mean** | 67.3 | **67.4** | **+0.1** |

The previous independent execution of the same protocol gave +1.1 pp for the combination and
+2.0 pp for GEPA alone, against +0.1 and +0.2 here. The deterministic arms moved ≤0.3 pp between
the two executions, so the swing is in the search, not in the evaluation: in this run GEPA
returned its **seed instruction unchanged** on 4 of 5 tasks for `gepa_3shot` and 3 of 5 for
`t2l_gepa_opt`. Every seed and best prompt is stored, so this is inspectable, not anecdote.

The earlier composition controls still stand: transferring a base-model prompt onto the adapter
loses 4–6 pp on two tasks (so co-optimisation is the right shape), and searching the *description*
instead of the prompt found nothing above a ~1.4 pp noise floor. Details and numbers:
[`docs/report/t2l-gepa-comparison.md`](docs/report/t2l-gepa-comparison.md).

---

## Results — Gemma-2-2B-it (earlier phase)

Eight benchmarks × 4 arms, 1,000 items each (OpenBookQA 500), same harness, smaller model.

| arm | mean Δ vs base | best task | worst task |
|---|---|---|---|
| t2l | +1.4 pp | boolq +7.9 | gsm8k −1.4 |
| t2l_icl | +3.2 pp | hellaswag +9.0 | gsm8k −10.7 |
| icl3 | +1.2 pp | piqa +6.6 | arc_challenge −10.3 |

The migration weights were verified bit-identical to `google/gemma-2-2b-it` (288/288 tensors):
[`docs/report/verification.md`](docs/report/verification.md).

---

## What the study shows

1. **T2L is the strongest and the cheapest.** +4.8 to +5.4 pp across two runs for one forward
   pass and a 14 MB adapter, against +0.2 to +2.0 pp for ~1,250 rollouts plus reflection calls.
2. **GEPA's gain is mostly its demos, and the search is high-variance.** Against `icl3` it ranges
   from −0.5 to +1.1 pp of mean accuracy depending on the run; on GSM8K one search returned a
   better prompt and the next returned the seed, scoring 45.4 and 39.8. The demos are doing the
   heavy lifting.
3. **The two methods act on different failure modes.** On format-bound tasks (BoolQ,
   WinoGrande) the prompt and demos do the work; on HellaSwag the adapter adds +16 pp that no
   prompt in our search reached. Where they tie (WinoGrande 64.6 vs 64.3) the gain is an answer
   convention, not a capability.
4. **Combining works only when the prompt is searched *with* the adapter — but the gain is
   small and unproven with one search.** Transferring a base-model prompt to the adapted model
   loses 4–6 pp on two tasks; searching with the adapter in the loop gives +0.1 to +1.1 pp of
   mean accuracy over T2L across two runs, with no per-task delta significant in the new run.
   Searching the *description* instead found nothing, and has a ~1.4 pp noise floor. The next
   experiment is several GEPA seeds, not a bigger budget.

---

## Cost of adaptation

| method | per task | artifact |
|---|---|---|
| base / icl3 | 0 | — |
| **T2L** | 1 hypernetwork forward pass (~1 s; 0.04 s warm) | **14 MB LoRA** |
| **GEPA** | ~1,260 rollouts + 53 reflection calls over 5 tasks, 2,357 s endpoint wall | prompt text |
| **T2L+GEPA (prompt search)** | ~1,290 rollouts + 74 reflection calls, **1,476 s** endpoint wall | prompt text |
| T2L+GEPA (description search) | ~900 rollouts + 10 adapter generations, ~15 min | 10 LoRAs + description |

Endpoint wall seconds over the five tasks for the non-GEPA arms: base 798, icl3 782, t2l 389,
t2l_icl 427. The `t2l` arms generate ~3× fewer tokens because the adapter answers directly
instead of writing out chain-of-thought, which is why the adapted search is ~1.6× faster than
the same search on the base model at the same call budget.

---

## Harness bugs found and fixed

Each of these invalidated an earlier run and now has a regression test.

1. **BoolQ never rendered its passage** (stored but unused): base moved 56.1% → 82.4% after the
   fix. Earlier BoolQ numbers are not comparable.
2. **GEPA was seeded with the GSM8K instruction for every task**, so reflection spent its budget
   undoing it.
3. **GEPA's prompt renderer emitted options only for `arc_challenge`**, so HellaSwag, WinoGrande
   and BoolQ were optimised with no choices shown (seed score 0.267 vs 0.557). The first GEPA
   sweep was deleted, not reported.
4. **A zero-shot T2L adapter ignores the output format** on WinoGrande: 59.6% of outputs had no
   extractable answer, fixed by three demos (8.8%).
5. **GEPA's proposer does not know what a task description is** — zero candidates until a
   description-specific proposer was added.
6. `assert_one_job_per_gpu` hard-coded GPUs 6/7; the client doubled `/v1` for OpenAI-style base
   URLs; adapters loaded at runtime were rejected by the client.

---

## Demo

A web playground compares the adaptation surfaces on one question, with gold-answer scoring when
the item is drawn from the test split. See [`docs/demo.md`](docs/demo.md).

```bash
./scripts/start_demo.sh --tunnel     # target endpoint + FastAPI page + cloudflared
```

**Version-switching demo, ready to build on.** The artifact bundle
`/data/quan.lt/temp/t2l-mistral/artifacts/mistral-7b-v1/` (71 MB tarball beside it) contains:

- `manifest.json` — 20 versions (4 methods × 5 tasks), each with the `model` to request, the
  exact `demo_block` + `instruction` to send, adapter path and measured metrics;
- `adapters/<task>/` — the five frozen LoRAs, `use_rslora: false`;
- `prompts/<arm>/` — seed prompt, best prompt, candidate history, Pareto curve, rendered example;
- `results/` — per-item scores and generations; `serve_config.yaml`; `demo_smoke.json`.

```bash
# shows the four versions' answers side by side, through the endpoint, per task
uv run python scripts/demo_smoke.py   --manifest /data/quan.lt/temp/t2l-mistral/artifacts/mistral-7b-v1/manifest.json
```

---

## Reproduce

```bash
uv sync --extra dev
uv run pytest                       # 205 tests

# 1. adapters from descriptions (frozen hypernetwork)
uv run python scripts/gen_mistral_loras.py --config configs/mistral.yaml

# 2. serve base + 5 LoRA modules on one GPU
uv run python scripts/write_demo_config.py
VLLM_ALLOW_RUNTIME_LORA_UPDATING=1 .venv-serve/bin/vllm serve \
  --config /data/quan.lt/temp/t2l-mistral/serve_search.yaml

# 3. comparison grid, then GEPA on the same server
uv run python scripts/run_grid.py --config configs/mistral.yaml --no-gepa
uv run python scripts/run_grid.py --config configs/mistral.yaml --gepa-only --gepa-arms gepa_3shot

# 4. T2L+GEPA: search descriptions
uv run python scripts/search_descriptions.py --tasks winogrande,gsm8k --budget 900 --pareto 120

# 5. gates and tables
uv run python scripts/eval_mistral_gate.py --results /data/quan.lt/temp/t2l-mistral/results
uv run python scripts/make_tables.py --results /data/quan.lt/temp/t2l-mistral/results \
  --out docs/report/mistral

# 6. the canonical four-method run, its artifact bundle and its report tables
uv run python scripts/run_grid.py --config configs/mistral.yaml \
  --arms base,icl3,t2l,t2l_icl --gepa-arms gepa_3shot,t2l_gepa_opt \
  --results-dir /data/quan.lt/temp/t2l-mistral/runs/mistral-7b-v1/results
uv run python scripts/build_artifact_bundle.py \
  --run-dir /data/quan.lt/temp/t2l-mistral/runs/mistral-7b-v1/results \
  --out /data/quan.lt/temp/t2l-mistral/artifacts/mistral-7b-v1
uv run python scripts/build_report_v1.py \
  --run-dir /data/quan.lt/temp/t2l-mistral/runs/mistral-7b-v1/results \
  --out docs/report/mistral-api-v1
```

---

## Reports

| document | contents |
|---|---|
| [`docs/report/mistral-api-v1/report.md`](docs/report/mistral-api-v1/report.md) | **canonical run**: four methods, two-run variance, cost, artifact manifest |
| [`docs/report/t2l-gepa-opt-method.md`](docs/report/t2l-gepa-opt-method.md) | **method report for `t2l_gepa_opt`**: checkpoint, flow, reflection model, protocol, cost |
| [`docs/report/t2l-gepa-comparison.md`](docs/report/t2l-gepa-comparison.md) | full methods + results for all three approaches |
| [`docs/report/mistral/`](docs/report/mistral/) | Mistral accuracy and cost tables, adapter and serve configs |
| [`docs/report/report.md`](docs/report/report.md) | the earlier Gemma-2B run |
| [`docs/demo.md`](docs/demo.md) | how to run the demo page |

---

## Layout

```
src/t2lgepa/          data, prompts, scoring, runner, GEPA arm, T2L wrapper, gates, description search
src/t2lgepa/webapp/   FastAPI demo + static frontend
scripts/              adapter generation, adapter worker, grid runner, gates, tables, demo start
configs/              base (Gemma) and mistral configurations
docs/report/          results and methodology
docs/superpowers/     design docs and implementation plans
```

---

## Caveats

1. One seed, greedy decoding; intervals are bootstrap over items. Two executions of the same
   protocol moved the searched arms by 1.3–1.5 pp of mean accuracy, so treat single-search
   results as indicative only. Serving itself moves the deterministic arms by ~0.3 pp, and the
   dynamic-LoRA path contributes ~1.4 pp on top.
2. The harness is not lm-eval and is easier: Mistral base is +8 to +14 pp above the published
   base on ARC-C, BoolQ and WinoGrande. Absolute scores are not comparable to the paper — only
   within-harness deltas are.
3. One adapter per task, from the first paper-time description; the paper averages three.
4. GEPA ran ~1,250 metric calls per task, not the paper's budget, and its reflection model is
   `deepseek-v4.1-flash`, not GPT-4.1-mini.
5. The description search used a 120-item selection set and a 900-call budget — a pilot that
   establishes the mechanism and its noise floor, not a tuned result.
6. Out of scope: HumanEval/MBPP (code execution) from T2L's suite, and HotpotQA / HoVer / PUPA /
   AIME / LiveBench from GEPA's.

## Licence notes

Text-to-LoRA code is vendored under `vendor/text-to-lora` (SakanaAI). Mistral-7B-Instruct-v0.2
is Apache-2.0. No model weights are stored in this repository.
