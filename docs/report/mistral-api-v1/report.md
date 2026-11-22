# Mistral-7B: four adaptation methods over one API endpoint (run `mistral-7b-v1`)

Run date 2026-11-22 · seed 0 · 1,000 test items per task · greedy final scoring.
This is the canonical run for the four-method comparison. The earlier run
(`docs/report/t2l-gepa-comparison.md`) is kept as a second, independent replicate.

## 1. What is compared

| version | arm | weights | prompt |
|---|---|---|---|
| `v0-base` | `base` | base model, zero-shot | fixed task rules |
| `v1-t2l` | `t2l_icl` | frozen T2L LoRA | fixed task rules + 3 demos |
| `v2-gepa` | `gepa_3shot` | base model | GEPA-searched instruction + 3 demos |
| `v3-t2l-gepa` | `t2l_gepa_opt` | frozen T2L LoRA | GEPA-searched instruction, searched **with the adapter in the loop**, + 3 demos |
| control | `icl3` | base model | fixed task rules + 3 demos |
| control | `t2l` | frozen T2L LoRA | fixed task rules, zero-shot |

`v1` vs `v0` isolates the adapter. `v2` vs `icl3` isolates prompt search on the base model.
`v3` vs `v1` isolates prompt search on the adapted model — the combination.

## 2. Setup

| | |
|---|---|
| Base model | `mistralai/Mistral-7B-Instruct-v0.2` |
| Access | one OpenAI-compatible endpoint (`POST /v1/chat/completions`); an adapter is selected by putting `t2l_<task>` in the `model` field. No local model code is touched by the harness |
| T2L adapters | generated once from the T2L checkpoint `trained_t2l/mistral_7b_t2l`, frozen, `use_rslora: false`, 14 MB each |
| Reflection model | `deepseek-v4.1-flash`, hosted API; temperature 1.0, max 1,024 tokens |
| Prompting | chat template applied server-side; instruction + optional 3-shot demo block + item block |
| Decoding (reported) | greedy, max 512 tokens |
| Decoding (search rollouts) | T=0.6, top-p 0.95 |
| GEPA | 1,500 metric-call budget, `D_train` 150, `D_pareto` 300, seed instruction = the task's own rules |
| Leakage control | splits deduplicated by question text; the optimiser raises on any test item |
| Hardware | intentionally not disclosed; every measurement below is endpoint wall time, tokens and calls |

## 3. Results (accuracy %, 1,000 items per task)

| task | base | icl3 | t2l (0-shot) | t2l_icl | gepa_3shot | **t2l_gepa_opt** |
|---|---|---|---|---|---|---|
| gsm8k | 47.8 | 40.2 | 39.1 | 48.4 | 39.8 | 48.0 |
| arc_challenge | 74.2 | **74.3** | 70.7 | 73.7 | 72.8 | **74.3** |
| boolq | 82.7 | 83.3 | 85.1 | **86.0** | 83.3 | 85.2 |
| hellaswag | 48.2 | 54.7 | 61.7 | 64.2 | 55.0 | **64.7** |
| winogrande | 59.4 | 62.3 | 28.1 | 64.2 | 62.2 | **64.7** |
| **mean** | 62.5 | 63.0 | 56.9 | 67.3 | 62.6 | **67.4** |
| **mean Δ vs base** | | +0.5 | −5.5 | +4.8 | +0.2 | **+4.9** |

Paired bootstrap, 95% CI (full table: `paired_ci.md`):

| comparison | gsm8k | arc_challenge | boolq | hellaswag | winogrande |
|---|---|---|---|---|---|
| `t2l_icl` vs `base` | +0.6 [−2.9, +4.1] | −0.5 [−3.1, +2.0] | +3.3 [+1.6, +5.1] | +16.0 [+12.7, +19.4] | +4.8 [+1.5, +8.1] |
| `t2l_gepa_opt` vs `t2l_icl` | −0.4 | +0.6 | −0.8 | +0.5 | +0.5 |

No `t2l_gepa_opt` delta over `t2l_icl` is individually significant in this run.

## 4. Run-to-run variance (this is the important finding)

Two independent executions of the identical protocol, same seed, same budgets, same test items:

| arm | mean acc, run A (2026-11-17) | mean acc, this run | Δ |
|---|---|---|---|
| `base` | 62.2 | 62.5 | +0.3 |
| `icl3` | 63.1 | 63.0 | −0.1 |
| `t2l` | 56.8 | 56.9 | +0.1 |
| `t2l_icl` | 67.6 | 67.3 | −0.3 |
| `gepa_3shot` | 64.1 | 62.6 | **−1.5** |
| `t2l_gepa_opt` | 68.7 | 67.4 | **−1.3** |

