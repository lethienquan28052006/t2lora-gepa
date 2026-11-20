# T2L, GEPA, and T2L+GEPA on Mistral-7B: methods and results

Date: 2026-11-20
Model: `mistralai/Mistral-7B-Instruct-v0.2`
Artifacts: `/data/quan.lt/temp/t2l-mistral/` · code: branch `feat/t2l-gepa-combo`

---

## 1. Executive summary

We compared three ways of adapting Mistral-7B-Instruct-v0.2 to five benchmarks:

| method | what changes | mean accuracy gain over the base model |
|---|---|---|
| **T2L** (`t2l_icl`) | weights: a LoRA generated from a task description | **+5.4 pp** |
| **GEPA** (`gepa_3shot`) | prompt: an instruction evolved by reflective search | **+2.0 pp** |
| **T2L + GEPA** (`desc_search`) | the *description* T2L reads, searched by GEPA | **+2.2 pp** *(2 tasks only; no better than the shipped description)* |

Three findings dominate:

1. **T2L is the strongest method and the cheapest by three orders of magnitude.**
   +5.4 pp for one hypernetwork forward pass (~1 s) and a 14 MB artifact, against +2.0 pp for
   ~1,250 rollouts and 7–18 reflection calls per task.
2. **GEPA's gain is mostly its demo block, not its instruction.** Against `icl3` — the same
   3-shot scaffold with the original instruction — GEPA is +1.1 pp on average, and positive on
   only one of five tasks (GSM8K, +5.5 pp).
3. **Combining them does not help, in the form we could test.** Searching the task description
   with a frozen T2L produced ten candidate adapters and none beat the shipped description.
   The pipeline also has a ~1.4 pp noise floor, so any gain would have to be larger than that
   to be visible.

---

## 2. Benchmark setup

### 2.1 Model and serving

| | |
|---|---|
| Base model | `mistralai/Mistral-7B-Instruct-v0.2` (7.2B, fp16) |
| Serving | one vLLM 0.31.0 process on GPU 7 (A100-80GB), base model + 5 LoRA modules |
| LoRA slots | `max_loras` 8 for the main grid, 4 for the description search |
| Prompt format | vLLM applies the tokenizer's chat template (`[INST] … [/INST]`) |
| Decoding | greedy (T=0), `max_tokens` 512, for **every** reported number |

The same server, the same five items per task, the same answer extractor and the same
decoding settings are used by every arm. Only the adaptation surface changes.

### 2.2 Benchmarks and splits

Five tasks from T2L's own suite: `gsm8k`, `arc_challenge`, `boolq`, `hellaswag`, `winogrande`.

| | |
|---|---|
| Test items | 1,000 per task (5,000 per arm) |
| Train pool | 150 items for optimisation (`D_train`) |
| Selection set | 300 items for GEPA's Pareto frontier (`D_pareto`); 120 for the description search |
| Leakage control | splits deduplicated by normalised question; a hard guard fails the run if a question appears in two splits |
| Seed | 0 (all greedy arms deterministic given the prompt) |

### 2.3 Metrics

Accuracy against the gold answer, with one shared extractor (`scoring.extract_answer`) for all
arms: a `#### <number>` marker for GSM8K, a letter for multiple-choice, `yes`/`no` for BoolQ.
95% intervals are bootstrap over test items; arm-vs-arm comparisons use a **paired** bootstrap
over the same item ids.

---

## 3. Methods, arm by arm

### 3.1 `base` — zero-shot, no adaptation

