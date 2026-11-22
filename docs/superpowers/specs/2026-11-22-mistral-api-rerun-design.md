# Design: Mistral-7B four-method comparison over an API endpoint, with full artifacts

Date: 2026-11-22. Owner: study continuation on branch `feat/t2l-then-gepa`.

## Intent

Produce one clean, self-consistent run of four methods on five tasks, accessed only through an
OpenAI-compatible HTTP endpoint, and keep every artifact needed to write the report and to build
a version-comparison web demo later.

## Decisions (confirmed with the user)

1. The four reported methods are `base`, `t2l_icl` (T2L, paper configuration), `gepa_3shot`,
   `t2l_gepa_opt` (frozen T2L adapter + GEPA-searched instruction). `icl3` and `t2l` (zero-shot)
   are kept as controls.
2. Re-run everything fresh into a new results directory; old runs stay archived, untouched.
3. Adapters ship as a compressed tarball, not committed to git.
4. Demo work is preparation only: a version manifest plus a smoke script, no web UI.

## Constraints

- Base model `mistralai/Mistral-7B-Instruct-v0.2`; checkpoint `trained_t2l/mistral_7b_t2l`.
- All model access is `POST /v1/chat/completions`; the adapter name is just the `model` field.
- Public documents name no GPU model, GPU index or VRAM figure. Cost is reported as endpoint
  wall seconds, generated tokens and call counts. No claim that T2L needs no GPU: adapters still
  require LoRA-capable serving.
- Results stay out of git; prompts, manifest, metrics and docs are committed.
- One seed (0), greedy final scoring, 1,000 test items per task, GEPA budget 1,500 metric calls.

## Known defect to fix first

`export_best_prompt()` writes `gepa_<task>_s0_best_prompt.txt` for every GEPA arm, so
`t2l_gepa_opt` overwrote `gepa_3shot`'s prompts. Seed prompts were never written. Prompt
artifacts must be arm-scoped, and the old `gepa_3shot` prompts recovered from `*.job.json`.

## Approach

One endpoint serves the base model plus the five adapters. A single `run_grid` invocation runs
the four target arms and the two GEPA arms into `runs/mistral-7b-v1/results`, writing seed, best,
candidate-history and rendered-example prompt artifacts per arm. A bundle builder then collects
adapters, prompts, metrics and a version manifest into a tarball; a smoke script exercises all
four versions through the endpoint exactly the way the future web app will.

## Non-goals

No web UI, no new tasks, no hypernetwork training, no history rewrite of earlier hardware
mentions, no change to the T2L weights.
