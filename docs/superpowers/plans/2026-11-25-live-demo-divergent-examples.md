# Live Demo Divergent Examples Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce one copy-ready Markdown catalog of 15 concise, real benchmark cases where the four live-demo methods disagree.

**Architecture:** A one-off read-only extraction joins canonical result records by test ID, selects three diverse correctness patterns per dataset, enriches inputs through the existing dataset loader and writes deterministic Markdown. A separate read-only validator checks the resulting document against source records; no runtime application code changes.

**Tech Stack:** Python standard library, existing `t2lgepa.data.load_task`, Markdown, canonical JSONL artifacts.

**Spec:** `docs/superpowers/specs/2026-11-25-live-demo-divergent-examples-design.md`

## Global Constraints

- Exactly 15 cases, three per task, using stored `mistral-7b-v1` records and the arm order Base, T2L+ICL, GEPA+ICL, T2L×GEPA.
- No fabricated content, model/API calls, full-generation dumps, aggregate claims or UI changes.
- Include every input field needed by Live demo and keep excerpts bounded/source-faithful.
- Do not commit or update PR #8 unless the user requests it.

## Review Focus

- Joining different item IDs or arms could misattribute outputs; validate every ID and row against source.
- Dataset enrichment could silently pair the wrong options/passage; assert IDs and gold match before writing.
- Markdown pipes/newlines could corrupt tables or inputs; escape excerpts and use fenced input blocks.
- Selection could collapse into one correctness pattern; inspect diversity within every task.
- Serving variation could be mistaken for guaranteed replay outputs; include the canonical-run caveat.

---

### Task 1: Build and validate the 15-case Markdown catalog

**Files:**
- Create: `docs/live-demo-divergent-examples.md`

**Interfaces:**
- Consumes: canonical `<arm>_<task>_s0.jsonl` item rows and existing `load_task(task, "test", cache_dir=cfg.cache_dir)` examples.
- Produces: a five-section, 15-case Markdown document with exact input fields, gold, method result tables, excerpts, correctness patterns and provenance.

- [ ] **Step 1: Define and run the failing validation contract.** Check that the target file exists, has five task sections and exactly 15 case IDs/exactly three per task, and that its embedded source metadata will be checkable against canonical rows; expected initial failure is the missing Markdown file.
- [ ] **Step 2: Extract candidate cases read-only.** Join all four arms by identical test ID, keep only differing correctness tuples, recover exact dataset inputs by ID and rank candidates deterministically for correctness-pattern and method-result diversity without invoking inference.
- [ ] **Step 3: Review the selection and write the Markdown.** Use three clear cases per task, include copy-ready fenced question/options/passage fields, gold, four-method prediction/correctness/excerpt tables, the correctness-order legend, canonical provenance and replay variation caveat.
- [ ] **Step 4: Validate source fidelity and usability.** Programmatically assert 15 unique IDs with three per task, differing correctness patterns, and every row's stored gold/prediction/correctness matching the document metadata; inspect the rendered Markdown structure and verify no result excerpt contains fabricated text or unescaped table delimiters.
- [ ] **Step 5: Run repository regression checks and inspect the final diff.** Run `pytest -q`, confirm no runtime files changed and report the new file plus exact case counts without committing.