One instruction per task ("Solve the problem, then write `#### <number>`", "Choose the correct
option, then write `The answer is (X)`", and so on), the item, and an `Answer:` cue. This is
the reference for every delta in this report.

### 3.2 `icl3` — in-context learning, no weight change

The same prompt, prefixed with three demonstrations drawn from `D_train`, formatted exactly
like the target item. `icl3` exists to separate "the demos helped" from "the method helped";
without it, GEPA's gain cannot be attributed.

### 3.3 `t2l` — Text-to-LoRA, zero-shot

T2L is a **hypernetwork** trained to map a natural-language task description to a LoRA.

```
description ──► gte-large-en-v1.5 ──► hypernetwork (frozen) ──► LoRA (r=8, α=16, q_proj/v_proj)
```

Implementation details that matter:

- Checkpoint: `SakanaAI/text-to-lora → trained_t2l/mistral_7b_t2l` (SFT variant, `hypermod.pt`,
  263 MB). **Nothing is trained on our evaluation data** — adaptation is inference.
- `use_rslora` is **forced to `false`**. The released `adapter_config.json` ships `true`, but
  the published numbers were produced with vLLM 0.5.4's plain `α/r` scaling; with rsLoRA
  scaling the adapter is ~2.8× too strong and collapses to near-chance. This was verified on
  a 100-item smoke run before the grid.
- Descriptions are the paper-time text from the T2L repo's eval config
  (`configs/task_descriptions.yaml`), verbatim.
- Cost: one forward pass per task (~1 s cold, 0.03–0.04 s once the hypernetwork is warm),
  a 14 MB adapter.

### 3.4 `t2l_icl` — T2L + 3-shot (the headline T2L arm)

Same adapter as `t2l`, with the three demonstrations. This is the paper's own evaluation
configuration, and it matters: without demos the adapter sometimes ignores the answer-format
instruction (see §5.3).

### 3.5 `gepa_3shot` — reflective prompt evolution

GEPA proposes new **instructions**, runs them on training items, reads the failures in natural
language, and keeps a Pareto frontier of attempts.

| | |
|---|---|
| Seed instruction | the task's own rules (not GSM8K's, see §5.2) |
| Budget | 1,500 metric calls (rollouts), of which 300 are the initial selection-set pass |
| Selection set | `D_pareto`, 300 items |
| Demos | fixed 3-shot block; GEPA may rewrite the instruction but not the demos |
| Reflection LM | `deepseek-v4.1-flash` through an OpenAI-compatible endpoint, temperature 1.0 |
| Feedback per item | model output + gold answer + correctness |
| Gate | the run must beat its seed program on `D_pareto` by ≥1 pp, else it is reported as "found nothing" |

The final instruction is then scored **greedily on the 1,000-item test set** — the Pareto score
is measured on the set the optimiser maximised and is not comparable to the other arms.

### 3.6 `t2l_gepa` — the naive composition (control, not the combo)

Before building a search loop we tested the cheap version: take the instruction GEPA evolved
**for the base model** and apply it on top of the adapter, with the same demos. Zero extra
compute.

This is not the combination we report as "T2L+GEPA" — it is the control that showed a
base-optimised prompt does not transfer to an adapted model (§5.4).

### 3.7 `desc_search` — the actual T2L+GEPA combination

Here GEPA searches the **task description**, and T2L turns each candidate description into a
new adapter. The hypernetwork stays frozen; the search moves its *input*.

```
        ┌──────────────────────────── GEPA loop ────────────────────────────┐
        │                                                                   │
description ──► hypernetwork (frozen, 0.03-0.04 s) ──► LoRA                  │
                                                          │                   │
                                          POST /v1/load_lora_adapter          │
                                                          │                   │
                     15 train items, 3-shot, T=0.6 ──► score + failure text    │
                                                          │                   │
                                    reflection LM (deepseek) ──► new description
```

Concrete pieces:

- **Frozen generator.** A long-lived worker process holds the hypernetwork, the base model and
  the text encoder. It speaks JSON lines on stdin/stdout (`{"id", "description"}` →
  `{"id", "path", "seconds"}`), so loading costs 16.2 s once and each adapter costs 0.03–0.04 s
  instead of a 16 s process restart.
- **Dynamic adapters.** vLLM must run with `VLLM_ALLOW_RUNTIME_LORA_UPDATING=1`, which exposes
  `POST /v1/load_lora_adapter` and `/v1/unload_lora_adapter`. Each candidate is loaded under a
  name derived from a hash of its description (`desc_<sha1>`), and the model name in the
  request switches to that adapter.
- **Candidate = description.** The candidate dict is `{"instruction": <description>}`, but our
  proposer treats it as a task description. GEPA's built-in proposer is written for the
  instruction that produced the sampled outputs and returned **zero** candidates here; a
  description-specific proposer fixed that (§5.5).
- **Proposer prompt.** The current description, plus up to six (input, output, feedback) rows
  from the adapted model, plus explicit rules: 2–5 sentences, plain prose, describe the task,
  the answer format and the reasoning skill, do not mention specific examples, reply with the
  description only.
- **Budget.** 900 metric calls, `D_pareto` = 120 items, reflection minibatch 15. Small on
  purpose: it bounds the experiment to ~15 minutes per task.
- **Final evaluation.** The best description is regenerated into an adapter, loaded, and scored
  greedily on the full 1,000-item test set — the same protocol as every other arm.

---

## 4. Results

### 4.1 Main table (accuracy on 1,000 test items per task)

| task | base | t2l (0-shot) | **t2l_icl** | **gepa_3shot** | t2l_gepa (control) |
|---|---|---|---|---|---|
| gsm8k | 47.5 | 39.6 | **49.7** | 45.4 | 45.5 |
| arc_challenge | 73.9 | 70.2 | 73.7 | 73.0 | 73.7 |
| boolq | 82.4 | 85.2 | **86.1** | 83.3 | **86.2** |
| hellaswag | 47.7 | 61.3 | **63.9** | 54.7 | **64.2** |
| winogrande | 59.3 | 27.9 | **64.6** | 64.3 | 58.6 |
| **mean Δ vs base** | | −5.3 | **+5.4** | **+2.0** | **+3.5** |

