# Experiment Slides Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild chapter 4 into a natural, evidence-rich 30-minute presentation including an 8–10 minute AdaptLab demo.

**Architecture:** Keep the existing shared Beamer theme and single chapter file. Rewrite `parts/05_experiments.tex` as a focused main narrative with clearly separated appendix frames; keep all experimental values traceable to existing reports and do not touch other chapters.

**Tech Stack:** XeLaTeX/Beamer, TikZ, booktabs, existing Be Vietnam Pro theme, isolated local PDF tooling for verification.

**Spec:** `docs/superpowers/specs/2026-11-24-experiment-slides-redesign-design.md`

## Global Constraints

- Work on the existing `feat/slides` branch; do not create commits, push or mutate git history.
- Main narrative targets 20–22 minutes plus an 8–10 minute demo.
- Use `mistral-7b-v1` for headline values; label run A on analyses sourced from that run.
- Never infer or invent unreported values. Keep the two canonical unchanged-seed counts distinct: GEPA 4/5 and T2L+GEPA 2/5.
- Do not alter `main_uit.tex`, chapters 1–3 or the shared theme.

## Review Focus

- Paper zero-shot versus group ICL3 comparisons must not be presented as like-for-like replication (Task 1 source/data check).
- Point estimates, paired CIs and run-to-run variation must not be conflated (Task 1 source/data check).
- Dense CI/cost/pipeline slides must remain within the 16:9 content area (Task 3 rendered-page inspection and LaTeX log).
- Demo downtime must not lead to simulated results or an invented screenshot (Task 2 public/local verification).
- Appendix frames must not interrupt the main narrative or alter final-frame conclusions (Task 3 PDF frame order inspection).

---

### Task 1: Evidence-led main chapter and appendix

**Files:** Modify `slides/parts/05_experiments.tex`.

**Produces:** The approved main sequence plus appendix frames containing the full six-arm table, detailed GEPA setup and harness-validity notes.

- [ ] Replace generic/repeated frames with the exact measurements in the approved spec; use concise assertion-style titles and visible `Run A`/`run chuẩn` labels where needed.
- [ ] Build the WinoGrande case using the reported output-style example and run-A extraction rates; do not quote a fabricated full question or generation.
- [ ] Build the T2L significance and GEPA−ICL3 tables from `paired_ci.md`, canonical accuracy values and `prompts.md`; retain the distinction between highest observed score and statistical significance.
- [ ] Quantify composition transfer, description search, token counts, wall time, prompt growth and per-task run variance exactly as sourced in the spec.
- [ ] Retain the existing co-optimisation TikZ pipeline with only essential protocol annotations and move exhaustive setup/results material into appendix frames.
- [ ] Run a source-level reconciliation script over `05_experiments.tex` for required values, run labels and forbidden overclaims; inspect the resulting frame list to confirm one section divider, 11 main content frames, one demo frame and appendix separation.

### Task 2: Demo handoff and chapter documentation

**Files:** Modify `slides/parts/05_experiments.tex`, `slides/README.md`; add a real screenshot under `slides/figure/deck/` only if one can be captured from the actual service.

**Produces:** A demo frame that directs the live performance rather than listing features, plus up-to-date build/chapter documentation.

- [ ] Check the real AdaptLab service. If available, capture an actual screenshot with local browser tooling and use it with the URL/QR; if unavailable, use an honest live-demo sequence with URL and explicit no-fabrication fallback, not a mock or generated screenshot.
- [ ] Script the demo around one WinoGrande item, four actual method outputs, then the stored seed/candidate/best history; keep timing at 8–10 minutes and retain a backup path for service failure.
- [ ] Update `slides/README.md` to replace the stale slide-range description with the new main/appendix chapter structure and any new asset tooling.
- [ ] Verify the demo URL/service status and all documentation paths; report downtime honestly if it persists.

### Task 3: Compile and visual verification

**Files:** Generate `slides/main_uit.pdf` and build artifacts; update `slides/Makefile` only if required for a portable local build.

**Produces:** A compiled deck with chapter 4 visually checked and no unexplained layout warnings.

- [ ] Establish XeTeX-compatible and PDF-rendering tools only inside gitignored project-local directories; do not install system packages or regenerate unrelated figures.
- [ ] Compile `main_uit.tex` twice, or use an equivalent XeTeX-compatible build that resolves frame counts and references. Expect exit status 0 and a newly generated `main_uit.pdf`.
- [ ] Inspect the log for errors and overfull/underfull boxes; inspect text ordering and rendered images for every chapter 4 main and appendix page. Fix clipping, crowding or tiny content and rerun until clean.
- [ ] Reconcile all displayed experimental values with their source reports and verify that appendix frames follow the demo/conclusion without changing the main story.
- [ ] Run `git diff --check` and inspect `git status`/`git diff --stat`; summarize modified files, verification evidence and any remaining demo-service limitation. Do not commit.
