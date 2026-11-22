# Method report: `t2l_gepa_opt` (T2L adapter + GEPA prompt search)

Date: 2026-11-22 · Branch: `feat/t2l-then-gepa`
Scope: how the combined method is built, run and scored, with the exact artifacts and settings.

---

## 1. What is being tested

`t2l_gepa_opt` asks a single question:

> If we freeze a Text-to-LoRA adapter and let GEPA optimise the **prompt** while that adapter is
> the model answering, does the combination beat either method alone?

Three things are deliberately fixed:

- the **adapter** — generated once from a task description, never updated;
- the **demos** — always the same three training items;
- the **decoding** used for the reported score — always greedy.

Only the instruction text moves during the search.

---

## 2. Environment

| | |
|---|---|
| Base model | `mistralai/Mistral-7B-Instruct-v0.2` (7.2B, fp16, ~14.5 GB) |
| Serving | vLLM 0.31.0, one process, GPU 7 (A100-80GB) |
| Adapters | base model + 5 LoRA modules on the same server |
| `max_model_len` | 4,096 |
| Prompt format | vLLM applies the tokenizer's chat template (`[INST] … [/INST]`) |
| Reported decoding | greedy, T=0, `max_tokens` 512 |
| Rollout decoding (search only) | T=0.6, server-default top-p |

---

## 3. The T2L checkpoint

### 3.1 What it is

T2L is a **hypernetwork**: a model whose output is the weight delta of another model. It is
trained once, offline, on a large collection of (task description → LoRA) pairs
(the T2L paper trains on 479 tasks from Lots-of-LoRAs). After that training it is frozen; using
it costs one forward pass, not fine-tuning.

| | |
|---|---|
| Repository | `SakanaAI/text-to-lora` |
| Checkpoint | `trained_t2l/mistral_7b_t2l` |
| Files | `hypermod.pt` (262.6 MB), `args.yaml`, `adapter_config.json` |
| Variant | SFT-trained (the released general-purpose variant) |
| Text encoder | `Alibaba-NLP/gte-large-en-v1.5` (~1.7 GB) |
| Output adapter | **128 tensors**, 14 MB on disk |
| LoRA shape | rank `r=8`, `alpha=16`, target modules `q_proj` and `v_proj` on every layer |

### 3.2 How an adapter is produced

```
task description (text)
        │
        ▼
gte-large-en-v1.5  ──►  task embedding
        │
        ▼
hypernetwork (frozen)  ──►  state dict of 128 LoRA tensors
        │
        ▼
save_lora(...)  ──►  <out>/adapter_config.json + adapter_model.safetensors
```

Measured on the study machine: loading the hypernetwork, base model and encoder takes **16.2 s**;
the first generation takes 1.5 s (CUDA warm-up) and each later one **0.03–0.04 s**.

### 3.3 The `use_rslora` correction

The released `adapter_config.json` says `"use_rslora": true`. The published numbers were produced
with vLLM 0.5.4, which applies plain `alpha / r` scaling. With rsLoRA scaling (`alpha / sqrt(r)`)
the adapter is ~2.8× too strong and the model stops producing usable answers. Every adapter in
this study is therefore rewritten to `"use_rslora": false` after generation, and a 100-item smoke
run verifies each adapter is alive before any full evaluation.

### 3.4 Descriptions

The descriptions are the paper-time text from the T2L repository's own evaluation config
(`configs/hyper_lora_decontam_lol_tasks.yaml`), copied verbatim into
`configs/task_descriptions.yaml`. One description per task, generated once. Nothing in this
pipeline is trained on the evaluation data.

---

## 4. Data and splits

