# GEPA example gallery — Design

Date: 2026-11-24
Status: approved in conversation (user selected guided gallery, direction 1)

## Intent

Make AdaptLab's **Prompt optimization** view immediately show what GEPA changed and provide concrete, real test cases where the optimized instruction corrected an answer that the matching starting-prompt baseline got wrong. The current view hides successful histories behind dataset selection and has no before/after output examples.

## Goals

- Open on a successful optimization example rather than defaulting to unchanged GSM8K.
- Provide a guided gallery for the four genuinely changed canonical prompt pairs: GEPA/ARC-C and T2L×GEPA/ARC-C, BoolQ, HellaSwag.
- Explain the meaningful instruction changes concisely, with full seed and optimized instructions available.
- Show multiple real held-out test examples per successful pair where the starting-prompt baseline was wrong and the optimized arm was right.
- Pair like with like: `icl3` vs `gepa_3shot`, and `t2l_icl` vs `t2l_gepa_opt`; same task, model weights, demos and test item, with only the searched instruction differing.
- Preserve the existing full candidate/score explorer and unchanged-prompt handling.
- Use stored canonical artifacts only; no model calls, fabricated prompts, illustrative outputs, image-led walkthrough or long meta-prompts.

## Non-goals and anti-goals

- Do not imply cherry-picked corrected cases establish an aggregate or statistically significant improvement.
- Do not show cases from runs where best equals seed as evidence of prompt optimization.
- Do not compare GEPA with `base` or T2L×GEPA with `gepa_3shot`; those change more than the instruction.
- Do not rerun optimization or inference to generate gallery content.
- Do not add a frontend framework, build step, external assets or a large prompt to the model/runtime path.

## Approach

**Chosen: examples-first guided gallery.** Successful-pair cards select a story. A concise change summary and seed/optimized prompt comparison explain the optimization; case cards select concrete wrong-to-right examples with question, gold and both stored outputs. The raw candidate history remains available as a secondary explorer.

**Alternative considered:** keep the existing workbench layout, auto-select a changed dataset and append a case list. This is smaller but still makes visitors infer the optimization lessons from long prompt diffs, so it does not meet the storytelling goal as well.

## Implementation

- Extend read-only library code to expose changed prompt pairs and recorded wrong-to-right cases from canonical per-item JSONL records.
- Add an API response suitable for the gallery, including stable pair/example IDs and the baseline arm used for each comparison.
- Rebuild the Prompt optimization view around pair selection, a change summary, compact prompt comparison and output case comparison; retain raw history in a collapsible/secondary explorer.
- Derive change summaries from reviewed stored prompts and keep them in backend/static gallery metadata rather than invoking an LLM.
- If an expected artifact is missing, omit only that story/case and keep other stories usable. Preserve explicit unchanged behavior in the raw explorer.
- Clearly label corrected cases as selected examples, not aggregate evidence, and link/show the canonical per-arm metrics separately.
- Keep the interface text-only, responsive, copyable and keyboard accessible.

## Verification

- Unit-test successful pair discovery, correct baseline pairing, wrong-to-right filtering and missing/malformed artifact handling.
- Test API gallery responses and ensure unchanged histories never produce optimization stories.
- Browser-test gallery selection, several corrected examples, full prompt/candidate access, honest labeling and mobile layout using stored deterministic fixtures.
- Run existing prompt-library, web app and end-to-end tests to catch regressions.
