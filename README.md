# T2L vs GEPA — adapting Mistral-7B, and what happens when you combine them

Three ways to adapt a language model to a task, measured on the same model, the same five
benchmarks, the same 3-shot demo block, the same answer extractor and the same greedy decoding:

- **Text-to-LoRA (T2L)** — a frozen hypernetwork turns a natural-language task description into
  a LoRA in one forward pass.
- **GEPA** — reflective prompt evolution: the instruction is rewritten from the model's failures.
- **T2L + GEPA** — GEPA searches the *task description* that the hypernetwork reads, so every
  candidate is a different set of weights.

The headline comparison is `t2l_icl` vs `gepa_3shot`: both start from the same demos; one
changes the weights, the other changes the instruction.

---

## Results — Mistral-7B-Instruct-v0.2

Five benchmarks from T2L's suite, 1,000 test items each, greedy decoding, seed 0.
T2L checkpoint `trained_t2l/mistral_7b_t2l`, GEPA reflection via `deepseek-v4.1-flash`.

| task | base | icl3 | t2l (0-shot) | t2l_icl | gepa_3shot | t2l_gepa (A) | **t2l_gepa_opt (B)** |
|---|---|---|---|---|---|---|---|
| gsm8k | 47.5 | 39.9 | 39.6 | **49.7** | 45.4 | 45.5 | 49.6 |
| arc_challenge | 73.9 | **74.2** | 70.2 | 73.7 | 73.0 | 73.7 | **74.2** |
| boolq | 82.4 | 83.4 | 85.2 | **86.1** | 83.3 | **86.2** | 85.9 |
| hellaswag | 47.7 | 54.6 | 61.3 | 63.9 | 54.7 | 64.2 | **65.9** |
| winogrande | 59.3 | 63.2 | 27.9 | 64.6 | 64.3 | 58.6 | **67.8** |
| **mean Δ vs base** | | +0.9 | −5.3 | +5.4 | +2.0 | +3.5 | **+6.5** |

### T2L vs GEPA, with paired 95% CIs

| task | T2L Δ vs base | GEPA Δ vs base | GEPA − T2L |
|---|---|---|---|
| gsm8k | +2.2 [−1.2, +5.6] | −2.1 [−5.5, +1.3] | −4.3 [−7.6, −0.9] |
| arc_challenge | −0.2 [−2.8, +2.3] | −0.9 [−3.3, +1.5] | −0.7 [−3.2, +1.8] |
| boolq | +3.7 [+2.0, +5.5] | +0.9 [−0.7, +2.5] | −2.8 [−4.3, −1.3] |
| hellaswag | +16.2 [+12.9, +19.6] | +7.0 [+3.8, +10.3] | −9.2 [−11.9, −6.5] |
| winogrande | +5.3 [+2.0, +8.6] | +5.0 [+1.7, +8.2] | −0.3 [−3.5, +2.9] |

**T2L wins on average (+5.4 vs +2.0) and on 4 of 5 tasks.**

### GEPA against its own fair baseline (`icl3`)

This is the cleanest result in the study — same demos, only the instruction differs:

| task | GEPA − icl3 | 95% CI |
|---|---|---|
| gsm8k | **+5.5** | [+2.2, +8.9] |
| arc_challenge | −1.2 | [−2.3, −0.2] |
| boolq | −0.1 | [−0.5, +0.2] |
| hellaswag | +0.1 | [−1.0, +1.3] |
| winogrande | +1.1 | [−1.9, +4.1] |

**GEPA's evolved instruction is worth +1.1 pp over the demos it was given, positive on one of
five tasks.** Most of its "+2.0 over base" is the demo block, not the search.

### T2L + GEPA

Two compositions were tested.

**Naive (control): adapter + the prompt GEPA evolved for the base model** — zero extra compute:

| task | t2l_icl | t2l_gepa | Δ |
|---|---|---|---|
| gsm8k | 49.7 | 45.5 | **−4.2** [−7.2, −1.2] |
| arc_challenge | 73.7 | 73.7 | +0.0 [−0.6, +0.6] |
| boolq | 86.1 | 86.2 | +0.1 [+0.0, +0.3] |
| hellaswag | 63.9 | 64.2 | +0.3 [−0.3, +0.9] |
| winogrande | 64.6 | 58.6 | **−6.0** [−8.9, −3.2] |

A prompt optimised for the base model does **not** transfer to an adapted model: a wash on
three tasks, significantly worse on two. On WinoGrande the share of outputs with no
extractable answer rises from 8.8% to 12.4% — adapter and instruction disagree about the
format.

