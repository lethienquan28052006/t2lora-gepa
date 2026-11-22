# GEPA Pipeline Visualization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a beautiful, animated, offline GEPA pipeline walkthrough in one portable folder and zip archive.

**Architecture:** A static HTML/CSS/classic-JavaScript application renders a persistent SVG map from fixed chapter data. A deterministic chapter state machine drives narration, camera framing, highlighting, and playback; CSS handles local motion while JavaScript handles navigation and autoplay. No runtime dependencies or server are used.

**Tech Stack:** Semantic HTML5, CSS3, SVG, vanilla JavaScript, Node built-in tests, Playwright for isolated browser verification.

**Spec:** `docs/superpowers/specs/2026-11-21-gepa-pipeline-visualization-design.md`

## Global Constraints

- Runtime folder is `artifacts/gepa-pipeline/`; direct `index.html` opening must work with network disabled.
- No runtime CDN, remote font, module import, package install, backend, or build step.
- Preserve per-instance Pareto selection, optional module-wise merge, cheap minibatch gating, full D_pareto evaluation after acceptance, and final highest-average selection.
- Label scores as an illustrative simulation, not measured results.
- Include the supplied figure only as an optional reference, not as the primary presentation.
- Honor reduced motion and provide keyboard/focus accessibility.
- Do not commit or otherwise mutate git history.

## Review Focus

- **File-URL execution:** classic scripts must initialize without CORS or fetch calls; browser test opens `file://` with offline mode.
- **Autoplay at first/last chapter:** play must start or restart predictably and stop at the final chapter; unit tests pin boundaries.
- **Viewport compression:** all labels and controls must remain reachable at 1280×720 and 390×844; responsive screenshots pin this.
- **Rapid navigation during animation:** stale timers and camera frames must not overwrite a newly selected chapter; browser tests exercise next/previous/play/restart quickly.
- **Reduced motion:** no traveling packets, pulses, or delayed autoplay scene animation; unit/browser tests inspect the rendered mode.

---

### Task 1: Portable story data and deterministic logic

**Files:**
- Create: `artifacts/gepa-pipeline/data.js`
- Create: `artifacts/gepa-pipeline/app.js`
- Test: `.superpowers/sdd/2026-11-21-gepa-pipeline-visualization/tests/logic.test.cjs`

**Interfaces:**
- Produces: browser global `GEPA_DATA` with `chapters`, `candidates`, `instances`, `references`.
- Produces: CommonJS test exports `normalizeStep`, `nextStep`, `previousStep`, `getBestPerInstance`, `getAverageScore`, `shouldStopPlayback`, `getSceneDuration` while initializing normally in a browser.

- [ ] **Step 1: Write failing tests for chapter boundaries, score helpers, final-chapter stopping, and reduced-motion duration.**

```js
assert.equal(normalizeStep(-2, 9), 0);
assert.equal(normalizeStep(20, 9), 8);
assert.equal(nextStep(8, 9), 8);
assert.equal(previousStep(0, 9), 0);
assert.deepEqual(getBestPerInstance([[0.4, 0.8], [0.4, 0.7]]), [0, 1]);
assert.equal(shouldStopPlayback(8, 9), true);
assert.equal(getSceneDuration(6000, 2, true), 0);
```

- [ ] **Step 2: Run the tests and confirm missing implementation failure.**

Run: `node --test .superpowers/sdd/2026-11-21-gepa-pipeline-visualization/tests/logic.test.cjs`
Expected: FAIL because the site logic does not exist.

- [ ] **Step 3: Implement chapter/candidate/reference data and pure state helpers.**

Use nine chapters matching the approved storyboard. Score rows are candidates, columns are instances; best-per-instance includes ties. Playback clamps at chapter 8 and reports completion there rather than wrapping unexpectedly. Browser entry initialization is guarded so requiring the file under Node does not require a DOM.

- [ ] **Step 4: Run logic tests and JavaScript syntax checks.**

Run: `node --test .superpowers/sdd/2026-11-21-gepa-pipeline-visualization/tests/logic.test.cjs && node --check artifacts/gepa-pipeline/data.js && node --check artifacts/gepa-pipeline/app.js`
Expected: all tests PASS; both syntax checks exit 0.

### Task 2: Editorial shell and persistent animated map

**Files:**
- Create: `artifacts/gepa-pipeline/index.html`
- Create: `artifacts/gepa-pipeline/styles.css`
- Modify: `artifacts/gepa-pipeline/app.js`
- Copy: supplied image to `artifacts/gepa-pipeline/assets/reference-map.png`
- Test: `.superpowers/sdd/2026-11-21-gepa-pipeline-visualization/tests/browser.test.cjs`

**Interfaces:**
- Consumes: `GEPA_DATA` and state helpers from Task 1.
- Produces: `#pipeline-map`, `#chapter-title`, `#chapter-description`, `#chapter-rail`, `#play-button`, `#previous-button`, `#next-button`, `#speed-control`, `#references-dialog`, `#inspect-panel`.

- [ ] **Step 1: Write a browser smoke test that serves no requests and opens the HTML through `file://`.**

