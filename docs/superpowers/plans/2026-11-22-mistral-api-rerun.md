# Mistral API re-run + artifact bundle Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** One fresh four-method run over an OpenAI-compatible endpoint, with arm-scoped prompt artifacts and a versioned artifact bundle for the report and a later demo.

**Architecture:** Fix prompt persistence, extend `run_grid` with a results-dir override and arm-labelled prompts, run all six arms on one endpoint, then build a versioned bundle (adapters + prompts + metrics + manifest + tarball) and regenerate the public docs without hardware identifiers.

**Tech Stack:** Python 3.11, pytest, httpx client, vLLM OpenAI-compatible server, GEPA.

**Spec:** `docs/superpowers/specs/2026-11-22-mistral-api-rerun-design.md`

## Global Constraints

- Fresh results only in `/data/quan.lt/temp/t2l-mistral/runs/mistral-7b-v1/results`.
- Prompt file names: `<arm>_<task>_s<seed>_{seed_prompt,best_prompt}.txt`, `<arm>_<task>_s<seed>_candidates.json`, `<arm>_<task>_s<seed>_rendered_example.txt`.
- `t2l_gepa` (legacy transfer arm) must read `gepa_3shot`'s prompt only.
- No `A100`, `GPU 7`, or VRAM numbers in `README.md`, `docs/report/t2l-gepa-comparison.md`, `docs/report/t2l-gepa-opt-method.md`.
- No git mutation without the user's confirmation at the end of the run.

## Review Focus

- Two GEPA arms writing to the same directory: assert files never collide (Task 1 test).
- Empty/missing GEPA candidate history on a partial run: bundle must not crash (Task 4).
- Re-running an arm must not resurrect the legacy shared prompt file (Task 1).
- Bundle built before a task finished: manifest must mark the version incomplete (Task 4).
- Docs regenerated from a different results dir must not mix arms across runs (Task 5).

---

### Task 1: Arm-scoped prompt artifacts

**Files:** `src/t2lgepa/gepa_arm.py` (export/load, `run_gepa`), `src/t2lgepa/prompts.py`, `tests/test_gepa_arm.py`

**Produces:** `export_best_prompt(result, out_dir, task, seed, arm)`, `export_seed_prompt(text, out_dir, task, seed, arm)`, `export_candidates(result, out_dir, task, seed, arm)`, `load_best_prompt(results_dir, task, seed, arm="gepa_3shot")`.

- [x] Failing test: exporting two arms for one task yields two distinct best-prompt files and two seed files; `load_best_prompt(..., arm="gepa_3shot")` returns the `gepa_3shot` text.
- [x] Run the test, confirm it fails on the current shared filename.
- [x] Implement arm-scoped export/load; write the seed prompt before `optimizer(...)`; dump `getattr(result, "candidates", [])` with scores, tolerating missing attributes.
- [x] Recover the old `gepa_3shot` prompts from `results/gepa_3shot_<task>_s0.job.json` into the new names.
- [x] Full `pytest` + `ruff`.

### Task 2: Runner plumbing

**Files:** `scripts/run_grid.py`, `src/t2lgepa/config.py` (only if needed), `tests/test_schedule.py`

**Produces:** CLI `--results-dir PATH`; `run_gepa(..., arm=...)` passed `job.arm`; optional `--target-api-key-env`.

- [x] Failing test: `main([... "--dry-run"])` with `--results-dir` plans jobs without touching the config default directory.
- [x] Implement override via `dataclasses.replace(cfg, results_dir=...)`; pass `arm=job.arm`; export seed, best, candidates and a rendered example built from `splits.train[0]`.
- [x] `pytest` + `ruff`; dry-run lists 20 target + 10 GEPA jobs for the six arms.

### Task 3: Fresh endpoint run

**Files:** `/data/quan.lt/temp/t2l-mistral/serve_config.yaml` (regenerated), run logs.

- [x] Start vLLM with the base model and five adapters; assert `/v1/models` lists exactly six ids.
- [x] `run_grid --arms base,icl3,t2l,t2l_icl --gepa-arms gepa_3shot,t2l_gepa_opt --results-dir ...` in the background.
- [x] Verify 30 `*.job.json` records, 1,000 scored items per arm/task, and prompt artifacts for all ten GEPA runs.
- [x] Sanity-check new scores against the archived run; investigate any task differing by more than 3 pp.

### Task 4: Versioned bundle + demo smoke

**Files:** `scripts/build_artifact_bundle.py`, `scripts/demo_smoke.py`, `demo/mistral-7b-v1.manifest.json`, `tests/test_bundle.py`

**Produces:** `build_bundle(run_dir, lora_root, out_dir) -> Path` writing `manifest.json` with per-version `{version_id, label, arm, model, prompt_files, adapter, metrics, complete}`; `mistral-7b-v1-artifacts.tar.gz`.

- [x] Failing test: a run dir with one finished arm and one missing arm produces `complete: false` for the missing version and no exception.
- [x] Implement the builder (adapters copied, prompts and metrics collected, sha256 of the tarball recorded).
- [x] `demo_smoke.py --endpoint ... --manifest ...` sends one train-free sample per task to all four versions and prints outputs side by side.
- [x] Build the bundle; run the smoke script against the live endpoint.

### Task 5: Public docs

**Files:** `README.md`, `docs/report/t2l-gepa-comparison.md`, `docs/report/t2l-gepa-opt-method.md`, `docs/report/mistral-api-v1/{accuracy,cost}.md`, `docs/report/prompts-v1.md`

- [x] Regenerate accuracy/cost tables from the new run only.
- [x] Rewrite the main table as four methods plus two controls; update deltas and paired CIs.
- [x] Add the prompt section (seed vs best for both GEPA arms, one real example) and the artifact/demo section.
- [x] Replace hardware identifiers with "an OpenAI-compatible endpoint"; cost in wall seconds, tokens and calls.
- [x] Grep the three public docs for `A100|GPU 7|80GB|MiB` and confirm no hits.

### Task 6: Verification and handoff

- [x] `uv run pytest -q` and `uv run ruff check src tests scripts` clean.
- [x] Present results, artifact paths and tarball size; ask before committing and pushing.