- The deterministic arms move by ≤0.3 pp (serving nondeterminism). The searched arms move by
  1.3–1.5 pp of *mean* accuracy, and much more per task: GEPA on GSM8K scored 45.4 in run A and
  39.8 here.
- The combination's edge over T2L was **+1.1 pp** in run A and **+0.1 pp** here. It is real at
  best in the ~1 pp range, and **not established** by a single search.
- Cause, visible in the artifacts: this time GEPA returned the *seed* instruction unchanged on
  4 of 5 tasks for `gepa_3shot` and on 3 of 5 for `t2l_gepa_opt`
  (`prompts.md` shows seed and best side by side). Run A found better instructions on more tasks.
- Gate caveat: the recorded gate compares the Pareto score with the *base model's* accuracy, so
  "pass" does not by itself mean the searched prompt beat its seed.

**Honest headline:** T2L contributes a robust +4.8 to +5.4 pp. GEPA on top of the frozen adapter
matches or slightly improves T2L (+0.1 to +1.1 pp across two runs); GEPA on the base model is the
least stable arm and can be worse than plain 3-shot. Multi-seed searches are required before
claiming a combination gain.

## 5. Cost

Definitions, so the columns stay comparable:

- **wall** = search + final test, measured at the endpoint;
- **final-test tokens** = tokens generated for the greedy 1,000-item test pass only — tokens used
  *during* a GEPA search are not metered, so searched arms consume more than this column shows;
- **search calls** = optimiser rollouts (zero for the fixed arms); **test calls** = the 1,000
  held-out evaluations per task, which every arm pays, 5,000 over the five tasks.

| arm | wall (5 tasks) | final-test tokens | search calls | reflection calls |
|---|---|---|---|---|
| `base` | 798 s | 565,506 | 0 | 0 |
| `icl3` | 782 s | 535,948 | 0 | 0 |
| `t2l` | 389 s | 186,758 | 0 | 0 |
| `t2l_icl` | 427 s | 204,155 | 0 | 0 |
| `gepa_3shot` | 2,357 s | 514,387 | 6,318 | 53 |
| `t2l_gepa_opt` | **1,476 s** | 221,216 | 6,444 | 74 |

Same search budget, but the adapted loop is ~1.6× faster: the adapter answers directly, emitting
roughly 3× fewer tokens than the base model. Reflection is remote and cheap; cost is dominated by
target-model tokens.

## 6. Artifacts

| what | where |
|---|---|
| Bundle (manifest + adapters + prompts + results) | `/data/quan.lt/temp/t2l-mistral/artifacts/mistral-7b-v1/` |
| Tarball + sha256 | `mistral-7b-v1.tar.gz` (71 MB), `mistral-7b-v1.tar.gz.sha256` beside it |
| Version manifest (20 versions, all marked complete) | `manifest.json` in the bundle |
| Seed / best / candidate history / rendered prompts | `prompts/<arm>/` in the bundle, also mirrored in `prompts.md` |
| Per-item scores and generations | `results/` in the bundle |
| Demo smoke outputs (4 versions × 5 tasks, side by side) | `demo_smoke.json` in the bundle |
| Serve config for the bundle | `serve_config.yaml` in the bundle (base id + relative adapter paths) |
| Tables | `accuracy.md`, `cost.md`, `paired_ci.md`, `prompts.md` in this directory |

Regenerate everything:

```bash
uv run python scripts/run_grid.py --config configs/mistral.yaml \
  --arms base,icl3,t2l,t2l_icl --gepa-arms gepa_3shot,t2l_gepa_opt \
  --results-dir /data/quan.lt/temp/t2l-mistral/runs/mistral-7b-v1/results
uv run python scripts/build_artifact_bundle.py \
  --run-dir /data/quan.lt/temp/t2l-mistral/runs/mistral-7b-v1/results \
  --out /data/quan.lt/temp/t2l-mistral/artifacts/mistral-7b-v1
uv run python scripts/build_report_v1.py \
  --run-dir /data/quan.lt/temp/t2l-mistral/runs/mistral-7b-v1/results \
  --out docs/report/mistral-api-v1
uv run python scripts/demo_smoke.py \
  --manifest /data/quan.lt/temp/t2l-mistral/artifacts/mistral-7b-v1/manifest.json
```

## 7. Limitations

1. One seed and one search trajectory per arm; the variance section above is only two points.
2. One adapter per task, from the first paper description (the paper averages three).
3. The reflection model is `deepseek-v4.1-flash`, not the GEPA paper's GPT-4.1.
4. The harness is not lm-eval and is easier; only within-harness comparisons are meaningful.
5. Where GEPA returns the seed prompt, the "optimised" arm is literally the 3-shot baseline, so
   its score must be read as a replication of that baseline, not as a search result.
