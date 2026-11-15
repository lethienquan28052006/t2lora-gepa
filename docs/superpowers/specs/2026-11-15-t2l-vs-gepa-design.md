# T2L vs GEPA on a small model — Design

Date: 2026-11-15
Status: draft, awaiting approval
Author: (agent) with human partner

## 1. Intent

Compare the **best published configuration** of Text-to-LoRA (T2L) against the **best
published configuration** of GEPA on the **same small model** and the **same task**, and
characterise the trade-off (accuracy vs. cost of adaptation), not just a single accuracy
number.

This is a fast, honest head-to-head, not a full reproduction of either paper.

## 2. The mismatch this design has to handle

| | T2L | GEPA |
|---|---|---|
| Adapts | weights (LoRA emitted by a hypernetwork from a task description) | prompts / context only |
| One-time cost | hypernetwork training (already done, checkpoint released) | none |
| Per-task cost | one forward pass | N rollouts + reflection calls |
| Inputs | task description | program + train split + metric + textual feedback |
| Published models | Llama-3.1-8B, Mistral-7B, **Gemma-2-2B-it** | Qwen3-8B, GPT-4.1-mini |

Consequence: there is no single fair scalar comparison. We report an accuracy table and a
cost table separately, and state the break-even explicitly.

## 3. Decisions (and who made them)

| Decision | Value | Rationale |
|---|---|---|
| Target model | **google/gemma-2-2b-it** | Only sub-5B model with an official T2L checkpoint (`trained_t2l/gemma_2b_t2l`) and published reference numbers. |
| T2L "best" | released checkpoint + task description + 3-shot ICL | Best published config for this model; no retraining, no hyperparameter search. |
| GEPA "best" | GEPA with rich feedback function (+ GEPA+Merge if budget allows) | Strongest published config. |
| Reflection LM | **Qwen3-14B-Instruct-AWQ, local** (fallback Qwen3-8B-AWQ if OOM/slow) | $0 API cost, same machine, reproducible; 14B is strong enough to diagnose, 2B self-reflection is not. |
| Primary benchmark | **GSM8K** (test 1,319) | Free-form, exact-match verifiable, ~44pp headroom at 2B, and the task family where the GEPA paper found weights can beat prompts. |
| Secondary benchmark | **ARC-Challenge** (test 1,172), only if time allows | T2L's home turf (MCQ), GEPA's weakest feedback regime; tests task dependence. |
| Hardware | GPU 6 = target, GPU 7 = reflection. Two independent processes. | No tensor parallelism for a 2B model; no VRAM contention. |
| Seeds | 3 for stochastic (GEPA) arms; 1 deterministic + bootstrap CI for greedy arms | Fixes the earlier 2-vs-3 inconsistency. |
| Demo | one vLLM server hosting Gemma-2-2B with LoRA modules | T2L result is a LoRA, GEPA result is a prompt — both served by one base model. |

## 4. Goals / non-goals / anti-goals

**Goals**
- Reproduce T2L's published Gemma-2-2B-it numbers within ±2pp (harness validity gate).
- Measure T2L-best vs GEPA-best on GSM8K with 95% bootstrap CIs.
- Report the cost of each adaptation path (GPU-seconds, generated tokens, reflection
  calls, artifact size).
- 4 qualitative case studies showing the mechanism difference.

**Non-goals**
- Training T2L from scratch. Tuning T2L or GEPA hyperparameters.
- HotpotQA / HoVer / PUPA / AIME / LiveBench (2B is too weak, infra too heavy).
- Claims of methodological superiority of one paper over the other.

**Anti-goals (would make this a failure even if it runs)**
- Reporting an accuracy delta smaller than the confidence interval as a win.
- Comparing T2L-with-ICL against GEPA-without-ICL, or similar asymmetric setup.
- Silently using a stronger reflection model and calling it "same model".

## 5. Experiment design

### 5.1 Data

- GSM8K: `train` (7,473) is the pool for GEPA's D_train (n=150) and D_pareto (n=300);
  `test` (1,319) is the held-out evaluation set. Same items for every arm.
- ARC-Challenge: official test split (1,172).
- Both methods are exposed to GSM8K train (T2L's oracle LoRAs were trained on it, GEPA
  optimises on it), so the exposure is symmetric. Contamination caveat documented in §9.

### 5.2 Arms

