# GEPA Example Gallery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn Prompt optimization into an examples-first gallery with four real prompt-change stories and selected held-out wrong-to-right output comparisons, while retaining the existing raw history explorer.

**Architecture:** A read-only Python gallery service joins stored GEPA artifacts with matching per-item test records and caches the resulting stories. FastAPI serves that payload at one new endpoint; dependency-free HTML/CSS/JS renders guided story/case selection and keeps the current candidate workbench as a secondary explorer.

**Tech Stack:** Python 3.10+, pathlib/json dataclasses or dictionaries, FastAPI TestClient/pytest, vanilla JavaScript/CSS/HTML, existing Playwright browser checks.

**Spec:** `docs/superpowers/specs/2026-11-24-gepa-example-gallery-design.md`

## Global Constraints

- Use only stored `mistral-7b-v1` artifacts; no model or optimizer calls and no fabricated examples.
- Only genuinely changed pairs become stories; `icl3` pairs with `gepa_3shot`, and `t2l_icl` pairs with `t2l_gepa_opt`.
- Corrected cases must share task and item ID and have baseline `correct is False` plus optimized `correct is True`.
- Label cases as selected examples, never evidence of aggregate/statistically significant improvement.
- Retain existing prompt-library behavior, unchanged-prompt messaging and all four live comparison arms.
- Keep the gallery text-only, dependency-free, mobile-safe and accessible. No image or long-prompt generation.
- Missing/malformed optional story data must not break other stories or the live playground.
- Do not perform git mutations unless the user separately confirms them.

## Review Focus

- Wrong baseline pairings could attribute adapter effects to prompt search; pin exact arm mapping in service/API tests.
- Unchanged seed/best files could still contain wrong-to-right random variation; test that they never create stories.
- Duplicate/resumed JSONL records could duplicate cases; test last-record-per-ID behavior and stable unique case IDs.
- Missing choices or BoolQ passages could make cases unreadable; test lookup-backed options/passage and graceful record-only fallback.
- One corrupt story must not suppress healthy stories; test per-story error isolation and frontend empty/error states.

---

### Task 1: Stored optimization stories and corrected cases

**Files:**
- Create: `src/t2lgepa/webapp/examples.py`
- Modify: `src/t2lgepa/webapp/service.py`
- Test: `tests/test_prompt_examples.py`

**Interfaces:**
- Consumes: existing `<arm>_<task>_s0_{seed,best}_prompt.txt`, `<arm>_<task>_s0.jsonl`, and `DemoService._splits(task).test` examples.
- Produces: `PromptExampleLibrary(results_dir, item_lookup=None).stories() -> list[dict]`; `DemoService.test_item(task: str, example_id: str) -> dict | None`; each story has `id`, `task`, `arm`, `baseline_arm`, `title`, `changes: list[str]`, `seed`, `best`, and `cases`. Each case has `id`, `question`, `options`, `passage`, `gold`, `before: {text,pred,correct}`, `after: {text,pred,correct}`.

- [ ] **Step 1: Write failing service tests** with temporary stored prompts and item JSONL files. Assert the four curated pair definitions are attempted, unchanged prompts produce no story, exact baseline arms are used, only wrong-to-right matches survive, a maximum of three deterministic cases are returned per story, and options/passages are filled by `test_item` when available.
- [ ] **Step 2: Add resilience tests** for duplicate item IDs (latest record wins), corrupt/missing files affecting only one story, missing lookup data, and no reversed right-to-wrong cases being presented as improvements.
- [ ] **Step 3: Run tests to verify they fail** with `pytest tests/test_prompt_examples.py -v`; expected failure is the missing gallery interface.
- [ ] **Step 4: Implement the minimal reader** in `examples.py`: reviewed concise change metadata for the four known successful pairs, prompt equality checks, streamed JSONL loading, latest-by-ID joins, stable filtering/order/limit, optional item lookup and per-story exception isolation.
- [ ] **Step 5: Add `DemoService.test_item`** using its cached test splits, returning the same item fields as `sample` or `None` for an unknown ID.
- [ ] **Step 6: Run tests and lint** with `pytest tests/test_prompt_examples.py tests/test_prompt_library.py tests/test_webapp.py -v` and `ruff check src/t2lgepa/webapp/examples.py src/t2lgepa/webapp/service.py tests/test_prompt_examples.py`; expect PASS.

### Task 2: Gallery API