**GEPA on top of the adapter (the combination that works)** — the adapter is frozen and GEPA
searches the instruction with that adapter serving every rollout:

| task | base | t2l_icl | **t2l_gepa_opt** | Δ vs t2l_icl |
|---|---|---|---|---|
| gsm8k | 47.5 | 49.7 | 49.6 | −0.1 [−3.0, +2.8] |
| arc_challenge | 73.9 | 73.7 | 74.2 | +0.5 [−1.6, +2.6] |
| boolq | 82.4 | 86.1 | 85.9 | −0.2 [−1.7, +1.2] |
| hellaswag | 47.7 | 63.9 | **65.9** | +2.0 [−0.1, +4.1] |
| winogrande | 59.3 | 64.6 | **67.8** | **+3.2** [+0.8, +5.7] |
| **mean** | | +5.4 | **+6.5** | **+1.1** |

Co-optimising beats transferring a base-model prompt (arm A, which *loses* 4–6 pp on two tasks),
and the gains land exactly where the mechanism predicts: WinoGrande, where the zero-shot adapter
ignored the answer format, and HellaSwag, where it had the most headroom. Cheap, too — the
adapter writes 3× fewer tokens, so five tasks took ~30 minutes (1,236–1,380 metric calls,
6–20 reflection calls each).

**Description search (the other direction, for completeness)** — GEPA searches the description, T2L turns each
candidate into a new adapter (hypernetwork frozen), the adapter is loaded into the running
vLLM server and scored:

| task | candidates | val (120) | test (1,000) | shipped description |
|---|---|---|---|---|
| winogrande | 10 | 0.792 | 63.2% | **64.6%** |
| gsm8k | 1 | 0.525 | 48.0% | **49.7%** |

No candidate beat the seed. Two findings matter more than the number: GEPA's default proposer
returns **zero** candidates for a description (it expects an instruction — a custom proposer
fixes it), and the pipeline has a **~1.4 pp noise floor** (the same description, regenerated
and loaded dynamically, scores 63.2% instead of 64.6%).

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

1. **T2L is the strongest and the cheapest.** +5.4 pp for one forward pass (~1 s) and a 14 MB
   adapter, against +2.0 pp for ~1,250 rollouts and 7–18 reflection calls per task.
2. **GEPA's gain is mostly its demos.** Against `icl3` it is +1.1 pp on average and positive on
   one task. It is a good prompt optimiser; the demos are doing the heavy lifting.
3. **The two methods act on different failure modes.** On format-bound tasks (BoolQ,
   WinoGrande) the prompt and demos do the work; on HellaSwag the adapter adds +16 pp that no
   prompt in our search reached. Where they tie (WinoGrande 64.6 vs 64.3) the gain is an answer
   convention, not a capability.
4. **Combining works only when the prompt is searched *with* the adapter.** Transferring a
   base-model prompt to the adapted model loses 4–6 pp on two tasks; searching the prompt while
   the adapter serves the rollouts adds +1.1 pp on average (+3.2 on WinoGrande, CI excludes
   zero; +6.5 pp over base in total, the best number in the study). Searching the *description*
   instead found nothing, and has a ~1.4 pp noise floor.

---

## Cost of adaptation

| method | per task | artifact |
|---|---|---|
| base / icl3 | 0 | — |
| **T2L** | 1 hypernetwork forward pass (~1 s; 0.04 s warm) | **14 MB LoRA** |
| **GEPA** | ~1,250 rollouts + 7–18 reflection calls, 294–349 s GPU | prompt text |
| **T2L+GEPA (prompt search)** | ~1,300 rollouts, ~150–320 s per task | prompt text |
| T2L+GEPA (description search) | ~900 rollouts + 10 adapter generations, ~15 min | 10 LoRAs + description |

GPU-seconds over the five tasks for the non-GEPA arms: base 802, icl3 793, t2l 382, t2l_icl 415.
The `t2l` arms generate ~3× fewer tokens because the adapter answers directly instead of
writing out chain-of-thought.

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

A web playground compares all three surfaces on one question, with gold-answer scoring when the
item is drawn from the test split. See [`docs/demo.md`](docs/demo.md).

```bash
./scripts/start_demo.sh --tunnel     # vLLM on GPU 7 + FastAPI page + cloudflared
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
```

---

## Reports

| document | contents |
|---|---|
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

1. One seed, greedy decoding; intervals are bootstrap over items, not run-to-run variance.
   vLLM's LoRA path contributes ~1.4 pp of it.
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
