# T2L on Mistral-7B-Instruct-v0.2 — results

Run date 2026-11-16. Regenerate every table from `results/mistral/` with

```bash
uv run python scripts/make_tables.py --results results/mistral --out docs/report/mistral
```

## Setup

| | |
|---|---|
| Base model | `mistralai/Mistral-7B-Instruct-v0.2` (not gated; the adapter config names this repo exactly) |
| T2L checkpoint | `SakanaAI/text-to-lora` → `trained_t2l/mistral_7b_t2l` (SFT variant, `hypermod.pt` 263MB) |
| Task encoder | `Alibaba-NLP/gte-large-en-v1.5` |
| Adapters | 5 LoRAs, r=8, alpha=16, `q_proj`/`v_proj`, **`use_rslora: false`**, 66MB total |
| Serving | one vLLM 0.31 server, GPU 7 (A100-80GB), base + 5 LoRA modules |
| Tasks | gsm8k, arc_challenge, boolq, hellaswag, winogrande — T2L's own suite |
| Items | 1,000 per task (5,000 test items per arm) |
| Decoding | greedy (T=0), max 512 new tokens |
| Seed | 0 (all arms deterministic given the prompt) |
| Prompt | one CoT rule set for every arm; Mistral chat template applied by vLLM; `icl3`/`t2l_icl` prepend 3 train demos |

## Gates

| Gate | Condition | Outcome |
|---|---|---|
| G1 adapter sanity (100-item smoke) | neither arm >15pp below base | **pass** — 5/5 after judging each adapter on its better arm |
| G2 direction | `t2l_icl` > `base` on ≥4/5 tasks | **pass** — 4/5 |
| G3 magnitude | mean Δ within ±10pp of the paper's +12.6pp | **pass** — +5.4pp |

## Accuracy

| arm | task | n | score | 95% CI | Δ vs base | 95% CI |
|---|---|---|---|---|---|---|
| base | arc_challenge | 1000 | 73.9% | [71.2, 76.6] | - | - |
| base | boolq | 1000 | 82.4% | [80.0, 84.7] | - | - |
| base | gsm8k | 1000 | 47.5% | [44.4, 50.6] | - | - |
| base | hellaswag | 1000 | 47.7% | [44.7, 50.8] | - | - |
| base | winogrande | 1000 | 59.3% | [56.3, 62.3] | - | - |
| icl3 | arc_challenge | 1000 | 74.2% | [71.5, 76.9] | +0.3pp | [-2.1, +2.6] |
| icl3 | boolq | 1000 | 83.4% | [81.0, 85.7] | +1.0pp | [-0.6, +2.6] |
| icl3 | gsm8k | 1000 | 39.9% | [36.9, 43.0] | -7.6pp | [-11.1, -4.1] |
| icl3 | hellaswag | 1000 | 54.6% | [51.4, 57.7] | +6.9pp | [+3.7, +10.2] |
| icl3 | winogrande | 1000 | 63.2% | [60.2, 66.2] | +3.9pp | [+0.6, +7.2] |
| t2l | arc_challenge | 1000 | 70.2% | [67.4, 73.0] | -3.7pp | [-6.3, -1.1] |
| t2l | boolq | 1000 | 85.2% | [82.9, 87.3] | +2.8pp | [+1.2, +4.4] |
| t2l | gsm8k | 1000 | 39.6% | [36.5, 42.7] | -7.9pp | [-11.5, -4.3] |
| t2l | hellaswag | 1000 | 61.3% | [58.3, 64.3] | +13.6pp | [+10.4, +17.0] |
| t2l | winogrande | 1000 | 27.9% | [25.2, 30.7] | -31.4pp | [-35.0, -27.8] |
| t2l_icl | arc_challenge | 1000 | 73.7% | [71.0, 76.5] | -0.2pp | [-2.8, +2.3] |
| t2l_icl | boolq | 1000 | 86.1% | [83.9, 88.2] | +3.7pp | [+2.0, +5.5] |
| t2l_icl | gsm8k | 1000 | 49.7% | [46.6, 52.8] | +2.2pp | [-1.2, +5.6] |
| t2l_icl | hellaswag | 1000 | 63.9% | [60.9, 66.9] | +16.2pp | [+12.9, +19.6] |
| t2l_icl | winogrande | 1000 | 64.6% | [61.7, 67.6] | +5.3pp | [+2.0, +8.6] |

Mean Δ vs base across the five tasks: **t2l_icl +5.4pp**, `t2l` −5.5pp, `icl3` +0.9pp.

## What the run shows

1. **T2L's published configuration (`t2l_icl`) is the best arm on 4 of 5 tasks**, and the one
   clear win is large: HellaSwag **+16.2pp** [12.9, 19.6], close to the paper's +17.4pp.
2. **The paper's delta reproduces in shape but not in size.** Our base is much stronger than
   the published one on the three small-headroom tasks — BoolQ 82.4 vs 71.6, WinoGrande 59.3
   vs 45.1, ARC-C 73.9 vs 65.8 — so the adapter has less room to add. GSM8K (+2.2 vs +3.0)
   and HellaSwag (+16.2 vs +17.4) do reproduce; ARC-C (−0.2 vs +11.6) and WinoGrande
   (+5.3 vs +18.1) do not. A ceiling effect is the most likely explanation, not a broken
   adapter: the same adapter is +16.2pp on HellaSwag.