| | |
|---|---|
| Tasks | `gsm8k`, `arc_challenge`, `boolq`, `hellaswag`, `winogrande` (T2L's suite) |
| Test set | 1,000 items per task (the official test split; validation where the test split is unlabelled) |
| `D_train` | 150 items from the train split |
| `D_pareto` | 300 items from the train split, used as GEPA's selection set |
| Leakage control | splits are deduplicated by normalised question text and a hard guard rejects any run where a question appears in two splits |
| Seed | 0 |

The optimiser never sees a test item: `run_gepa` raises if any example passed to it has
`split == "test"`, and `build_feedback` refuses to describe a test item.

---

## 5. The `t2l_gepa_opt` flow

### 5.1 One-time preparation (per task)

1. Generate the adapter from the task description (`scripts/gen_mistral_loras.py`).
2. Force `use_rslora: false`.
3. Start vLLM with the base model and all five adapters, so switching arms is a request
   parameter, not a restart.

After this, the adapter is a fixed artifact: `t2l_gsm8k`, `t2l_arc_challenge`, `t2l_boolq`,
`t2l_hellaswag`, `t2l_winogrande`.

### 5.2 The search loop

```
                      ┌──────────────────────────────────────────────┐
                      │                                            │
  seed instruction ──► GEPA proposes a new instruction               │
  (= task rules)             │                                     │
                             ▼                                     │
            3 demos + instruction + item                          │
                             │                                     │
                             ▼                                     │
                 adapter t2l_<task>  (T=0.6)                       │
                             │                                     │
                             ▼                                     │
              extract answer ─► compare with gold ─► score         │
                             │                                     │
                             ▼                                     │
        feedback: verdict + model output + gold + reference        │
                             │                                     │
                             ▼                                     │
              reflection LM (deepseek-v4.1-flash) ────────────────┘
```

Step by step, per candidate:

| step | what happens | code |
|---|---|---|
| 1 | Build the prompt: demo block, then the candidate instruction, then the item (`Passage`/options/`Answer:` cue as the task requires) | `gepa_arm._compose` |
| 2 | Send it to the **adapter**, not the base model: `model="t2l_<task>"` | `gepa_arm._Adapter.evaluate` |
| 3 | Extract the answer with the shared extractor and score it against the gold answer | `scoring.extract_answer` + `scoring.score` |
| 4 | Build textual feedback: verdict, the model's output, the gold final answer, and the dataset's reference reasoning (capped at 1,200 chars) | `feedback.build_feedback` |
| 5 | Ask the reflection LM for a better instruction, given the current instruction and up to a minibatch of these feedback rows | `_reflection_fn` |
| 6 | Evaluate the candidate on the selection set; keep it only if it lands on or improves the Pareto frontier | GEPA engine |

Settings:

| | |
|---|---|
| Seed instruction | the task's own rules (`prompts.rules_for`), e.g. "Choose the correct option… write `The answer is (X)`" |
| Demos | fixed 3-shot block; GEPA may rewrite the instruction only |
| Budget | 1,500 metric calls; 300 are consumed by the initial `D_pareto` pass, leaving 1,200 for search |
| Metric call | one rollout = one item scored by the model |
| Rollout decoding | T=0.6, `max_tokens` 512 |
| Seed | 0 |

### 5.3 Final evaluation

The search maximises `D_pareto`, so its own score is not comparable to the other arms. The best
instruction is therefore re-evaluated **greedily on the 1,000-item test set, still on the
adapter**, exactly like `t2l_icl` is evaluated:

```python
summary = run_arm(job.arm, job.task, job.seed, target,
                  prompt_fn_from(result.best_prompt, few_shot_block), arm_model, cfg, ...)
```

`scripts/run_grid.py` picks `arm_model = "t2l_<task>"` for this arm and the base model id for
every other GEPA arm; that single line is the whole difference between `gepa_3shot` and
`t2l_gepa_opt`.

### 5.4 Gate

A run "passes" only if the final program beats the seed program on `D_pareto` by at least 1 pp.
Otherwise it is reported as "found nothing" rather than as a result. On this run, 4 of 5 tasks
passed (ARC-Challenge did not: 0.733 vs 0.739).

---

## 6. The reflection model

| | |
|---|---|
| Model | **`deepseek-v4.1-flash`** |
| Access | OpenAI-compatible endpoint (`https://hy-llm.bioturing.com/v1`), no local GPU |
| Credential | `REFLECT_API_KEY`, else the user's `~/.config/opencode/opencode.jsonc`; never stored in the repo |
| Decoding | temperature 1.0, `max_tokens` 1,024 |
| Calls per task | 6–30 (69 over the five tasks) |
| What it receives | the current instruction + a minibatch of (input, generated output, gold answer, reference reasoning, verdict) rows |
| What it returns | a new instruction, as plain text |

The reflection model never sees the test split, and it does not see weights — only text. This is
the reason the method is cheap and also the reason its ceiling is low: the only thing that can
change is prose.

For the description-search experiment (a different arm, `desc_search`) the same model is used
with a different prompt that asks for a rewritten *task description* rather than an instruction.

---

## 7. Comparison protocol

| arm | weights | prompt | what isolates |
|---|---|---|---|
| `base` | base | zero-shot | what the model already does |
| `icl3` | base | 3 demos, fixed instruction | value of demos alone |
| `t2l` | adapter | zero-shot | value of the adapter alone |
| `t2l_icl` | adapter | 3 demos, fixed instruction | adapter + demos (paper configuration) |
| `gepa_3shot` | base | GEPA-optimised instruction + 3 demos | value of prompt search on the base model |
| `t2l_gepa` | adapter | the base-model's optimised instruction + 3 demos | whether a prompt transfers to an adapted model |
| **`t2l_gepa_opt`** | adapter | **GEPA-optimised instruction, searched against the adapter** + 3 demos | **the combination** |

All arms share:

- the same 1,000 test items per task and the same item ids;
- one answer extractor and one scoring function (`t2lgepa.scoring`);
- greedy decoding for every reported number;
- 95% confidence intervals by bootstrap over items; arm-vs-arm comparisons use a **paired**
  bootstrap over identical item ids.

---

## 8. Cost accounting

| quantity | meaning |
|---|---|
| metric call | one model evaluation during the search |
| reflection call | one request to the reflection LM |
| wall time | GPU time for the whole task, search + final test pass |
| generated tokens | tokens emitted by the model |

Observed, per task:

| task | metric calls | reflection calls | wall (s) | test score |
|---|---|---|---|---|
| gsm8k | 1,242 | 7 | 696 | 49.6% |
| arc_challenge | 1,236 | 6 | 126 | 74.2% |
| boolq | 1,380 | 30 | 174 | 85.9% |
| hellaswag | 1,236 | 6 | 147 | 65.9% |
| winogrande | 1,320 | 20 | 147 | 67.8% |
| **total** | **6,414** | **69** | **1,290 s (21.5 min)** | |

For comparison, the same protocol on the base model (`gepa_3shot`) spent 6,312 metric calls and
52 reflection calls but **2,364 s (39.4 min)**: the adapter answers with ~3× fewer tokens, so
each rollout is cheaper even though the number of rollouts is the same.

---

## 9. Results

| task | base | t2l_icl | gepa_3shot | t2l_gepa (transfer) | **t2l_gepa_opt** |
|---|---|---|---|---|---|
| gsm8k | 47.5 | **49.7** | 45.4 | 45.5 | 49.6 |
| arc_challenge | 73.9 | 73.7 | 73.0 | 73.7 | **74.2** |
| boolq | 82.4 | **86.1** | 83.3 | **86.2** | 85.9 |
| hellaswag | 47.7 | 63.9 | 54.7 | 64.2 | **65.9** |
| winogrande | 59.3 | 64.6 | 64.3 | 58.6 | **67.8** |
| **mean Δ vs base** | | +5.4 | +2.0 | +3.5 | **+6.5** |

Against `t2l_icl`, paired bootstrap: winogrande **+3.2** [+0.8, +5.7]; hellaswag +2.0
[−0.1, +4.1]; arc_challenge +0.5 [−1.6, +2.6]; gsm8k −0.1 [−3.0, +2.8]; boolq −0.2 [−1.7, +1.2].
Mean +1.1 pp.

---

## 10. Reproduce

```bash
# adapter (once per task, frozen afterwards)
uv run python scripts/gen_mistral_loras.py --config configs/mistral.yaml --tasks winogrande

# server: base + 5 adapters on GPU 7
uv run python scripts/write_demo_config.py --gpu-util 0.90 --max-loras 8 --out serve_config.yaml
CUDA_VISIBLE_DEVICES=7 .venv-serve/bin/vllm serve \
  --config /data/quan.lt/temp/t2l-mistral/serve_config.yaml

# the combined arm (reflection key from REFLECT_API_KEY or the opencode config)
uv run python scripts/run_grid.py --config configs/mistral.yaml \
  --gepa-only --gepa-arms t2l_gepa_opt

# tables
uv run python scripts/make_tables.py --results /data/quan.lt/temp/t2l-mistral/results \
  --out docs/report/mistral
```

Artifacts per task in the results directory: `t2l_gepa_opt_<task>_s0.jsonl` (summary + per-item),
`.generations.jsonl` (raw outputs), `.gate.json` (gate verdict), and
`gepa_<task>_s0_best_prompt.txt` (the winning instruction).

---

## 11. Limitations of this method

1. **One seed, greedy final scoring.** Intervals cover item sampling, not run-to-run variance.
2. **The adapter is one sample.** It comes from the first paper-time description; the paper
   averages three generated adapters per task.
3. **The search optimises 300 items.** With ±3 pp of selection noise, a +1 pp mean gain is at the
   edge of what this protocol can resolve; only WinoGrande's +3.2 pp is individually significant.
4. **The reflection model is not the paper's.** `deepseek-v4.1-flash` replaces GPT-4.1-mini, and
   the budget is 1,500 metric calls rather than the paper's.
5. **The harness is not lm-eval and is easier**: base Mistral scores +8 to +14 pp above the
   published base on ARC-C, BoolQ and WinoGrande, which compresses every delta. Only
   within-harness comparisons are meaningful.
6. **Prompt search cannot add knowledge.** It can only change how the adapter is asked; the
   ceiling is set by the weights. The observed pattern — gains on format-bound tasks, none where
   `t2l_icl` is already at its ceiling — is consistent with that.