### 4.2 T2L vs GEPA, task by task (paired bootstrap, 95% CI)

| task | T2L Δ vs base | GEPA Δ vs base | GEPA − T2L |
|---|---|---|---|
| gsm8k | +2.2 [−1.2, +5.6] | −2.1 [−5.5, +1.3] | −4.3 [−7.6, −0.9] |
| arc_challenge | −0.2 [−2.8, +2.3] | −0.9 [−3.3, +1.5] | −0.7 [−3.2, +1.8] |
| boolq | +3.7 [+2.0, +5.5] | +0.9 [−0.7, +2.5] | −2.8 [−4.3, −1.3] |
| hellaswag | +16.2 [+12.9, +19.6] | +7.0 [+3.8, +10.3] | −9.2 [−11.9, −6.5] |
| winogrande | +5.3 [+2.0, +8.6] | +5.0 [+1.7, +8.2] | −0.3 [−3.5, +2.9] |

T2L wins the mean by 3.4 pp and is ahead on 4 of 5 tasks; the losses are significant on three
of them.

### 4.3 GEPA vs its own fair baseline (`icl3`)

| task | GEPA − icl3 | 95% CI |
|---|---|---|
| gsm8k | **+5.5** | [+2.2, +8.9] |
| arc_challenge | −1.2 | [−2.3, −0.2] |
| boolq | −0.1 | [−0.5, +0.2] |
| hellaswag | +0.1 | [−1.0, +1.3] |
| winogrande | +1.1 | [−1.9, +4.1] |

This is the cleanest result in the study. GEPA's instruction is worth about **nothing on top of
the three demonstrations it is given**, except on GSM8K, where reflection genuinely adds
+5.5 pp. The "+2.0 pp over base" in §4.1 is mostly the demos.

### 4.4 The combination

| arm | gsm8k | arc_c | boolq | hellaswag | winogrande | mean Δ vs base |
|---|---|---|---|---|---|---|
| t2l_icl (shipped description) | **49.7** | 73.7 | 86.1 | 63.9 | **64.6** | **+5.4** |
| t2l_gepa (base-evolved prompt, control) | 45.5 | 73.7 | 86.2 | 64.2 | 58.6 | +3.5 |
| desc_search (searched description) | 48.0 | — | — | — | 63.2 | +2.2 (2 tasks) |

- The **control** is a wash on three tasks (+0.0 to +0.3 pp) and significantly worse on two
  (gsm8k −4.2 [−7.2, −1.2], winogrande −6.0 [−8.9, −3.2]). A prompt optimised for the base
  model fights the adapter: on WinoGrande the share of outputs with no extractable answer rises
  from 8.8 % (`t2l_icl`) to 12.4 %.
- The **description search** explored 10 candidate adapters on WinoGrande and 1 on GSM8K, and
  accepted none: no candidate beat the seed description on the 120-item selection set. The
  final adapters scored 63.2 % and 48.0 % against 64.6 % and 49.7 % for the shipped ones.

---

## 5. What we had to fix to make these numbers trustworthy

Every item below invalidated at least one earlier run. They are part of the method, not
footnotes.

### 5.1 BoolQ never saw its passage

The passage was stored but never rendered into the prompt, so the model answered from the
question alone. Fixing it moved the base arm from 56.1 % to **82.4 %**. All BoolQ numbers from
the earlier Gemma run are invalid and should not be quoted.

### 5.2 GEPA was seeded with the wrong task

The seed instruction was the GSM8K one ("solve the arithmetic word problem, answer `#### N`")
for every task. Reflection spent its budget undoing that. Fixed by seeding each task with its
own answer format.

### 5.3 GEPA's prompt renderer dropped the options

`_compose` rendered answer options only for `arc_challenge`, so HellaSwag, WinoGrande and
BoolQ were optimised **with no choices shown**. The seed program scored 0.267 on HellaSwag
instead of 0.557. The first GEPA sweep was deleted and rerun.

### 5.4 The zero-shot adapter ignores the output format

On WinoGrande the `t2l` arm answers with the entity (`" Sarah."`) rather than
`The answer is (A).`: **59.6 %** of outputs had no extractable answer. Three demos fix it
(8.8 %). This is why the headline arm is `t2l_icl`, and why the `t2l` row in §4.1 is not a
measure of the adapter's knowledge.

### 5.5 GEPA's proposer does not know what a task description is

For the description search, the default proposer returned no candidates at all in ten
iterations, because it is written for the instruction that produced the sampled outputs. A
custom proposer that asks explicitly for a rewritten description produced 10 candidates on
WinoGrande.

### 5.6 There is a ~1.4 pp pipeline floor

