# T2L on Mistral-7B-Instruct-v0.2 — Design

Date: 2026-11-15
Status: draft, awaiting approval
Supersedes: nothing. Extends `2026-11-15-t2l-vs-gepa-design.md` (which stays as the record
of the Gemma-2B run).

## 1. Intent

Run **Text-to-LoRA only** on `mistralai/Mistral-7B-Instruct-v0.2` over **five benchmarks
from T2L's own suite**, with GEPA deliberately deferred. The point of this phase is to
produce a trustworthy T2L result on the model the paper actually uses, on infrastructure
GEPA can reuse unchanged in the next phase.

Why this model: Mistral-7B-Instruct-v0.2 is T2L's **primary** base model — the paper's
main tables are this model, and the released checkpoint `trained_t2l/mistral_7b_t2l`
targets it by name. The previous run could only use Gemma-2B, where T2L deltas were
+1.4pp on average. On Mistral the published deltas are an order of magnitude larger
(+11.6pp ARC-C, +13.1pp BoolQ, +17.4pp HellaSwag, +18.1pp WinoGrande), so the measurement
has far more headroom.

## 2. Scope

**In scope (this phase)**
- 5 datasets × 4 arms × 1,000 items, seed 0, on GPU 7.
- T2L adapters generated from task descriptions, never trained on our data.
- Accuracy + cost tables with 95% bootstrap CIs and paired deltas.
- All heavy artifacts under `/data/quan.lt/temp/t2l-mistral/`.

**Out of scope (next phase)**
- GEPA on these tasks. The design keeps the server, dataset splits, scorers and results
  schema reusable so GEPA is additive, not a rebuild.
- HumanEval / MBPP (code execution sandbox), and any new dataset loader.

**Anti-goals** (would make this a failure even if it runs)
- Reporting a delta smaller than its confidence interval as a win.
- Comparing T2L-with-demos against a base arm with no demos.
- Silently shipping adapters with `use_rslora: true` and calling the collapse "T2L is bad".

## 3. Decisions

| Decision | Value | Why / who |
|---|---|---|
| Target model | `mistralai/Mistral-7B-Instruct-v0.2` | Human partner. Also T2L's primary model; repo is **not gated** (verified via HF API), and the adapter config names it exactly, so no mirror/weight-identity risk. |
| T2L checkpoint | `SakanaAI/text-to-lora` → `trained_t2l/mistral_7b_t2l` (`hypermod.pt`, 263MB) | Only released Mistral checkpoint. Verified present in the HF file listing. |
| Task text encoder | `Alibaba-NLP/gte-large-en-v1.5` (1.7GB) | Required by the checkpoint (`emb_model` in `args.yaml`). |
| Datasets | gsm8k, arc_challenge, boolq, hellaswag, winogrande | Human partner: "chỉ cần pick từ T2L, GEPA chạy được là được". All five already exist in this repo's loader/scorer/splits, so no new dataset code. |
| Arms | `base`, `icl3`, `t2l`, `t2l_icl` | `icl3` is the control that separates "demos helped" from "weights helped". Dropping it would make the result uninterpretable. |
| GPU | **7 only** | Human partner. GPU 7 was free at decision time (427MB driver overhead of 80GB). |
| Storage | `/data/quan.lt/temp/t2l-mistral/` | Human partner. `/mnt` has 28GB free and is 95% full; `/data` has 27TB. |
| Seeds | 1 (seed 0) | All four arms are greedy/deterministic given the prompt; bootstrap CI covers item sampling. Extend only if a delta lands inside the CI. |
| Items | 1,000 per task | Matches the previous run so tables are comparable across phases. |
| Decoding | greedy (T=0) for every reported number | Removes decoding variance from the comparison. |

## 4. Dataset selection

All five come from T2L's 10-task suite. GEPA applicability is by construction: each has a
programmatic metric and a labelled train pool, which is all GEPA needs in phase 2.

