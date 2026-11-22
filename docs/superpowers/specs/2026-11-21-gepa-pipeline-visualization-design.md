# GEPA Pipeline Visualization Design

## Intent

Create a beautiful, presentation-ready website that helps a technical or semi-technical audience understand the GEPA pipeline in the supplied reference map. The user approved a **guided animated walkthrough** and prioritized the final result over further design questions.

The canonical reference is **GEPA: Reflective Prompt Evolution Can Outperform Reinforcement Learning** (Agrawal et al., arXiv:2507.19457, ICLR 2026 Oral): https://arxiv.org/abs/2507.19457. The official implementation is https://github.com/gepa-ai/gepa; this repository also integrates the `gepa` package in its prompt and description-search experiments.

## Goals

- Explain the complete evolutionary loop, not just reflection: pool → per-instance scores → Pareto filtering → mutation or merge → minibatch gate → full selection-set evaluation → pool update → budget loop.
- Make the two proposers visually distinct and understandable.
- Show both acceptance and rejection at the minibatch gate while continuing the main story with an accepted child.
- Provide play/pause, previous/next, direct chapter navigation, clickable map components, speed control, restart, and keyboard operation.
- Make the experience polished enough for a conference screen and usable on a laptop or phone.
- Run locally by opening `index.html`; no web server, build, package installation, CDN, font download, or network access is required for the experience.
- Link to the paper, official code, documentation, and this repository's GEPA integration from a compact references drawer.
- Package all runtime assets in `artifacts/gepa-pipeline/` and also create a downloadable zip archive.

## Non-goals and anti-goals

- No live LLM calls, actual GEPA optimization, model downloads, or backend.
- No claim that the illustrated scores came from an experiment. The interface labels them as an illustrative simulation.
- No dense reproduction of the paper figure with tiny labels. Preserve its information architecture while redesigning for readability.
- No generic dashboard aesthetic, gratuitous 3D, stock imagery, or continuous motion that obscures the explanation.
- Do not reduce the candidate pool to only Pareto members; filtering controls parent selection.
- Do not describe merge as an LLM synthesizing prompt text. It is module-wise crossover relative to a common ancestor.
- Do not imply full evaluation is a second improvement gate or a held-out test evaluation.

## Approach and alternatives

**Chosen: guided animated walkthrough with exploratory interaction.** A persistent map gives spatial continuity while a chapter rail and explanation panel reveal one idea at a time. This is the best fit for an audience and still supports self-study.

Rejected alternatives:

1. Pure interactive explorer: good for self-study but weak as a hands-free presentation.
2. Scroll-based long-form story: attractive, but less convenient to control during a talk and easier to lose the whole-loop context.

## Visual direction

Editorial scientific storytelling: deep evergreen-black background, warm ivory typography, acid-lime for active flow, mint for accepted candidates, soft coral for rejection, and muted violet for reflection. Fine grid lines, thin connectors, numbered chapter markers, softly glowing nodes, and subtle grain provide depth without visual noise. Typography uses a bold condensed-feeling system sans for headlines, clean sans for body copy, and monospace for scores and labels.

The opening view contains:

```text
GEPA / GENETIC–PARETO                              PAPER ↗  CODE ↗

Reflect. Select. Evolve.          [current chapter / conceptual explanation]
A visual guide to prompt          ┌──────────────────────────────────────┐
evolution through feedback        │                                      │
and Pareto search.                │       persistent animated map        │
                                  │                                      │
[▶ Play the pipeline]             └──────────────────────────────────────┘

○ Initialize  ○ Score  ○ Select  ○ Propose  ○ Reflect  ○ Gate  ○ Evolve
```

After play begins, the hero compresses into a compact title and the explanation panel follows the active chapter. On presentation-width displays the map receives most of the area. On small displays the explanation stacks above a horizontally scrollable, scaled map.

## Storyboard

The site uses nine chapters, with a single persistent SVG/DOM map rather than disconnected slides:

0. **Overview — Reflect. Select. Evolve.** The complete loop is visible and a single packet traces its route.
1. **Initialize the pool.** Seed candidate P₀ contains module prompts. D_feedback supplies cheap reflective rollouts; D_pareto supplies per-instance selection scores. Model weights remain fixed.
2. **Measure every candidate.** A brief “after several accepted children” transition explains the representative multi-candidate pool. Animated task-instance dots fill a candidate-by-instance score matrix. “Task” is clarified as usually an individual validation instance, not necessarily a broad task category.
3. **Preserve complementary specialists.** Best-per-instance winners (including ties) are highlighted and candidates not best on any validation instance recede. Parent sampling favors candidates winning more instances. The pool and ancestry remain intact; this is the default per-instance frontier, not the complete conventionally nondominated set.
4. **Choose a proposal strategy.** Reflective mutation and optional system-aware merge separate visually; merge requires complementary compatible lineages and a common ancestor.
5. **Learn from traces.** A selected parent executes on a small D_feedback minibatch. Inputs, outputs, reasoning/tool traces, scores, and textual diagnostics flow into the reflection LM, which rewrites one selected module prompt. Merge shows non-LLM module-wise inheritance as a secondary animated detail.
6. **Test cheaply first.** A mutation child runs on the same small feedback minibatch and requires strict aggregate improvement over its parent. Merge is presented separately: a merged candidate uses a validation/D_pareto subsample and must be at least as good as both parents. The accepted route glows mint; a ghosted coral route demonstrates that a rejected proposal is discarded without full D_pareto evaluation. Neither decision requires global optimality.
7. **Evaluate and evolve.** The accepted child receives a full D_pareto score vector and joins the pool with ancestry. The Pareto selector updates and the packet returns to the budget loop.
8. **Return the strongest candidate.** The budget closes and the candidate with the highest average D_pareto score is selected. Final test performance remains separate.

## Implementation

- `index.html`: semantic shell, SVG map definitions, chapter navigation, accessible controls, and dialogs/drawers.
- `styles.css`: design tokens, responsive layout, map styling, transitions, keyframes, and reduced-motion rules.
- `data.js`: chapter copy, candidate/task scores, diagram labels, and source metadata; exposed as a classic-script global so `file://` works.
- `app.js`: deterministic state machine, scene renderer, playback scheduler, controls, keyboard shortcuts, component inspection, and pure helpers exported for Node tests when required.
- `assets/reference-map.png`: supplied map for the optional “Original figure” reference view.
- `README.md`: open/present instructions, controls, technical fidelity notes, and source links.
- No runtime third-party libraries. Animation uses CSS plus a single JavaScript playback clock.

## Accessibility and resilience

- Buttons are real buttons with focus states and accessible names; chapters expose selected state.
- Arrow keys navigate, Space toggles playback, R restarts, and F requests fullscreen where supported.
- The experience honors `prefers-reduced-motion`; reduced motion uses immediate state changes without traveling packets or pulses.
- Playback begins only after an explicit user action.
- Important labels remain in HTML or SVG text, with sufficient contrast and minimum readable sizes.
- A full static overview remains usable if animation is unsupported or paused.

## Verification

- Unit-test chapter bounds, playback wrapping/stopping, score helpers, and reduced-motion behavior where practical.
- Browser-test direct `file://` loading with network disabled, all controls, keyboard input, fullscreen-safe behavior, dialogs, and absence of console errors.
- Capture and visually inspect desktop and mobile screenshots for every chapter, correcting clipped labels and connector misalignment.
- Test at 1440×900, 1920×1080, 1280×720, and 390×844.
- Verify the folder and zip contain only portable runtime/reference files and no test dependencies.

## Builder freedom

Exact easing, particle count, microcopy lengths, and small responsive adjustments may be tuned after screenshots. The information architecture, technical distinctions, offline requirement, and visual palette above are fixed unless inspection reveals a usability problem.