Assert the document title, nine chapters, visible SVG map, nine matrix columns/rows as rendered, active chapter title, zero unexpected external requests, and zero page errors/consoles errors. Capture the overview at 1440×900.

- [ ] **Step 2: Run the browser test before implementation and confirm the page is absent.**

Run with Playwright installed only under `.superpowers/sdd/2026-11-21-gepa-pipeline-visualization/browser/`.
Expected: FAIL opening the not-yet-created local HTML file.

- [ ] **Step 3: Build the semantic shell and visual system.**

Implement the approved evergreen/ivory/lime palette, fine grid, editorial hero, compact source links, playback dock, chapter rail, explanation panel, simulation label, dialogs, focus states, and responsive layout. Use inline icons and system fonts only.

- [ ] **Step 4: Render the fixed map and chapter-specific states.**

Keep spatial positions stable: pool and matrix at left, Pareto selector below center, proposal branches at upper right, minibatch gate at lower right, evaluation/update below center, and budget loop across the top. Emphasize the current region, animate packets only along valid paths, and zoom the SVG camera for detailed chapters. Include clear textual feedback and module labels in reflection/merge scenes.

- [ ] **Step 5: Run smoke tests and inspect desktop screenshots.**

Expected: full map is immediately legible, no runtime errors or external requests, and no clipped active region. Adjust exact SVG positions and sizes based on the captured image.

### Task 3: Guided playback and exploration controls

**Files:**
- Modify: `artifacts/gepa-pipeline/app.js`
- Modify: `artifacts/gepa-pipeline/styles.css`
- Test: `.superpowers/sdd/2026-11-21-gepa-pipeline-visualization/tests/browser.test.cjs`

**Interfaces:**
- Consumes: DOM IDs from Task 2 and helpers from Task 1.
- Produces: `goToStep(index)`, `setPlaying(boolean)`, `restart()`, deterministic timer cleanup, keyboard controls, component inspection, and playback-speed updates.

- [ ] **Step 1: Add failing browser tests for next/previous, chapter clicks, play/pause, speed changes, restart, keyboard navigation, source/reference dialogs, and map inspection.**

Include rapid step changes and accelerated playback to expose stale timer behavior. Assert playback stops on the final chapter and Space does not scroll the page when the presentation owns the key.

- [ ] **Step 2: Run tests to verify the missing interactions fail.**

Expected: navigation/control assertions FAIL without changing the already passing static-map test.

- [ ] **Step 3: Implement the state machine and timer cancellation.**

Every transition increments a render token; delayed playback and camera animation capture this token and no-op when stale. Playing from the terminal chapter restarts at overview. Speed changes affect the current remaining chapter predictably. Direct chapter navigation pauses playback.

- [ ] **Step 4: Add reduced-motion and accessible component interaction.**

Reduced-motion users receive immediate camera/state updates and no traveling particles. Clickable SVG groups support Enter as well as pointer input, and dialogs return focus to their openers. Fullscreen failure is caught without breaking playback.

- [ ] **Step 5: Run all logic and browser tests.**

Expected: all interactions PASS with no page errors.

### Task 4: Visual polish, offline audit, documentation, and packaging

**Files:**
- Create: `artifacts/gepa-pipeline/README.md`
- Modify: `artifacts/gepa-pipeline/styles.css` as needed
- Create: `artifacts/gepa-pipeline.zip`
- Test: `.superpowers/sdd/2026-11-21-gepa-pipeline-visualization/tests/browser.test.cjs`

**Interfaces:**
- Consumes: complete runtime from Tasks 1–3.
- Produces: final portable directory, independently loadable zip contents, screenshots in `.superpowers/sdd/2026-11-21-gepa-pipeline-visualization/tests/screenshots/`.

- [ ] **Step 1: Add viewport and reduced-motion checks.**

Capture every chapter at 1440×900, representative chapters at 1920×1080 and 1280×720, and overview/detail/final chapters at 390×844. Assert horizontal document overflow is absent, controls remain in the viewport or reachable by normal vertical scrolling, and reduced-motion hides traveling packets.

- [ ] **Step 2: Run visual checks and inspect the captures using the image reader.**

Look specifically for overlapping SVG labels, tiny body text, weak contrast, unclear active paths, cut-off narrative, and mobile chapter-rail overflow. Refine the smallest CSS/SVG values needed.

- [ ] **Step 3: Write concise local-use and fidelity documentation.**

Document double-click opening, optional `python -m http.server`, Space/arrow/R/F controls, simulation status, and canonical paper/code/documentation URLs. Include the local repository GEPA integration paths identified during recon.

- [ ] **Step 4: Audit portability and package the site.**

Run with browser offline mode and abort every HTTP(S) request; verify no failed required asset. Check all runtime files are under the site folder and contain no test-only absolute paths. Zip only `index.html`, `styles.css`, `data.js`, `app.js`, `README.md`, and `assets/reference-map.png`.

- [ ] **Step 5: Run final verification and inspect archive contents.**

Run: logic tests, browser tests, `node --check`, and `unzip -t artifacts/gepa-pipeline.zip`.
Expected: all checks pass; archive contains exactly the portable runtime/reference files and opens offline after extraction to a fresh temporary folder.
