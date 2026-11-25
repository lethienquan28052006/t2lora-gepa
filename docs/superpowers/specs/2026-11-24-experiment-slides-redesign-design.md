# Experiment slides redesign

Date: 2026-11-24. Approved direction: revise chapter 4 on `feat/slides` for a 30-minute slot including the AdaptLab demo.

## Intent

Make the experimental chapter evidence-led rather than repetitive. The speaker should have concrete measurements and examples to discuss for about 20–22 minutes, followed by an 8–10 minute demo, without slides that merely repeat what the speaker can say naturally.

## Goals

- Keep roughly 11 main content frames plus a section divider and a visual demo frame.
- Merge the two general setup frames and remove the standalone motivation frame.
- Replace repeated six-arm reporting with focused analyses: paper replication, WinoGrande format failure, T2L significance, GEPA versus ICL3, cost, co-optimisation and run-to-run variance.
- Use canonical `mistral-7b-v1` values for headline results. Clearly label run A when using extraction, composition-transfer or description-search analyses that only exist there.
- Preserve the full six-arm table and detailed GEPA protocol in appendix frames for Q&A.
- Use assertive, natural slide titles and fewer generic takeaway boxes.
- End with three headline numbers: T2L `+4.8 pp`, added combination gain `+0.1 pp`, and searched-arm run variation `1.3–1.5 pp`; supporting context may remain secondary.

## Non-goals

- Do not run new experiments or manufacture missing outputs, confidence intervals, screenshots or measurements.
- Do not change the shared deck theme or chapters 1–3.
- Do not turn the demo slide into a static feature list or simulate an unavailable live service.
- Do not commit or push changes without a separate explicit request.

## Decisions and evidence

- Main sequence: setup; paper comparison; WinoGrande case; significant T2L effects; GEPA versus its fair ICL3 baseline; measured cost; three composition strategies; co-optimisation pipeline/protocol; paired combination result; run stability; numeric conclusion; demo.
- WinoGrande run A: accuracy `27.9 -> 64.6`, unextractable answers `59.6% -> 8.8%`, with the stored output-style example `" Sarah."` versus `The answer is (A).`.
- T2L+ICL3 versus base, canonical paired 95% CI: BoolQ `+3.3 [+1.6,+5.1]`; HellaSwag `+16.0 [+12.7,+19.4]`; WinoGrande `+4.8 [+1.5,+8.1]`; GSM8K and ARC-C contain zero.
- GEPA versus ICL3, canonical deltas: GSM8K `-0.4`; ARC-C `-1.5`; BoolQ `0.0`; HellaSwag `+0.3`; WinoGrande `-0.1`; mean about `-0.4` pp. Seed unchanged on 4/5 tasks for `gepa_3shot`, 2/5 for `t2l_gepa_opt` according to `prompts.md`.
- Final-test tokens: `204155` for T2L+ICL3 versus `535948` for ICL3. Search+test wall: `1476 s` for T2L+GEPA versus `2357 s` for GEPA; search calls `6444` versus `6318`.
- Run A composition transfer: GSM8K `-4.2 [-7.2,-1.2]`; WinoGrande `-6.0 [-8.9,-3.2]`; mean gain versus base falls from `+5.4` to `+3.5`; WinoGrande unextractable rate `8.8% -> 12.4%`.
- Description search run A: WinoGrande 10 candidates, `63.2` versus `64.6`; GSM8K one candidate, `48.0` versus `49.7`. The 120-item selection set has roughly `±4 pp` sampling noise; separately, regenerating the same adapter through the dynamic-LoRA pipeline has an approximately `1.4 pp` floor.
- Prompt growth in the canonical co-optimised arm: ARC-C `130 -> 2332` characters, BoolQ `60 -> 2963`, HellaSwag `130 -> 1768`.
- Qualify scientific claims: replication is partial; “wins 4/5” is a point-estimate statement; co-optimisation is more sensible than prompt transfer but its added benefit is unproven.

## Verification

Compile `main_uit.tex` with an isolated local XeTeX-compatible toolchain without changing system packages. Inspect chapter 4 page images for clipping, overflow and readability, inspect the log for overfull boxes, and reconcile every displayed value against the reports. Update `slides/README.md` to describe the new chapter structure. Produce `overleaf_uit.zip` only if the normal build path supports it.