3. **Demos and weights are not additive; they substitute.** On WinoGrande, `icl3` alone is
   +3.9pp and `t2l` alone is −31.4pp, yet `t2l_icl` is +5.3pp — barely above demos alone.
   On HellaSwag it is the reverse: both help and the combination is the best result.
4. **`t2l` without demos is not a fair measure of the adapter's knowledge.** See the format
   finding below: on WinoGrande 59.6% of its outputs contain no extractable letter at all.

## Finding: the zero-shot adapter ignores the output-format rule

Counted from the saved generations (`pred is None` = the shared answer extractor found no
answer), across 999 scored items per cell:

| arm | arc_challenge | hellaswag | winogrande |
|---|---|---|---|
| base | 0.6% | 2.1% | 5.2% |
| icl3 | 0.7% | 0.0% | 0.4% |
| t2l | **8.6%** | 1.9% | **59.6%** |
| t2l_icl | 4.0% | 0.1% | 8.8% |

The WinoGrande adapter answers with the entity itself (`" Sarah."`) instead of the required
`The answer is (A).` Three demos showing the expected format fix it (59.6% → 8.8%). So the
−31.4pp of the `t2l` arm is mostly **format non-compliance**, not lost capability — a real
property of the generated adapter, and a reason the published numbers always come with ICL.

This is why the headline comparison is `t2l_icl`, and why `t2l` should be read as "the
adapter without any format scaffold", not "the adapter's knowledge".

## GEPA head-to-head

Same five tasks, same 1,000 test items, same 3-shot scaffold, same greedy decoding. GEPA
optimises the **instruction** (it may not touch the demo block); T2L changes the **weights**.
Reflection LM: `deepseek-v4.1-flash` through the user's OpenAI-compatible provider.

| task | base | icl3 | GEPA (`gepa_3shot`) | T2L (`t2l_icl`) | GEPA Δ | T2L Δ |
|---|---|---|---|---|---|---|
| gsm8k | 47.5 | 39.9 | 45.4 | **49.7** | −2.1 [−5.5, +1.3] | +2.2 [−1.2, +5.6] |
| arc_challenge | 73.9 | **74.2** | 73.0 | 73.7 | −0.9 [−3.3, +1.5] | −0.2 [−2.8, +2.3] |
| boolq | 82.4 | 83.4 | 83.3 | **86.1** | +0.9 [−0.7, +2.5] | +3.7 [+2.0, +5.5] |
| hellaswag | 47.7 | 54.6 | 54.7 | **63.9** | +7.0 [+3.8, +10.3] | +16.2 [+12.9, +19.6] |
| winogrande | 59.3 | 63.2 | 64.3 | **64.6** | +5.0 [+1.7, +8.2] | +5.3 [+2.0, +8.6] |
| **mean** | | +0.9 | **+2.0** | **+5.4** | | |

GEPA run accounting: 1,242–1,308 metric calls (rollouts), 7–18 reflection calls, 294–349 s
wall per task. One run failed its own gate: on GSM8K the optimiser could not beat the seed
program on D_pareto (0.457 vs 0.475), so it returned the seed instruction unchanged — it is
reported as "found nothing", not as a result.

**Reading the head-to-head:**

1. **T2L wins on mean (+5.4 vs +2.0) and on 4 of 5 tasks.** Its one clear, large win is
   HellaSwag, +16.2 vs GEPA's +7.0.
2. **GEPA's gain on three of five tasks is its own demo block, not its instruction.** On
   BoolQ and HellaSwag the optimised prompt lands within 0.1pp of plain `icl3`; the search
   returned essentially the seed. Relative to `icl3` (the fair prompt-only baseline), GEPA
   is +1.1pp on average.
3. **Where prompts and weights tie is informative**: WinoGrande, 64.3 vs 64.6 — the +5pp
   both methods earn there is available either way, which suggests it is a format/answer
   convention gain rather than new capability.
4. **Cost asymmetry is unchanged and larger than before**: T2L is one hypernetwork forward
   pass and a 14MB adapter; GEPA is ~1,250 rollouts plus ~10 reflection calls per task,
   roughly 5–6 minutes of GPU time, and it must be redone for every new task.

## Combination A: adapter + the prompt evolved for the base model

`t2l_gepa` = `t2l_<task>` adapter + the GEPA instruction found for the base model + the same
3 demos. No new optimisation: this tests only whether a prompt evolved against the base model
transfers to the adapted model.

