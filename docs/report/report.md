# T2L vs GEPA on Gemma-2-2B-it — results

Run date 2026-11-15. Tables regenerate from `results/` with
`uv run python scripts/make_tables.py`.

> **Later run, different model.** The Mistral-7B-Instruct-v0.2 T2L-only results are in
> [`mistral/report.md`](mistral/report.md) (2026-11-16, 5 tasks × 4 arms, GPU 7). They are
> not comparable to the tables below: different model, different harness fixes, and the
> BoolQ prompt here omits the passage (see that report's caveat 4).

## Setup

| | |
|---|---|
| Base model | `unsloth/gemma-2-2b-it` — **verified bit-identical** to `google/gemma-2-2b-it` (288/288 tensors, see `verification.md`) |
| T2L checkpoint | `SakanaAI/text-to-lora` → `trained_t2l/gemma_2b_t2l` (SFT variant) |
| Adapters | one LoRA per task, generated from the paper's own task descriptions (`configs/task_descriptions.yaml`), `use_rslora` forced off to match the paper's vLLM-0.5.4 scaling |
| Reflection LM (GEPA) | `Qwen/Qwen3-8B-AWQ`, local, GPU 7 |
| Target | one vLLM 0.31 server, GPU 6 (A100-80GB), base + 8 `t2l_<task>` LoRA modules |
| Benchmarks | gsm8k, arc_challenge, arc_easy, boolq, hellaswag, openbookqa, piqa, winogrande (T2L's own suite, minus HumanEval/MBPP) |
| Items | 1,000 per task (OpenBookQA 500 — the whole test split) |
| Decoding | greedy; T=0.6 / top-p 0.95 for GEPA rollouts only |
| GEPA | 1,500 metric calls/run, D_train=150, D_pareto=300, seed 0 |
| Splits | test = dataset test (validation where the test split is unlabelled); pool deduped by question to guarantee no overlap |

## Harness validity (Gate A)

`scripts/phase1_gate.py --mode full` on GSM8K:

| arm | our harness | published (T2L repo) |
|---|---|---|
| base | 64.29% | 55.27% (+9.0pp) |
| t2l_icl | 54.89% | 56.89% (−2.0pp) |

Our zero-shot prompt (which asks for `#### <number>`) is easier than T2L's lm-eval 5-shot
harness, so **absolute numbers are not comparable to the paper**. Comparisons between arms
inside this harness are what the tables report.

## Accuracy

| arm | task | n | score | 95% CI | delta vs base | 95% CI |
|---|---|---|---|---|---|---|
| base | arc_challenge | 1000 | 74.9% | [72.3, 77.6] | - | - |
| base | arc_easy | 1000 | 83.8% | [81.5, 86.1] | - | - |
| base | boolq | 1000 | 56.1% | [53.0, 59.1] | - | - |
| base | gsm8k | 1000 | 65.6% | [62.6, 68.5] | - | - |
| base | hellaswag | 1000 | 52.4% | [49.3, 55.5] | - | - |
| base | openbookqa | 500 | 73.6% | [69.8, 77.4] | - | - |
| base | piqa | 1000 | 68.1% | [65.2, 71.0] | - | - |
| base | winogrande | 1000 | 53.5% | [50.5, 56.6] | - | - |
| gepa_0shot | gsm8k | 1319 | 65.9% | [63.3, 68.5] | +2.3pp | [+0.0, +4.6] |
| gepa_3shot | gsm8k | 1319 | 64.7% | [62.2, 67.3] | +0.4pp | [-2.4, +3.2] |
| icl3 | arc_challenge | 1000 | 64.6% | [61.6, 67.5] | -10.3pp | [-13.2, -7.5] |
| icl3 | arc_easy | 1000 | 86.1% | [83.9, 88.2] | +2.3pp | [+0.4, +4.1] |
| icl3 | boolq | 1000 | 61.8% | [58.8, 64.8] | +5.7pp | [+2.7, +8.7] |
| icl3 | gsm8k | 1000 | 64.2% | [61.2, 67.2] | -1.4pp | [-3.9, +1.1] |
| icl3 | hellaswag | 1000 | 53.5% | [50.4, 56.6] | +1.1pp | [-1.5, +3.8] |
| icl3 | openbookqa | 500 | 78.0% | [74.4, 81.6] | +4.4pp | [+0.8, +8.0] |
| icl3 | piqa | 1000 | 74.7% | [72.0, 77.3] | +6.6pp | [+3.4, +9.8] |
| icl3 | winogrande | 1000 | 54.6% | [51.5, 57.6] | +1.1pp | [-2.3, +4.6] |
| t2l | arc_challenge | 1000 | 75.1% | [72.5, 77.8] | +0.2pp | [-1.8, +2.2] |
| t2l | arc_easy | 1000 | 83.4% | [81.1, 85.7] | -0.4pp | [-2.2, +1.4] |
| t2l | boolq | 1000 | 64.0% | [61.0, 66.9] | +7.9pp | [+4.9, +10.8] |
| t2l | gsm8k | 1000 | 64.2% | [61.1, 67.1] | -1.4pp | [-4.1, +1.2] |
| t2l | hellaswag | 1000 | 54.1% | [51.1, 57.2] | +1.7pp | [-1.2, +4.6] |
| t2l_icl | arc_challenge | 1000 | 74.1% | [71.4, 76.8] | -0.8pp | [-3.1, +1.5] |
| t2l_icl | arc_easy | 1000 | 85.2% | [83.0, 87.4] | +1.4pp | [-0.4, +3.1] |
| t2l_icl | boolq | 1000 | 64.7% | [61.7, 67.6] | +8.6pp | [+5.5, +11.7] |
| t2l_icl | gsm8k | 1000 | 54.9% | [51.8, 58.0] | -10.7pp | [-13.8, -7.8] |
| t2l_icl | hellaswag | 1000 | 61.4% | [58.3, 64.5] | +9.0pp | [+6.1, +11.9] |
| t2l_icl | openbookqa | 500 | 77.6% | [73.8, 81.2] | +4.0pp | [+0.8, +7.4] |
| t2l_icl | piqa | 1000 | 75.2% | [72.5, 77.9] | +7.1pp | [+3.9, +10.3] |
| t2l_icl | winogrande | 1000 | 60.5% | [57.5, 63.5] | +7.0pp | [+3.7, +10.3] |
| t2l | openbookqa | 500 | 74.0% | [70.2, 77.8] | +0.4pp | [-2.8, +3.6] |
| t2l | piqa | 1000 | 66.7% | [63.8, 69.5] | -1.4pp | [-4.8, +2.0] |
| t2l | winogrande | 1000 | 57.8% | [54.8, 60.8] | +4.3pp | [+1.5, +7.1] |


Mean change vs base across the eight tasks:

| arm | mean Δ | best task | worst task |
|---|---|---|---|
| t2l | **+1.4pp** | boolq +7.9pp | gsm8k −1.4pp |
| t2l_icl | **+3.2pp** | hellaswag +9.0pp | gsm8k −10.7pp |
| icl3 | +1.2pp | piqa +6.6pp | arc_challenge −10.3pp |
| gepa_0shot | pending | | |
| gepa_3shot | pending | | |

## Cost

| arm | task | GPU seconds | generated tokens | metric calls | reflection calls |
|---|---|---|---|---|---|
| base | arc_challenge | 106.6 | 156431 | 1000 | 0 |
| base | arc_easy | 101.6 | 149327 | 1000 | 0 |
| base | boolq | 10.8 | 7990 | 1000 | 0 |
| base | gsm8k | 108.0 | 154766 | 1000 | 0 |
| base | hellaswag | 107.0 | 156461 | 1000 | 0 |
| base | openbookqa | 44.9 | 65864 | 500 | 0 |
| base | piqa | 71.0 | 101301 | 1000 | 0 |
| base | winogrande | 61.4 | 88061 | 1000 | 0 |
| gepa_0shot | gsm8k | 162.2 | 238237 | 1319 | 0 |
| gepa_3shot | gsm8k | 193.8 | 257651 | 1319 | 0 |
| icl3 | arc_challenge | 177.1 | 252570 | 1000 | 0 |
| icl3 | arc_easy | 98.6 | 139930 | 1000 | 0 |
| icl3 | boolq | 8.4 | 4178 | 1000 | 0 |
| icl3 | gsm8k | 115.2 | 152865 | 1000 | 0 |
| icl3 | hellaswag | 88.7 | 112320 | 1000 | 0 |
| icl3 | openbookqa | 45.3 | 63068 | 500 | 0 |
| icl3 | piqa | 60.4 | 81190 | 1000 | 0 |
| icl3 | winogrande | 55.6 | 76576 | 1000 | 0 |
| t2l | arc_challenge | 109.5 | 115413 | 1000 | 0 |
| t2l | arc_easy | 105.6 | 111463 | 1000 | 0 |
| t2l | boolq | 9.8 | 4368 | 1000 | 0 |
| t2l | gsm8k | 134.8 | 141464 | 1000 | 0 |
| t2l | hellaswag | 84.8 | 86129 | 1000 | 0 |
| t2l_icl | arc_challenge | 91.4 | 90844 | 1000 | 0 |
| t2l_icl | arc_easy | 60.4 | 58746 | 1000 | 0 |
| t2l_icl | boolq | 9.7 | 4199 | 1000 | 0 |
| t2l_icl | gsm8k | 130.3 | 125199 | 1000 | 0 |
| t2l_icl | hellaswag | 61.5 | 53718 | 1000 | 0 |
| t2l_icl | openbookqa | 25.4 | 24323 | 500 | 0 |
| t2l_icl | piqa | 51.8 | 48462 | 1000 | 0 |
| t2l_icl | winogrande | 47.2 | 45664 | 1000 | 0 |
| t2l | openbookqa | 39.6 | 40511 | 500 | 0 |
| t2l | piqa | 65.3 | 65506 | 1000 | 0 |
| t2l | winogrande | 48.2 | 46544 | 1000 | 0 |


Adaptation cost, which the tables above do not show:

| | per task |
|---|---|
| T2L (checkpoint given) | one hypernetwork forward pass, ~1 s, 6.4 MB adapter |
| T2L (if you had to train it) | ~5 GPU-days on one H100 for the 7–8B variants (no Gemma-2B figure published) |
| GEPA | ~660 rollouts + ~10 reflection calls, ~5 min on one A100 with a local 8B reflector |
| Base / ICL | zero adaptation cost |

## What the run shows

1. **T2L is not a uniform win, and the spread is the story.** It gains 7.9pp on BoolQ and
   4.3pp on WinoGrande, but loses 1.4pp on GSM8K and is flat on ARC. Averaged over eight
   tasks: +1.4pp.
2. **T2L + 3-shot is the strongest T2L configuration on average (+3.2pp)**, but it is
   fragile: −10.7pp on GSM8K. The adapter and the demo format interact; on five other
   tasks the demos help.
3. **3-shot ICL alone is not free**: +6.6pp on PIQA but −10.3pp on ARC-Challenge.
4. **GEPA's contribution depends on the task's feedback richness.** On GSM8K it gained
   +2.3pp over base at 1,500 metric calls, with the search accepting a single candidate
   (degenerate by the pre-registered ≥3 gate), so the evidence is weak.
5. **Cost asymmetry is the clearest result**: T2L's marginal cost per task is one forward
   pass and 6 MB; GEPA pays minutes of rollouts plus reflection calls per task. On these
   benchmarks that extra cost bought +2.3pp on one task.

## Caveats

1. One seed, one run per arm. CIs are bootstrap over items and do not capture run-to-run
   variance.
2. Reflection is local Qwen3-8B-AWQ, weaker than the paper's GPT-4.1-mini; a flat GEPA
   result is evidence about *this* configuration.
3. GEPA ran at 1,500 metric calls, not the paper's budget, and its gate is degenerate on
   every run so far (1 accepted candidate).
4. The published T2L adapter only behaves sensibly with `use_rslora: false`; with the
   shipped flag it collapses to 3–5% on GSM8K. See `progress.md` (Ruling).
5. HumanEval and MBPP (in T2L's suite) and HotpotQA/IFBench/HoVer/PUPA/AIME (GEPA's) are
   out of scope: code execution and retrieval infrastructure are a different project.
6. Both methods see GSM8K train (T2L's hypernetwork was trained on SNI and applied
   zero-shot; GEPA optimises on the train split), so exposure is symmetric, but the
   benchmarks themselves may be contaminated in pretraining.