| Task | Type | Metric | Published base (Mistral) | Why included |
|---|---|---|---|---|
| gsm8k | free-form CoT → number | exact number | 41.02 | only generative task; tests whether the LoRA changes reasoning, not formatting |
| arc_challenge | 4-way MCQ, science | accuracy | 65.79 | hardest MCQ in the suite, largest documented T2L gain (+11.6pp) |
| boolq | binary yes/no with passage | accuracy | 71.56 | short output; isolates prompt/format effects |
| hellaswag | 4-way narrative completion | accuracy | 49.64 | long context, biggest absolute headroom |
| winogrande | 2-way coreference | accuracy | 45.07 | different reasoning shape from the other MCQ tasks |

Excluded, with reasons:

| Excluded | Reason |
|---|---|
| arc_easy | saturated (~78% base, ~89% with T2L) — little room for either method to show |
| openbookqa | only 500 test items → CI too wide |
| piqa | same commonsense-MCQ domain as hellaswag, smaller headroom |
| humaneval, mbpp | need a code-execution sandbox; GEPA's paper does not evaluate code in its main table either |

## 5. Reference numbers and the gate

Published T2L, Mistral-7B-Instruct-v0.2 (repo reproducibility table, `T2L (eval #1)`):

| | arc_c | boolq | gsm8k | hellaswag | winogrande |
|---|---|---|---|---|---|
| base | 65.79 | 71.56 | 41.02 | 49.64 | 45.07 |
| with ICL | 72.01 | 71.80 | 41.02 | 59.15 | 58.09 |
| **T2L (with ICL)** | **77.42** | **84.62** | **44.02** | **67.08** | **63.14** |

Two things to read off this table:

1. Standalone ICL already gains a lot on ARC-C/HellaSwag/WinoGrande **but nothing on
   BoolQ** (+0.24) and GSM8K (+0.00). So `t2l` (no demos) has to carry those two alone.
2. Published GSM8K is identical across base / ICL / task-description rows, which means the
   paper evaluates GSM8K with a fixed 5-shot lm-eval prompt that `--use-icl` does not
   touch. Our harness is not lm-eval, so **absolute numbers are not comparable** — same
   conclusion as the Gemma run, where our base was +9pp off.

Therefore the gate is on **deltas and adapter sanity**, not on absolute scores:

| Gate | Pass condition | If it fails |
|---|---|---|
| G1 adapter sanity | each adapter scores **≥ base − 15pp** on its own task (smoke, 100 items) and above chance | adapter is broken — check `use_rslora`, rank, target modules |
| G2 direction | `t2l_icl` > `base` on **≥4 of 5** tasks | harness/adapter bug; stop before the full grid |
| G3 magnitude | mean Δ(`t2l_icl` − `base`) within **±10pp** of the published mean Δ (**+12.6pp**) | report as "harness does not reproduce the paper's regime" and stop |

