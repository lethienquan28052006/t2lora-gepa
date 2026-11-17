# T2L vs GEPA — a head-to-head on Mistral-7B

Two ways to adapt a language model to a task, measured on the same model, the same
benchmarks, the same prompts and the same answer extractor:

- **Text-to-LoRA (T2L)** — a hypernetwork turns a natural-language task description into a
  LoRA in one forward pass. Adaptation cost: ~1 second and 14 MB per task.
- **GEPA** — reflective prompt evolution. Adaptation cost: ~1,250 rollouts plus 7–18
  reflection calls per task.

The headline comparison is `t2l_icl` vs `gepa_3shot`: both start from the same 3-shot demo
block; one changes the weights, the other changes the instruction.

## Results — Mistral-7B-Instruct-v0.2 (primary)

Five benchmarks from T2L's own suite, 1,000 test items each, greedy decoding, T2L's released
checkpoint `trained_t2l/mistral_7b_t2l`, GEPA reflection via `deepseek-v4.1-flash`.

| task | base | icl3 | t2l | **t2l_icl** | **gepa_3shot** |
|---|---|---|---|---|---|
| gsm8k | 47.5 | 39.9 | 39.6 | **49.7** | 45.4 |
| arc_challenge | 73.9 | **74.2** | 70.2 | 73.7 | 73.0 |
| boolq | 82.4 | 83.4 | 85.2 | **86.1** | 83.3 |
| hellaswag | 47.7 | 54.6 | 61.3 | **63.9** | 54.7 |
| winogrande | 59.3 | 63.2 | 27.9 | **64.6** | 64.3 |
| **mean Δ vs base** | | +0.9 | −5.5 | **+5.4** | **+2.0** |

**T2L wins on average (+5.4pp vs +2.0pp) and on 4 of 5 tasks.** Its largest gain is
HellaSwag, +16.2pp against GEPA's +7.0pp.

Three findings worth the run:

1. **Most of GEPA's gain is the demo block it inherits, not its instruction.** On BoolQ and
   HellaSwag the optimised prompt lands within 0.1pp of plain `icl3`. Against the fair
   prompt-only baseline (`icl3`), GEPA is +1.1pp on average.
2. **Where the two tie is informative.** WinoGrande: 64.6 vs 64.3. Both earn ~+5pp there,
   which suggests an answer-convention gain rather than new capability.
3. **A zero-shot T2L adapter can break the output format.** On WinoGrande the `t2l` arm emits
   the entity name (`" Sarah."`) instead of `The answer is (A).` — 59.6% of its outputs had
   no extractable answer, and 3 demos fix that (8.8%). That is why the paper's numbers always
   come with ICL, and why `t2l_icl` is the headline.

Full detail: [`docs/report/mistral/report.md`](docs/report/mistral/report.md) ·
[`accuracy.md`](docs/report/mistral/accuracy.md) ·
[`cost.md`](docs/report/mistral/cost.md)

## Results — Gemma-2-2B-it (earlier run)

Eight benchmarks × 4 arms, 1,000 items each (OpenBookQA 500). Same harness, smaller model.

| arm | mean Δ vs base | best | worst |
|---|---|---|---|
| t2l | +1.4pp | boolq +7.9 | gsm8k −1.4 |
| t2l_icl | +3.2pp | hellaswag +9.0 | gsm8k −10.7 |
| icl3 | +1.2pp | piqa +6.6 | arc_challenge −10.3 |

Full detail: [`docs/report/report.md`](docs/report/report.md). The migration weights were
verified bit-identical to `google/gemma-2-2b-it` (288/288 tensors):
[`verification.md`](docs/report/verification.md).

## Cost of adaptation

| | per task | artifact |
|---|---|---|
| T2L | one hypernetwork forward pass (~1 s) | 14 MB LoRA |
| GEPA | ~1,250 rollouts + 7–18 reflection calls, 294–349 s GPU | prompt text |
| ICL | zero | none |

## Demo page

A web playground compares all three surfaces on one question, with gold-answer scoring when
the item is drawn from the test split. See [`docs/demo.md`](docs/demo.md).

```bash
./scripts/start_demo.sh --tunnel     # vLLM on GPU 7 + FastAPI page + cloudflared
```

## Reproduce

```bash
uv sync
uv run pytest                       # 190 tests

# 1. generate the five adapters from the paper's task descriptions
uv run python scripts/gen_mistral_loras.py --config configs/mistral.yaml

# 2. serve (base + 5 LoRA modules on one vLLM process)
uv run python scripts/write_demo_config.py
.venv-serve/bin/vllm serve --config /data/quan.lt/temp/t2l-mistral/serve_demo.yaml

# 3. smoke gate, then the full grid
uv run python scripts/mistral_smoke.py --config configs/mistral.yaml --limit 100
uv run python scripts/run_grid.py --config configs/mistral.yaml --no-gepa
uv run python scripts/run_grid.py --config configs/mistral.yaml --gepa-only --gepa-arms gepa_3shot

# 4. gates + tables
uv run python scripts/eval_mistral_gate.py --results /data/quan.lt/temp/t2l-mistral/results
uv run python scripts/make_tables.py --results /data/quan.lt/temp/t2l-mistral/results \
  --out docs/report/mistral
```

## Layout

```
src/t2lgepa/          data, prompts, scoring, runner, GEPA arm, T2L wrapper, gates
src/t2lgepa/webapp/   FastAPI demo + static frontend
scripts/              adapter generation, grid runner, gates, tables, demo start
configs/              base (Gemma) and mistral configurations
docs/report/          results and methodology
docs/superpowers/     design docs and implementation plans
```

## Caveats

1. One seed, greedy decoding; CIs are bootstrap over items, not run-to-run variance.
2. The harness is not lm-eval and is easier: Mistral base is +8 to +14pp above the paper on
   ARC-C, BoolQ and WinoGrande, so absolute numbers are not comparable — only within-harness
   deltas are.
3. One adapter per task, from the first paper-time description; the paper averages three.
4. GEPA ran ~1,250 metric calls per task, not the paper's budget, and its reflection model is
   `deepseek-v4.1-flash`, not GPT-4.1-mini.
5. HumanEval/MBPP (T2L's suite) and HotpotQA/HoVer/PUPA/AIME (GEPA's) are out of scope: code
   execution and retrieval infrastructure are a different project.

## Licence notes

Text-to-LoRA checkpoints and code are pinned as a submodule under `vendor/text-to-lora`
(SakanaAI). Mistral-7B-Instruct-v0.2 is Apache-2.0. No model weights are stored in this
repository.