**Files:**
- Modify: `src/t2lgepa/webapp/app.py`
- Test: `tests/test_prompt_examples.py`

**Interfaces:**
- Consumes: `PromptExampleLibrary.stories()` and `DemoService.test_item()` from Task 1.
- Produces: `GET /api/prompt-examples -> {"stories": [...]}` using the app’s configured results directory.

- [ ] **Step 1: Write failing TestClient tests** for HTTP 200, real changed-story content and exact baseline/correctness transitions; include an empty/malformed run returning `{"stories": []}` without affecting `/api/meta` or `/api/prompt-library`.
- [ ] **Step 2: Run the new API tests** with `pytest tests/test_prompt_examples.py -k api -v`; expect 404 before implementation.
- [ ] **Step 3: Implement one cached library per app** and expose the endpoint; do not invoke model health, comparison or optimization code.
- [ ] **Step 4: Run backend regressions** with `pytest tests/test_prompt_examples.py tests/test_prompt_library.py tests/test_webapp.py -v`; expect PASS.

### Task 3: Examples-first frontend and retained raw explorer

**Files:**
- Modify: `src/t2lgepa/webapp/static/index.html`
- Modify: `src/t2lgepa/webapp/static/app.js`
- Modify: `src/t2lgepa/webapp/static/style.css`
- Test: `tests/e2e/check_demo.mjs`

**Interfaces:**
- Consumes: `/api/prompt-examples` and existing `/api/prompt-library` responses.
- Produces: successful-story cards selected by story ID, seed/best comparison and change list, case cards selected by stable case ID, full before/after outputs, and an explicit **Explore full candidate history** disclosure.

- [ ] **Step 1: Extend browser checks first**: opening Prompt optimization waits for four story cards; the first visible story is changed ARC-C rather than unchanged GSM8K; changing stories updates change bullets/seed/best; at least one case shows baseline wrong and optimized right with identical gold/item ID; multiple cases can be selected; the selected-case disclaimer mentions curated/selected and no aggregate claim.
- [ ] **Step 2: Preserve explorer checks** by opening the raw-history disclosure before all existing candidate, score, copy, unchanged-note and stale-request assertions. Add empty-API and malformed-story frontend states plus keyboard/focus and 390px no-horizontal-overflow assertions.
- [ ] **Step 3: Run `node tests/e2e/check_demo.mjs` against the deterministic demo** and record the expected selector/404 failures before frontend implementation.
- [ ] **Step 4: Implement semantic gallery markup and rendering** with independent story/case state and request IDs so stale responses cannot overwrite the current view. Reuse safe text-node construction; never inject stored generations as HTML.
- [ ] **Step 5: Implement compact responsive styling**, scrollable long prompts/outputs, visible wrong/right states and an accessible raw-history disclosure; bump static asset versions.
- [ ] **Step 6: Run the complete browser check**, inspect desktop/mobile screenshots in `artifacts/demo-checks/`, and iterate only on actual clipping, overflow or interaction failures.

### Task 4: Documentation and whole-change verification

**Files:**
- Modify: `docs/demo.md`
- Modify: `docs/superpowers/specs/2026-11-17-mistral-demo-web-design.md` only if its current two-view description needs a pointer to the approved gallery refinement
- Test: existing project and browser suites

**Interfaces:**
- Consumes: completed API and UI from Tasks 1–3.
- Produces: accurate operator/developer documentation and reproducible verification results.

- [ ] **Step 1: Document real gallery semantics**, baseline pairings, selected-case caveat, `/api/prompt-examples`, read-only caching and graceful missing-artifact behavior in `docs/demo.md`; keep startup commands unchanged.
- [ ] **Step 2: Run focused/backend suites** with `pytest tests/test_prompt_examples.py tests/test_prompt_library.py tests/test_webapp.py tests/test_demo_smoke.py -v` and `ruff check src/t2lgepa/webapp tests/test_prompt_examples.py`; expect PASS.
- [ ] **Step 3: Run the full test suite** with `pytest -q`; expect PASS, apart from any pre-existing environment-dependent failure that must be reproduced on the base revision before being reported.
- [ ] **Step 4: Re-run `node tests/e2e/check_demo.mjs`**, confirm zero page/console/request errors and visually verify updated desktop/mobile screenshots.
- [ ] **Step 5: Review the diff against the spec**, verify there are no generated images, inference calls or claims of statistical improvement, then report changed files and exact test results without committing.