The same description, regenerated and loaded dynamically (`max_loras` 4), scores 63.2 %
instead of 64.6 % on WinoGrande. Same adapter, different vLLM configuration. Any claim about a
description-search gain must exceed roughly this much to be visible.

---

## 6. Cost

| method | per task | artifact | setup |
|---|---|---|---|
| base / icl3 | 0 | — | — |
| T2L | 1 hypernetwork forward pass (~1 s; 0.04 s warm) | 14 MB LoRA | 16.2 s to load the hypernetwork |
| GEPA | ~1,250 rollouts + 7–18 reflection calls, 294–349 s GPU | prompt text | none |
| T2L+GEPA | ~900 rollouts + 10 adapter generations, ~15 min | 10 LoRAs + description | same 16.2 s |

GPU-seconds over the five tasks for the non-GEPA arms: base 802, icl3 793, t2l 382, t2l_icl 415.
The `t2l` arms generate roughly **3× fewer tokens** than base/ICL because the adapter answers
directly instead of writing out chain-of-thought.

---

## 7. Interpretation

1. **The two methods do different things.** T2L changes what the model knows how to do; GEPA
   changes how the request is phrased. On tasks that are format-bound (BoolQ, WinoGrande) the
   prompt and the demos do most of the work; on HellaSwag the adapter adds +16 pp that no
   prompt in our search reached.
2. **Where they tie, the gain is a convention, not a capability.** WinoGrande at 64.6 (T2L) vs
   64.3 (GEPA) vs 63.2 (icl3) says the last five points come from agreeing on an answer format.
3. **Composition is not free.** Optimising the two surfaces independently gives a prompt and a
   set of weights that disagree; the result is worse than either alone on two tasks. A
   meaningful combination needs co-optimisation — GEPA running with the adapter in the loop —
   which this study did not do.
4. **Cost asymmetry is the practical result.** A 14 MB artifact emitted in a second matches or
   beats a thousand-rollout search, and it can be shipped, cached and swapped per request.

---

## 8. Threats to validity

1. **One seed, greedy decoding.** Intervals cover item sampling, not run-to-run variance.
   vLLM's LoRA path is documented as non-deterministic even at temperature 0; §5.6 measures
   ~1.4 pp of it.
2. **The harness is not lm-eval and is easier.** Mistral base is +8 to +14 pp above the
   published base on ARC-C, BoolQ and WinoGrande, so absolute scores are not comparable to the
   paper — only within-harness deltas are. This also compresses the deltas, because the base
   starts closer to the ceiling.
3. **One adapter per task**, from the first paper-time description. The paper averages three
   generated LoRAs per task.
4. **GEPA ran ~1,250 metric calls per task**, not the paper's budget, with
   `deepseek-v4.1-flash` rather than GPT-4.1-mini.
5. **The description search used a 120-item selection set**, too small to separate a 2 pp gain
   from noise. That is the main reason it accepted nothing.
6. **Out of scope:** HumanEval/MBPP (code execution) from T2L's suite, and HotpotQA / HoVer /
   PUPA / AIME / LiveBench from GEPA's, which need retrieval or a different task shape.

---

## 9. Reproduction

```bash
# adapters from descriptions (frozen hypernetwork)
uv run python scripts/gen_mistral_loras.py --config configs/mistral.yaml

# serve base + 5 adapters on one GPU
uv run python scripts/write_demo_config.py
VLLM_ALLOW_RUNTIME_LORA_UPDATING=1 .venv-serve/bin/vllm serve \
  --config /data/quan.lt/temp/t2l-mistral/serve_search.yaml

# comparison grid, then GEPA on the same server
uv run python scripts/run_grid.py --config configs/mistral.yaml --no-gepa
uv run python scripts/run_grid.py --config configs/mistral.yaml --gepa-only --gepa-arms gepa_3shot

# T2L+GEPA: search descriptions
uv run python scripts/search_descriptions.py --tasks winogrande,gsm8k --budget 900 --pareto 120

# tables
uv run python scripts/make_tables.py --results /data/quan.lt/temp/t2l-mistral/results \
  --out docs/report/mistral
```

## 10. Conclusion

On Mistral-7B-Instruct-v0.2 across five benchmarks, **T2L (+5.4 pp) beats GEPA (+2.0 pp) at a
fraction of the cost**, and most of GEPA's gain is attributable to the demonstrations it is
handed rather than to the instruction it evolves. Combining the two is possible without
retraining T2L — the hypernetwork is frozen and only its input text moves — but a
GEPA-searched description did not beat the shipped one, and a prompt optimised for the base
model actively hurts the adapter. The next experiment, if there is one, is co-optimisation:
run GEPA with the adapter in the loop, with a selection set large enough to resolve the
~1.4 pp noise floor.