| Arm | Method |
|---|---|
| `base` | 0-shot |
| `icl3` | 3-shot in-context, no weight change |
| `t2l` | T2L LoRA generated from task description |
| `t2l_icl` | T2L LoRA + 3-shot (published config) |
| `gepa_3shot` | GEPA-optimised instruction starting from the same 3-shot block as `t2l_icl` — **headline GEPA arm** |
| `gepa_0shot` | GEPA from a bare instruction (published-style), secondary |
| `gepa_merge` | GEPA+Merge (only if time) |
| `gepa_noreflect` | ablation: selection without reflection (isolates search from reflection) |

The headline contrast is `t2l_icl` vs `gepa_3shot`: same few-shot scaffold, one changes
weights and the other changes the instruction. GEPA may rewrite the instruction but not
the demo block, so the two arms differ only in adaptation surface.

### 5.2.1 GEPA budget and program (resolves builder-check Q1, Q5)

A GEPA "rollout" is one task-instance execution. Candidate screening uses a minibatch;
promising candidates are evaluated on D_pareto. A budget of 400–1,000 metric calls is only
a handful of full D_pareto evaluations, so that range is **not** the paper's regime.

- Budget: **1,500 metric calls** per run, D_pareto = 300, D_train = 150.
- The arm is therefore labelled **"GEPA at 1.5k rollouts"**, not "best published budget".
  The rollout/score curve is plotted per run so the reader sees saturation and can judge
  how far from convergence the run stopped.
- D_pareto is fixed across arms and seeds; the same 300 items are used by every GEPA run.

### 5.2.2 GEPA validity gate (resolves builder-check Q3)

There is no reproduction gate for GEPA, because the paper's GSM8K numbers are for a
different model. Instead:

- **Sanity gate:** the GEPA run must improve its own objective (mean score on D_pareto) by
  ≥1 pp over the seed program, and the curve must be non-degenerate (≥3 accepted
  candidates). If not, the run is reported as "failed to optimise", not as evidence about
  GEPA.
- **Confound control:** local Qwen3-14B reflection is weaker than the paper's GPT-4.1-mini.
  If the local run lands <+1 pp, we spend ~$1 on one paid GPT-class reflection run and
  report both, labelled by reflection model. This is a contingency, not baseline scope.

### 5.2.3 Feedback function (resolves builder-check Q7)

Per training item, the feedback given to the reflection LM contains: the model's full
output, the gold final answer, the gold reference rationale (GSM8K ships one), and a
correct/incorrect flag. Feedback is drawn from the train split only; the test split is
never visible to any arm.

### 5.3 Decoding and scoring

- `base`, `icl3`, `t2l`, `t2l_icl`: greedy. Report pass@1.
- `gepa` rollouts: temperature 0.6, top_p 0.95 (paper setting). Final reported number:
  greedy on the final prompt, so all arms are compared at the same decoding regime;
  stochastic score reported as a secondary figure.
- One answer extractor, used by every arm. Failing that, the comparison is meaningless.
- 3 fixed seeds for any stochastic step; bootstrap 95% CI over test items; paired
  bootstrap for arm-vs-arm.

### 5.4 Fairness / cost accounting

Recorded per run: wall-clock GPU-seconds per arm, number of generated tokens, number of
metric calls (rollouts), number of reflection calls and their token counts, LoRA file
size, prompt length. Two tables:

1. accuracy + CI per task;
2. cost per adaptation.

Break-even framing (resolves builder-check Q6): the released T2L checkpoint makes the
**marginal** one-time cost zero for us, so the cost table leads with marginal cost
(one forward pass, seconds, ~0 GPU) versus GEPA's per-task rollouts. A single sentence
quantifies the amortised case using the paper's reported hypernetwork training cost
(~5 GPU-days on one H100 for the 7–8B variants; no Gemma-2B figure is published). We do
not invent a Gemma-specific training cost.

## 6. Repo layout

```
vendor/text-to-lora/     pinned submodule
vendor/gepa/             pinned submodule
src/bench/               splits, prompt templates, answer parsers, scorers, seeding, caching
src/arms/                base | icl | t2l | gepa | ablations
src/feedback/            GSM8K and ARC feedback functions
src/serve/               vLLM launch + demo
configs/                 model / task / budget / decode configs
scripts/                 run_one_arm.py, run_grid.py, make_tables.py
results/                 one jsonl per (arm, task, seed) + run fingerprint
docs/                    this design, report
```

## 7. Phases and timing (a few hours of compute)

