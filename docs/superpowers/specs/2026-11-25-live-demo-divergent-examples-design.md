# Live demo divergent examples — Design

Date: 2026-11-25
Status: approved in conversation (15 concise cases)

## Intent

Give demo users one copy-ready Markdown catalog of benchmark inputs whose stored results differ across Base, T2L+ICL, GEPA+ICL and T2L×GEPA. The file should make it easy to reproduce interesting comparisons in the existing Live demo without reading raw JSONL.

## Goals

- Create `docs/live-demo-divergent-examples.md` with 15 real cases: three from each of GSM8K, ARC-Challenge, BoolQ, HellaSwag and WinoGrande.
- Include the exact stored test ID, question, options or BoolQ passage, and gold answer needed by the Live demo input fields.
- Show each arm's stored prediction, correctness and a short output excerpt in a compact table.
- Prefer distinct correctness patterns and contrasting method behavior over near-duplicate cases.
- Clearly identify the four-arm correctness order and the source run; note that replaying an endpoint can vary slightly.

## Non-goals and anti-goals

- No fabricated questions, answers, scores or generations.
- No model/API calls and no Live demo code changes.
- No full-generation dumps, screenshots or implication that selected cases replace aggregate metrics.

## Approaches

**Chosen: 15 concise cases.** Three per dataset, with copy-ready inputs, compact result tables and short excerpts; best balance of variety and usability.

**Considered: five deep case studies.** One per dataset with all complete generations; more detail but fewer examples and a much longer file, so rejected for this request.

## Implementation and verification

Read canonical per-arm item records from `mistral-7b-v1`, join identical test IDs, and select diverse wrong/right patterns deterministically. Use the existing dataset loader solely to recover option text and BoolQ passages missing from result records. Format the reviewed selection as Markdown with deterministic escaping and bounded excerpts. Validate all 15 IDs against every arm's source records, all task counts, gold/prediction/correctness fields, copy-ready inputs and the absence of runtime changes. Keep the change uncommitted unless the user requests a PR update.