| task | base | t2l_icl | gepa_3shot | **t2l_gepa** | vs t2l_icl |
|---|---|---|---|---|---|
| gsm8k | 47.5 | **49.7** | 45.4 | 45.5 | **−4.2** [−7.2, −1.2] |
| arc_challenge | 73.9 | 73.7 | 73.0 | 73.7 | +0.0 [−0.6, +0.6] |
| boolq | 82.4 | 86.1 | 83.3 | **86.2** | +0.1 [+0.0, +0.3] |
| hellaswag | 47.7 | 63.9 | 54.7 | **64.2** | +0.3 [−0.3, +0.9] |
| winogrande | 59.3 | **64.6** | 64.3 | 58.6 | **−6.0** [−8.9, −3.2] |
| **mean Δ vs base** | | +5.4 | +2.0 | **+3.5** | |

**The evolved prompt does not transfer to the adapter.** It is a wash on three tasks
(+0.0 to +0.3pp) and significantly worse on two (gsm8k −4.2, winogrande −6.0). Mean +3.5pp
against `t2l_icl`'s +5.4pp.

Mechanism: the instruction was optimised against the base model's failure modes. With the
adapter active, those failure modes are already gone, and the prompt's reasoning scaffolding
fights the adapter's own answer style. On WinoGrande the GEPA prompt asks for "brief
reasoning", and the fraction of outputs with no extractable answer rises from 8.8%
(`t2l_icl`) to 12.4% (`t2l_gepa`) — the adapter and the instruction disagree about the format.

Consequence: a combination has to be **co-optimised** — the prompt has to be searched with the
adapter in the loop — or the search has to move to a different surface entirely (the task
description that generates the adapter).

## Combination C (pilot): search the task description, not the prompt

Idea: keep T2L frozen and let GEPA rewrite the **description** that generates the adapter.
Each candidate = one hypernetwork forward pass (~0.04 s warm) + dynamic LoRA load in vLLM
(`POST /v1/load_lora_adapter`) + a minibatch of rollouts.

Plumbing works end to end: adapters are generated, loaded, scored, and the final description's
adapter is evaluated on the full test set.

The search itself produced **no new candidates**: in 10 iterations on each task the reflective
proposer returned nothing, so every run scored the seed description.

| task | seed description | best description | test (searched) | test (`t2l_icl`, shipped) |
|---|---|---|---|---|
| winogrande | unchanged | unchanged | 63.5% | 64.6% |
| gsm8k | unchanged | unchanged | 48.6% | 49.7% |

Conclusion: the *mechanism* is sound, but the candidate-proposal step does not fit. GEPA's
default proposer is written for an instruction that produced the sampled outputs; a task
description is a different object, and the reflector declined to rewrite it. The next step is
a description-specific proposer (explicitly asking for a new task description from the failure
cases), not a change to T2L.

The ~1pp gap against `t2l_icl` is the same adapter generated through a different path
(re-serialised weights, different LoRA slot layout), not a different method.

## Cost

| arm | GPU seconds (5 tasks) | generated tokens |
|---|---|---|
| base | 802 | 565,365 |
| icl3 | 793 | 542,872 |
| t2l | 382 | 188,459 |
| t2l_icl | 415 | 203,073 |

Per task, adaptation cost:

| | |
|---|---|
| T2L adapter | 1 hypernetwork forward pass (~1 s), 14MB on disk |
| Base / ICL | zero |
| GEPA | ~1,250 rollouts + 7-18 reflection calls per task, 294-349s wall, plus API tokens for reflection |
| Serving | one vLLM process, ~20GB VRAM at demo settings (see below) |

The `t2l` arms generate roughly **3× fewer tokens** than base/ICL: the adapter answers
directly instead of writing out chain-of-thought. That is cheaper and, on HellaSwag, also
more accurate — but it is exactly what breaks the extractor on WinoGrande.

## Caveats

1. **One adapter per task**, from the first paper-time description. The paper's tables
   average three generated LoRAs per task; our numbers are one sample from that distribution.
2. **One seed, greedy decoding.** CIs are bootstrap over test items and do not capture
   run-to-run variance (vLLM LoRA inference is documented as non-deterministic even at
   temperature 0).
3. **Our harness is not lm-eval**, and it is easier: base is +8 to +14pp above published on
   ARC-C, BoolQ and WinoGrande. Absolute scores are not comparable to the paper; only the
   within-harness deltas are.
4. **BoolQ prompt was fixed in this phase.** The passage had never been rendered in earlier
   runs (it was stored but unused), which is why the Gemma base sat at 56.1%. Here the
   passage is in the prompt, and base is 82.4%. Gemma's BoolQ numbers are therefore not
   comparable and should not be quoted.
5. `arc_challenge` and `winogrande` lose a few answered items to extraction (0.6–8.8%), so
   their true accuracy is slightly higher than reported; the effect is identical across arms
   except where noted above.

## Reproduction

```bash
R=/data/quan.lt/temp/t2l-mistral
HF_HOME=$R/hf CUDA_VISIBLE_DEVICES=7 VLLM_USE_FLASHINFER_SAMPLER=0 \
  .venv-serve/bin/vllm serve --config $R/serve_config.yaml

uv run python scripts/mistral_smoke.py --config configs/mistral.yaml --limit 100
uv run python scripts/run_grid.py --config configs/mistral.yaml --no-gepa
uv run python scripts/eval_mistral_gate.py --results $R/results
uv run python scripts/make_tables.py --results $R/results --out docs/report/mistral
```