| Phase | Work | Gate / duration |
|---|---|---|
| 0 | Submodules, `uv sync`, flash-attn, `uv pip install vendor/text-to-lora/src/fishfarm` (fishfarm is T2L's own vendored package, not a third-party harness), download `gemma_2b_t2l`, Gemma-2-2B-it (gated license), Qwen3-14B-AWQ | `generate_lora.py` produces a LoRA file. Unpredictable: env setup, license. |
| 1a | **Smoke test** (plumbing only): 300 GSM8K items, base and `t2l_icl` | tolerance ±6 pp — catches a broken pipeline, not a modelling error. ~10 min |
| 1b | **Validity gate** (the real one): full 1,319-item test set, both `base` and `t2l_icl` | `base` within ±3 pp of 55.27 **and** `t2l_icl` within ±3 pp of 56.89. SE on 1,319 items is ~1.4 pp, so ±3 pp is a real signal, not sampling noise. ~15 min |
| 2 | GEPA port: prompt module, metric, feedback function, rollout accounting, local reflection | one full 1,500-rollout run completes with logs. ~1.5 h |
| 3 | Main grid on GSM8K (8 arms, 3 seeds for stochastic arms) | ~2.5 h |
| 4 | ARC-Challenge, optional | +30–45 min |
| 5 | Case studies + `docs/report.md` | ~30 min |
| 6 | Demo: single vLLM server, LoRA modules, 3-column Gradio | ~30 min |

Seeds: 3 for any stochastic arm (GEPA), 1 deterministic run + bootstrap CI for greedy
arms. This supersedes the "2 seeds" figure that appeared earlier in planning.

## 8. Reference numbers (T2L README, Gemma-2-2B-it)

| | ARC-c | ARC-e | BoolQ | GSM8K | HellaSwag | OpenBookQA | PIQA | WinoGrande |
|---|---|---|---|---|---|---|---|---|
| base | 73.63 | 89.86 | 80.98 | 55.27 | 54.99 | 70.80 | 70.84 | 53.83 |
| T2L + ICL | 74.12 | 90.03 | 82.27 | 56.89 | 62.86 | 74.33 | 73.61 | 57.51 |

Note the small deltas: this is why the harness gate and the CIs matter more than usual.

**Provenance of these numbers (resolves builder-check Q2).** Verified in the source:
`scripts/eval_hypermod_checkpoint.py` calls `eval_hypermod_checkpoint`
(`src/hyper_llm_modulator/utils/eval_hypermod.py`), which calls
`generate_loras_for_tasks_from_descs` and only then runs vLLM evaluation. So the published
"T2L + ICL" numbers come from a **LoRA generated from a task description**, not from a
trained per-task oracle adapter, and the one-forward-pass cost claim holds. The
hypernetwork was trained on the SNI task mixture (`args.train_ds_names`), so GSM8K is an
unseen task for the hypernetwork — the comparison is a fair zero-shot adaptation on both
sides. If Phase 1b cannot reproduce these numbers, the cause is our harness, not the
method.

## 9. Risks

| Risk | Mitigation |
|---|---|
| Harness mismatch between T2L's vLLM pipeline and GEPA's HF/DSPy path | Phase 1 gate on published numbers before any comparison |
| T2L gain at 2B is only +1.6pp on GSM8K; GEPA may also be ~+1–2pp | 1,319 test items + CIs; ARC-c as second task; a well-measured "neither helps much, here is the cost curve" is an acceptable result |
| GSM8K contamination (Gemma-2 pretraining, and both methods see train split) | Symmetric exposure; optionally add a GSM8K-Platinum slice; caveat stated explicitly in report |
| vLLM non-determinism (documented in T2L README) | Log vLLM/torch/flash-attn versions + seed in every result record; never claim deltas <1pp |
| GEPA reflection quality (small local model) | Qwen3-14B-AWQ; fallback 8B; if both fail, upgrade to paid API and relabel the configuration |
| Gemma-2 gated license | request access day 0 |
| flash-attn wheel pinned to cu123/torch2.3 | rebuild for local torch, or fall back to SDPA |

## 10. Demo

Single process, GPU 6:

```
python -m vllm.entrypoints.openai.api_server \
  --model google/gemma-2-2b-it --enable-lora --max-lora-rank 64 \
  --lora-modules t2l_gsm8k=<path> --gpu-memory-utilization 0.85 --port 8000
```

Three columns on one GSM8K question: `google/gemma-2-2b-it` (base), `t2l_gsm8k`
(weights changed), `base + GEPA prompt` (context changed). No second model is hosted;
no API key is needed.

## 11. Open items (human decisions only)

- Are GPUs 6 and 7 exclusively ours for the whole run, and is there a hard wall-clock
  deadline? Contention or a cutoff decides whether `gepa_merge`, the third seed, and
  ARC-Challenge stay in scope.
- Exact card model (4090 / A10 / L4) — affects only wall-clock, not the design.