Rationale for G1's floor: a working adapter is worth tens of points on these tasks, so the
known failure mode (`use_rslora: true` with this checkpoint's r=8/alpha=16) is visible as a
collapse to near-random (chance: 25% for 4-way MCQ, 50% for BoolQ/WinoGrande). Note the
floor is "not collapsed", **not** "beats base": the published GSM8K gain is only +3.0pp, so
a positive-delta requirement would be the wrong smoke test.

## 6. Arms and what each isolates

| Arm | Weights changed | Demos | Isolates |
|---|---|---|---|
| `base` | no | 0 | what the model already does |
| `icl3` | no | 3 | value of in-context demos alone |
| `t2l` | yes | 0 | value of the T2L adapter alone |
| `t2l_icl` | yes | 3 | adapter on top of demos (the paper's published configuration) |

The headline comparison for phase 2 is `t2l_icl` vs a GEPA-optimised prompt starting from
the same 3-shot block, so this phase must produce `t2l_icl` on the same items.

## 7. Harness

- **Prompt format:** the client already posts to `/v1/chat/completions`, so vLLM applies
  the tokenizer's chat template — for this model, `[INST] … [/INST]`. No prompt-layer
  change is needed; the rules, options rendering, answer extraction and scoring are the
  tested Gemma harness unchanged.
- **Splits:** unchanged — `D_train` 150, `D_pareto` 300 drawn from train, test = official
  test split (validation where the test split has no labels), deduped by normalised
  question, leakage guard on.
- **Scoring:** unchanged extractors; the same function scores every arm.
- **Fingerprint:** each result record stores `git rev-parse HEAD` + dirty flag + model ids
  + vLLM/torch versions. Committing invalidates caches by design — plan for one commit
  before the grid, not during it.

## 8. Infrastructure

```
/data/quan.lt/temp/t2l-mistral/
  hf/                  HF_HOME — base model 14.5GB, gte-large 1.7GB, T2L ckpt 263MB
  venv/                vLLM + generation deps (kept off /mnt)
  tmp/                 TMPDIR
  loras/               5 T2L adapters (~40MB each at r=8 on a 7B model)
  results/             final per-item records + tables (survives shutdown)
```

Repo (`/mnt/.../t2lora-gepa`, 3.8GB) keeps code, configs, report and a compact copy of the
tables. No model weights on `/mnt`.

Serving: one vLLM process on GPU 7 with `--enable-lora` and all five adapters loaded, so
switching arms is a request parameter, not a restart.

## 9. Phases

| Phase | Work | Gate / duration |
|---|---|---|
| 0 | `HF_HOME`/`TMPDIR` to `/data`; create venv there; download base model, T2L checkpoint, gte-large | `python -c "import vllm"` + all three dirs present. ~30–45 min (network-bound) |
| 1 | Generate 5 LoRAs from task descriptions; force `use_rslora: false`; inspect each `adapter_config.json` | 5 adapter dirs; r=8, alpha=16, targets q_proj/v_proj. ~5 min |
| 2 | Smoke: 100 items/arm/task, all 4 arms | **G1** — every adapter >15pp above base on its task. ~20 min |
| 3 | Full grid: 5 tasks × 4 arms × 1,000 items | **G2, G3**. ~2–3 h |
| 4 | Tables (accuracy + CI + paired delta, cost), report, copy results+adapters to `/data`, commit | report regenerated from `results/`; GPU 7 released |

Total on the order of half a day, with the grid as the only long step.

## 10. Deliverables

- `docs/report/accuracy.md` — 5 tasks × 4 arms, 95% CI, paired delta vs base.
- `docs/report/cost.md` — GPU-seconds, generated tokens per arm; adapter size; adaptation
  wall-clock.
- `docs/report/report.md` — updated with the Mistral section, gate outcome, caveats.
- `results/` in the repo (per-item JSONL) **and** full copy at
  `/data/quan.lt/temp/t2l-mistral/results/`.
- 5 adapters at `/data/quan.lt/temp/t2l-mistral/loras/`.
- One commit containing code + tables + report.

## 11. Risks

| Risk | Mitigation |
|---|---|
| `use_rslora: true` in the released adapter config collapses the adapter (observed: Gemma 3–5% on GSM8K) | Force `false`, verify in `adapter_config.json`, and gate with G1 before the full grid |
| Our 0-shot/3-shot harness is easier than lm-eval, so deltas shrink below published | Gate G3 is explicitly about delta magnitude; if it fails, the report says the harness is the limit, and phase 2 still compares like-for-like |
| Mistral chat template interacts badly with the T2L LoRA (LoRA trained under lm-eval's prompt) | Smoke test compares `t2l` with and without the template on 100 items before committing to one |
| `/data` is a shared mount and could be slow for random reads | Weights are read once at server start; results are small. Only the initial download is I/O bound |
| Disk pressure on `/mnt` during setup | Nothing heavy is written to `/mnt`; venv and weights live in `/data` |
| One seed, greedy → no run-to-run variance estimate | Bootstrap CI over items reported; any delta inside the CI is labelled inconclusive |

## 12. What GEPA inherits

The next phase adds `gepa_0shot` and `gepa_3shot` arms against the same server, same five
task splits, same scorers, same results schema. The only new pieces are a reflection model
(co-located on GPU 7; 15GB target + 6GB reflector fits) and the feedback function. Nothing
in this design needs to be undone.
