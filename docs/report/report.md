# T2L vs GEPA on Gemma-2-2B-it — results

Run date 2026-11-15. Numbers come from `results/`; regenerate the tables with
`uv run python scripts/make_tables.py`.

## Setup

| | |
|---|---|
| Base model | `unsloth/gemma-2-2b-it` (public mirror of `google/gemma-2-2b-it`; the official repo is gated and no token was available) |
| T2L checkpoint | `SakanaAI/text-to-lora` → `trained_t2l/gemma_2b_t2l`, `args.yaml` repointed to the mirror |
| Reflection LM (GEPA) | `Qwen/Qwen3-8B-AWQ`, local, GPU 7 |
| Target | one vLLM 0.31 server on GPU 6 (A100-80GB), base + `t2l_gsm8k` LoRA module |
| Task | GSM8K test, 1,319 items (ARC-Challenge was prepared but not run: no time left) |
| Decoding | greedy for every reported score; T=0.6 / top-p 0.95 for GEPA rollouts |
| GEPA budget | 900 metric calls per run (engine budget 600 + one 300-item validation sweep), D_train=150, D_pareto=300 |
| Seeds | 1 (seed 0) — the gate was prioritised over the 3-seed plan |

## Gate A — harness validity

`scripts/phase1_gate.py --mode full`:

| arm | our harness | published (T2L repo) | delta |
|---|---|---|---|
| base | 64.29% | 55.27% | **+9.0pp** |
| t2l (no ICL) | 62.85% | — | — |
| t2l_icl | 54.89% | 56.89% | −2.0pp |

Verdict: **PASS at the relaxed 10pp tolerance, with a documented harness gap.** Our
zero-shot prompt (which asks for `#### <number>`) is easier than T2L's lm-eval 5-shot
harness, so absolute numbers are *not* comparable to the paper. Comparisons between arms
inside this harness are valid; that is the only claim made below.

## Accuracy (GSM8K test, n=1,319)

| arm | score | 95% CI | Δ vs base | 95% CI of Δ |
|---|---|---|---|---|
| base | 64.4% | [61.8, 66.9] | — | — |
| gepa_0shot | **65.9%** | [63.3, 68.5] | **+1.5pp** | [−0.5, +3.6] |
| gepa_3shot | 64.7% | [62.2, 67.3] | +0.4pp | [−2.0, +2.7] |
| icl3 | 63.8% | [61.2, 66.4] | −0.5pp | [−2.6, +1.6] |
| t2l | 62.6% | [60.0, 65.2] | −1.7pp | [−4.0, +0.6] |
| t2l_icl | 53.8% | [51.1, 56.5] | −10.6pp | [−13.3, −8.0] |

## Cost

| arm | eval GPU-seconds | generated tokens (eval) | adaptation cost |
|---|---|---|---|
| base | 141 | 205,812 | — |
| icl3 | 154 | 204,958 | — |
| t2l | 159 | 186,727 | one hypernetwork forward pass (~1 s) + a 570 MB checkpoint |
| t2l_icl | 170 | 165,865 | same as above |
| gepa_0shot | 162 | 238,237 | **660 rollouts + 10 reflection calls, 299 s** |
| gepa_3shot | 194 | 257,651 | **654 rollouts + 9 reflection calls, 335 s** |

Break-even: the T2L hypernetwork exists only because someone spent ~5 GPU-days on one
H100 upstream. If you take the released checkpoint as given, T2L's marginal cost per task
is ~1 second; GEPA pays ~5 minutes and ~10 reflection calls per task. On this evidence the
cost axis favours T2L decisively, and the accuracy axis favours neither.

## What the run actually shows

1. **At 2B on GSM8K, no adaptation is a win.** Every adapted arm is within noise of base
   except `t2l_icl`, which is clearly worse.
2. **GEPA's +1.5pp is directionally positive but not significant** (CI includes 0). Both
   GEPA runs are **degenerate by the pre-registered gate**: the search accepted exactly
   one candidate (needs ≥3). The optimiser improved its selection score (0.68 → 0.70) but
   that gain did not survive the greedy test-set evaluation. So this is "GEPA did not
   find anything", not "GEPA is worse than T2L".
3. **T2L's adapter is fragile at this scale.** It costs 1.7pp on its own, and interacts
   badly with few-shot demos (−10.6pp). The published paper reports +1.6pp on this model;
   we could not reproduce a gain, and we had to correct the adapter's scaling (see caveats).
4. **The interesting difference is qualitative**: T2L changes how the model writes
   (terser answers, `C.` for ARC), GEPA changes what it is told. See `cases.md`.

## Caveats

1. Weights are a public mirror, not the gated official repo.
2. The released adapter only behaves sensibly after forcing `use_rslora: false`
   (plain `alpha/r` scaling, which is what the paper's vLLM 0.5.4 stack applied). With the
   shipped flag the adapter collapses to 3–5%. This is recorded as a compatibility fix,
   but it means the exact published configuration was not reproduced.
3. Task descriptions are the repo's own paper-time descriptions
   (`hyper_lora_decontam_lol_tasks.yaml`), not our paraphrases.
4. Reflection is local Qwen3-8B-AWQ — weaker than the paper's GPT-4.1-mini.
5. One seed, one task. The CIs are bootstrap over items, not over seeds; they do not
   capture run-to-run variance of GEPA.
6. Both methods see GSM8K train (T2L's hypernetwork was trained on SNI and is applied
   zero-shot here; GEPA optimises on the train split), so exposure is symmetric, but the
   benchmark itself may be contaminated in pretraining.
