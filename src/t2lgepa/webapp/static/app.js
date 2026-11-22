const state = {
  task: null, meta: null, item: null, view: "playground", searchArm: "gepa_3shot",
  library: null, selectedIndex: null, busy: false, runId: 0, libraryRunId: 0,
  evalRows: null, evalMetric: "accuracy",
};

const ARM_META = {
  base: { label: "Base", hint: "Zero-shot · no adaptation", tag: "v0" },
  t2l_icl: { label: "T2L + ICL", hint: "Frozen task LoRA · fixed 3-shot", tag: "v1" },
  gepa_3shot: { label: "GEPA + ICL", hint: "Searched instruction · base model", tag: "v2" },
  t2l_gepa_opt: { label: "T2L × GEPA", hint: "Prompt searched with adapter in the loop", tag: "v3" },
};
const TASK_LABELS = { gsm8k: "GSM8K", arc_challenge: "ARC-C", boolq: "BoolQ", hellaswag: "HellaSwag", winogrande: "WinoGrande" };
const $ = (id) => document.getElementById(id);

function el(tag, props = {}, ...children) {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(props)) {
    if (key === "class") node.className = value;
    else if (key.startsWith("on")) node.addEventListener(key.slice(2), value);
    else if (value !== null && value !== undefined) node.setAttribute(key, value);
  }
  for (const child of children) {
    if (child !== null && child !== undefined) node.append(child.nodeType ? child : document.createTextNode(String(child)));
  }
  return node;
}

async function api(path, options) {
  const response = await fetch(path, options);
  if (!response.ok) {
    let detail = await response.text();
    try { detail = JSON.parse(detail).detail || detail; } catch (_) { /* plain error */ }
    throw new Error(detail);
  }
  return response.json();
}

function setStatus(text, kind) {
  $("status-text").textContent = text;
  $("status").className = "endpoint" + (kind ? ` ${kind}` : "");
}

function switchView(view) {
  state.view = view;
  for (const tab of document.querySelectorAll(".view-tab")) {
    tab.classList.toggle("active", tab.dataset.view === view);
    tab.setAttribute("aria-pressed", tab.dataset.view === view ? "true" : "false");
  }
  $("playground-view").hidden = view !== "playground";
  $("prompt-view").hidden = view !== "prompt";
  if (view === "prompt") loadLibrary();
}

function renderTasks() {
  $("task-tabs").replaceChildren(...state.meta.tasks.map((task) => el("button", {
    class: "task-tab" + (task === state.task ? " active" : ""),
    onclick: () => selectTask(task),
    "aria-pressed": task === state.task ? "true" : "false",
  }, TASK_LABELS[task] || task)));
}

function selectTask(task) {
  state.task = task;
  state.item = null;
  $("question").value = "";
  $("options").value = "";
  $("passage").value = "";
  $("gold").hidden = true;
  $("item-meta").textContent = "Choose a test item or write your own input.";
  $("options-field").hidden = !["arc_challenge", "hellaswag", "winogrande"].includes(task);
  $("passage-field").hidden = task !== "boolq";
  renderTasks();
  renderPlaceholders();
  if (state.view === "prompt") loadLibrary();
}

function renderPlaceholders() {
  $("cards").replaceChildren(...Object.entries(ARM_META).map(([arm, meta]) => el("article", { class: `response-card ${arm}` },
    el("div", { class: "response-top" }, el("div", {},
      el("span", { class: `method-badge ${arm}` }, `${meta.tag} · ${arm}`),
      el("h3", {}, meta.label))),
    el("p", { class: "placeholder" }, meta.hint),
    el("div", { class: "card-stats" }, el("span", {}, "waiting for input")))));
}

async function sampleItem() {
  if (state.busy) return;
  state.busy = true;
  $("sample-btn").disabled = true;
  $("item-meta").textContent = "Sampling a real test item…";
  try {
    const item = await api(`/api/sample?task=${encodeURIComponent(state.task)}`);
    state.item = item;
    $("question").value = item.question;
    $("passage").value = item.passage || "";
    $("options").value = (item.options || []).join("\n");
    $("gold").hidden = false;
    $("gold").textContent = `gold: ${item.gold}`;
    $("item-meta").textContent = item.id;
  } catch (error) {
    $("item-meta").replaceChildren(el("span", { class: "error" }, error.message));
  } finally {
    state.busy = false;
    $("sample-btn").disabled = false;
  }
}

function responseCard(run) {
  const meta = ARM_META[run.arm];
  const verdict = run.correct === null
    ? el("span", { class: "verdict" }, "UNSCORED")
    : el("span", { class: `verdict ${run.correct ? "correct" : "wrong"}` }, run.correct ? "✓ CORRECT" : "✕ WRONG");
  const output = run.text.trim();
  const body = el("div", { class: "response-text" + (output ? "" : " empty") }, output || "(empty generation)");
  if (run.pred === null) body.append(el("p", { class: "muted" }, "No answer in the expected format."));
  return el("article", { class: `response-card ${run.arm}`, "data-arm": run.arm },
    el("div", { class: "response-top" },
      el("div", {}, el("span", { class: `method-badge ${run.arm}` }, `${meta.tag} · ${run.arm}`), el("h3", {}, meta.label)),
      el("span", { class: "latency", title: run.model }, `${run.latency_ms} ms`)),
    body,
    el("div", { class: "card-stats" }, verdict,
      el("span", {}, "pred ", el("b", {}, run.pred ?? "—")),
      el("span", {}, "tokens ", el("b", {}, run.tokens)),
      el("button", { class: "prompt-link", onclick: () => showPrompt(run) }, "view prompt ↗")));
}

function showPrompt(run) {
  $("dialog-title").textContent = `${ARM_META[run.arm].label} · ${run.model}`;
  $("dialog-prompt").textContent = run.prompt;
  $("prompt-dialog").showModal();
}

async function compare() {
  if (state.busy) return;
  const question = $("question").value.trim();
  if (!question) {
    $("item-meta").textContent = "Write a question or choose Random test item first.";
    $("question").focus();
    return;
  }
  state.busy = true;
  const thisRun = ++state.runId;
  $("compare-btn").disabled = true;
  $("sample-btn").disabled = true;
  $("compare-btn").textContent = "Running all 4…";
  $("cards").replaceChildren(...Object.entries(ARM_META).map(([arm, meta]) => el("article", { class: `response-card ${arm}` },
    el("div", { class: "response-top" }, el("span", { class: `method-badge ${arm}` }, meta.tag)),
    el("p", { class: "placeholder" }, `Calling ${meta.label}…`))));
  const options = $("options").value.split("\n").map((s) => s.trim()).filter(Boolean);
  const passage = $("passage-field").hidden ? null : $("passage").value.trim() || null;
  try {
    const out = await api("/api/compare", {
      method: "POST", headers: { "content-type": "application/json" },
      body: JSON.stringify({
        task: state.task, question, options, passage,
        example_id: state.item && state.item.question === question ? state.item.id : null,
      }),
    });
    if (thisRun !== state.runId) return;
    $("gold").hidden = out.gold === null;
    if (out.gold !== null) $("gold").textContent = `gold: ${out.gold}`;
    $("cards").replaceChildren(...out.arms.map(responseCard));
    if (out.skipped_arms?.length) $("cards").append(el("article", { class: "notice" },
      `Not run: ${out.skipped_arms.join(", ")} — no stored best prompt for this version.`));
  } catch (error) {
    if (thisRun === state.runId) $("cards").replaceChildren(el("article", { class: "response-card error-card" },
      el("h3", {}, "Comparison failed"), el("p", { class: "error" }, error.message),
      el("p", { class: "muted" }, "Check that the model endpoint is online, then try again.")));
  } finally {
    state.busy = false;
    $("compare-btn").disabled = false;
    $("sample-btn").disabled = false;
    $("compare-btn").replaceChildren("Run all 4 ", el("span", {}, "→"));
  }
}

async function loadLibrary() {
  const requestId = ++state.libraryRunId;
  const requestedTask = state.task;
  const requestedArm = state.searchArm;
  $("library-status").hidden = false;
  $("library-status").className = "notice";
  $("library-status").textContent = `Loading stored ${state.searchArm} history for ${TASK_LABELS[state.task]}…`;
  try {
    const history = await api(`/api/prompt-library?task=${encodeURIComponent(requestedTask)}&arm=${encodeURIComponent(requestedArm)}`);
    if (state.view !== "prompt" || requestId !== state.libraryRunId
        || state.task !== requestedTask || state.searchArm !== requestedArm) return;
    state.library = history;
    state.selectedIndex = history.best_index ?? history.candidates[0]?.index ?? 0;
    $("library-status").hidden = true;
    renderLibrary();
  } catch (error) {
    if (requestId !== state.libraryRunId) return;
    state.library = null;
    $("candidate-list").replaceChildren();
    $("seed-prompt").textContent = "";
    $("selected-prompt").textContent = "";
    $("candidate-count").textContent = "";
    $("score-curve").replaceChildren();
    $("rendered-example").textContent = "";
    $("selected-label").textContent = "";
    $("selected-title").textContent = "Prompt history unavailable";
    $("unchanged-note").hidden = true;
    $("library-status").hidden = false;
    $("library-status").className = "notice error";
    $("library-status").textContent = error.message;
  }
}

function scoreText(value) {
  return value === null || value === undefined ? "—" : Number(value).toFixed(3);
}

function renderHighlightedPrompt(container, seed, text) {
  container.replaceChildren();
  const seedLines = new Set(seed.split("\n").map((line) => line.trim()).filter(Boolean));
  for (const [index, line] of text.split("\n").entries()) {
    if (line.trim() && !seedLines.has(line.trim())) container.append(el("span", { class: "added" }, line));
    else container.append(document.createTextNode(line));
    if (index < text.split("\n").length - 1) container.append(document.createTextNode("\n"));
  }
}

function renderLibrary() {
  const history = state.library;
  if (!history) return;
  const selected = history.candidates.find((c) => c.index === state.selectedIndex)
    || { index: 0, instruction: history.seed, val_aggregate_score: null, is_seed: true };
  state.selectedIndex = selected.index;
  $("candidate-count").textContent = `${history.candidates.length} stored`;
  $("candidate-list").replaceChildren(...history.candidates.map((candidate) => {
    const isBest = candidate.index === history.best_index;
    return el("button", {
      class: "candidate" + (candidate.index === selected.index ? " active" : ""),
      onclick: () => { state.selectedIndex = candidate.index; renderLibrary(); },
      "data-candidate": candidate.index,
    },
      el("div", { class: "candidate-top" },
        el("b", {}, candidate.is_seed ? "SEED" : `CANDIDATE ${String(candidate.index).padStart(2, "0")}`),
        el("span", { class: isBest ? "best-label" : "" }, isBest ? "BEST" : scoreText(candidate.val_aggregate_score))),
      el("div", { class: "candidate-snippet" }, candidate.instruction.slice(0, 160)));
  }));

  $("seed-prompt").textContent = history.seed;
  $("selected-label").textContent = selected.is_seed ? "Starting point / unchanged search" : `Candidate ${selected.index} · D_pareto ${scoreText(selected.val_aggregate_score)}`;
  $("selected-title").textContent = selected.index === history.best_index ? "Best instruction" : `Candidate ${selected.index}`;
  renderHighlightedPrompt($("selected-prompt"), history.seed, selected.instruction);
  $("unchanged-note").hidden = !history.unchanged || !selected.is_seed;
  $("rendered-example").textContent = history.rendered_example || "No rendered example was stored for this run.";

  const scores = history.curve.map((point) => point.pareto_score);
  const min = scores.length ? Math.min(...scores) : 0;
  const max = scores.length ? Math.max(...scores) : 1;
  $("score-curve").setAttribute("aria-label", history.curve.map((point) =>
    `${point.metric_calls} calls: ${scoreText(point.pareto_score)}`).join("; "));
  $("score-curve").replaceChildren(...history.curve.map((point) => el("span", {
    class: "curve-bar" + (point.pareto_score === max ? " best" : ""),
    style: `height:${Math.max(8, 8 + 45 * (point.pareto_score - min) / Math.max(0.01, max - min))}px`,
    title: `${point.metric_calls} metric calls · Pareto ${point.pareto_score}`,
  })));
}

async function copyPrompt(kind) {
  if (!state.library) return;
  const candidate = state.library.candidates.find((c) => c.index === state.selectedIndex);
  const text = kind === "seed" ? state.library.seed : (candidate?.instruction || state.library.best);
  const button = document.querySelector(`[data-copy="${kind}"]`);
  try {
    await navigator.clipboard.writeText(text);
    button.textContent = "Copied ✓";
  } catch (_) {
    const range = document.createRange();
    range.selectNodeContents(kind === "seed" ? $("seed-prompt") : $("selected-prompt"));
    const selection = window.getSelection();
    selection.removeAllRanges(); selection.addRange(range);
    button.textContent = "Selected · press Ctrl/Cmd+C";
  }
  setTimeout(() => { button.textContent = "Copy"; }, 2200);
}

function markdownTable(md) {
  const lines = md.split("\n").filter((line) => line.trim().startsWith("|"));
  if (!lines.length) return el("p", { class: "muted" }, "No rows available.");
  const table = el("table");
  lines.filter((line) => !/^\|[\s:|-]+\|$/.test(line.trim())).forEach((line, index) => {
    const tr = el("tr");
    for (const cell of line.split("|").slice(1, -1).map((c) => c.trim())) tr.append(el(index === 0 ? "th" : "td", {}, cell.replace(/\*\*/g, "")));
    table.append(tr);
  });
  return table;
}

function metricRows(md) {
  return md.split("\n").filter((line) => /^\|\s*(t2l|gepa|base|icl3)/.test(line.trim())).map((line) =>
    line.split("|").slice(1, -1).map((cell) => cell.trim().replace(/\*\*/g, "")));
}

function buildEvaluation(data) {
  const rows = {};
  for (const [arm, task, , score, ci, delta] of metricRows(data.accuracy_md)) {
    if (!ARM_META[arm]) continue;
    const parsedDelta = delta === "-" ? (arm === "base" ? 0 : Number.NaN) : Number.parseFloat(delta);
    rows[task] ||= {};
    rows[task][arm] = { score: Number.parseFloat(score), scoreText: score, ci, delta: parsedDelta,
      deltaText: Number.isFinite(parsedDelta) ? (arm === "base" ? "0.0" : delta.replace("pp", "")) : "—" };
  }
  const tasks = Object.keys(rows).filter((task) => Object.keys(ARM_META).every((arm) =>
    rows[task][arm] && Number.isFinite(rows[task][arm].score) && Number.isFinite(rows[task][arm].delta)));
  state.evalRows = Object.fromEntries(tasks.map((task) => [task, rows[task]]));
  if (!tasks.length) {
    $("summary-cards").replaceChildren(el("p", { class: "muted" }, "No complete task results are available."));
  } else {
    const baseMean = tasks.reduce((sum, task) => sum + rows[task].base.score, 0) / tasks.length;
    $("summary-cards").replaceChildren(...Object.entries(ARM_META).map(([arm, meta], index) => {
      const mean = tasks.reduce((sum, task) => sum + rows[task][arm].score, 0) / tasks.length;
      const delta = mean - baseMean;
      return el("article", { class: `summary-card ${arm}`, "data-arm": arm },
        el("div", { class: "summary-method" }, el("span", {}, meta.label), el("span", { class: "summary-version" }, `v${index}`)),
        el("div", { class: "summary-score", "data-value": mean.toFixed(1) },
          el("span", { class: "summary-score-value" }, mean.toFixed(1)), el("small", {}, "%")),
        el("div", { class: `summary-delta ${delta > 0 ? "positive" : delta < 0 ? "negative" : ""}` },
          arm === "base" ? "reference" : `${delta >= 0 ? "+" : ""}${delta.toFixed(1)} pp vs base`),
        el("div", { class: "summary-caption" }, meta.hint));
    }));
  }
  buildCostSummary(data.cost_md);
  $("evaluation-note").textContent = data.caveat_md;
  renderEvalChart();
}

function compactNumber(value) {
  if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(1)}M`;
  if (value >= 1_000) return `${(value / 1_000).toFixed(1)}k`;
  return String(value);
}

function buildCostSummary(md) {
  const byArm = Object.fromEntries(Object.keys(ARM_META).map((arm) => [arm, new Map()]));
  for (const [arm, task, seconds, tokens] of metricRows(md)) {
    if (!byArm[arm] || !Number.isFinite(Number(seconds)) || !Number.isFinite(Number(tokens))) continue;
    byArm[arm].set(task, { seconds: Number(seconds), tokens: Number(tokens) });
  }
  const taskLists = Object.values(byArm).map((rows) => [...rows.keys()].sort().join("\n"));
  const comparable = taskLists.every((list) => list && list === taskLists[0]);
  const taskCount = comparable ? byArm.base.size : 0;
  const totals = Object.fromEntries(Object.entries(byArm).map(([arm, rows]) => [arm,
    [...rows.values()].reduce((total, row) => ({ seconds: total.seconds + row.seconds, tokens: total.tokens + row.tokens }),
      { seconds: 0, tokens: 0 })]));
  const base = totals.base;
  $("cost-heading").textContent = comparable
    ? `The full ${taskCount}-task evaluation budget` : "Cost comparison unavailable";
  $("cost-summary").replaceChildren(...Object.entries(ARM_META).map(([arm, meta]) => {
    const total = totals[arm];
    const available = comparable && taskCount > 0;
    const timeChange = available ? (total.seconds / base.seconds - 1) * 100 : 0;
    return el("article", { class: `cost-card ${arm}`, "data-arm": arm },
      el("div", { class: "cost-method" }, meta.label),
      el("div", { class: "cost-time" }, available ? total.seconds.toFixed(1) : "—", available ? el("small", {}, " s") : null),
      el("div", { class: "cost-tokens" }, available ? `${compactNumber(total.tokens)} tokens` : "cost not available"),
      el("div", { class: `cost-change${available && timeChange <= 0 ? " positive" : ""}` },
        !available ? "incomplete cost data" : arm === "base" ? "reference" : `${timeChange <= 0 ? "−" : "+"}${Math.abs(timeChange).toFixed(0)}% time vs base`),
      el("div", { class: "cost-footnote" }, available ? `${taskCount} tasks · generated output` : "no common five-task total"));
  }));
}

function renderEvalChart() {
  if (!state.evalRows) return;
  const mode = state.evalMetric;
  const tasks = Object.keys(state.evalRows);
  const allDeltas = tasks.flatMap((task) => Object.keys(ARM_META).map((arm) => state.evalRows[task][arm].delta));
  const lo = Math.min(0, ...allDeltas), hi = Math.max(0, ...allDeltas);
  const range = hi - lo || 1, zero = (-lo / range) * 100;
  $("eval-chart").dataset.mode = mode;
  $("chart-description").textContent = mode === "accuracy"
    ? "Accuracy by task · higher is better" : "Percentage-point difference vs base · zero line = no gain";
  $("eval-chart").replaceChildren(...tasks.map((task) => {
    const rows = state.evalRows[task];
    const bestArm = Object.keys(ARM_META).reduce((best, arm) => rows[arm].score > rows[best].score ? arm : best, "base");
    const chartRows = Object.entries(ARM_META).map(([arm, meta]) => {
      const row = rows[arm];
      const winner = arm === bestArm && arm !== "base" && rows[arm].score > rows.base.score;
      const value = mode === "accuracy" ? row.score : row.delta;
      const left = mode === "accuracy" ? 0 : value >= 0 ? zero : zero + (value / range) * 100;
      const width = mode === "accuracy" ? value : Math.abs(value / range) * 100;
      const score = mode === "accuracy" ? row.scoreText : row.deltaText;
      return el("div", { class: `metric-row ${arm}`, title: `${meta.label} · 95% CI ${row.ci}` },
        el("span", { class: "metric-arm" }, meta.label),
        el("div", { class: `metric-track ${mode === "delta" ? "delta-track" : ""}`, style: `--zero:${zero}%` },
          mode === "delta" ? el("i", { class: "delta-zero" }) : null,
          el("i", { class: "metric-fill", style: `left:${left}%;width:${width}%` })),
        el("span", { class: `metric-score${winner ? " winner" : ""}` }, `${score}${mode === "accuracy" ? "" : " pp"}${winner ? " ▲" : ""}`));
    });
    return el("article", { class: "task-chart", "data-task": task },
      el("div", { class: "task-title" }, el("h3", {}, TASK_LABELS[task] || task),
        el("span", { class: "task-best" }, `${ARM_META[bestArm].label} leads`)), ...chartRows);
  }));
}

async function loadResults() {
  $("results-error").hidden = true;
  try {
    const data = await api("/api/results");
    buildEvaluation(data);
    $("results").replaceChildren(
      el("div", { class: "result-section" }, "Accuracy · 95% CI · delta vs base"),
      markdownTable(data.accuracy_md),
      el("p", { class: "fine-print" }, data.caveat_md),
      el("div", { class: "result-section" }, "Endpoint cost"), markdownTable(data.cost_md.replace("GPU seconds", "endpoint wall (s)")));
  } catch (error) {
    state.evalRows = null;
    $("summary-cards").replaceChildren();
    $("eval-chart").replaceChildren();
    $("cost-summary").replaceChildren();
    $("evaluation-note").textContent = "";
    $("results-error").textContent = `Could not load canonical evaluation: ${error.message}`;
    $("results-error").hidden = false;
    $("results").replaceChildren(el("p", { class: "error" }, error.message));
  }
}

async function boot() {
  try {
    state.meta = await api("/api/meta");
    state.task = state.meta.tasks[0];
    $("footer-model").textContent = state.meta.model;
    await api("/api/health");
    setStatus("endpoint online · 6 models ready", "ok");
    renderTasks();
    selectTask(state.task);
    loadResults();
  } catch (error) {
    setStatus("backend unavailable", "bad");
    $("cards").replaceChildren(el("article", { class: "response-card error-card" },
      el("h3", {}, "Demo backend is not ready"), el("p", { class: "error" }, error.message)));
  }
}

document.querySelectorAll(".view-tab").forEach((tab) => tab.addEventListener("click", () => switchView(tab.dataset.view)));
document.querySelectorAll("[data-search-arm]").forEach((button) => button.addEventListener("click", () => {
  state.searchArm = button.dataset.searchArm;
  document.querySelectorAll("[data-search-arm]").forEach((b) => b.classList.toggle("active", b === button));
  loadLibrary();
}));
document.querySelectorAll("[data-eval-metric]").forEach((button) => button.addEventListener("click", () => {
  state.evalMetric = button.dataset.evalMetric;
  document.querySelectorAll("[data-eval-metric]").forEach((b) => b.classList.toggle("active", b === button));
  renderEvalChart();
}));
document.querySelectorAll("[data-copy]").forEach((button) => button.addEventListener("click", () => copyPrompt(button.dataset.copy)));
$("sample-btn").addEventListener("click", sampleItem);
for (const id of ["question", "passage", "options"]) {
  $(id).addEventListener("input", () => {
    state.item = null;
    $("gold").hidden = true;
    $("item-meta").textContent = "Custom input · unscored";
  });
}
$("compare-btn").addEventListener("click", compare);
$("dialog-close").addEventListener("click", () => $("prompt-dialog").close());
$("prompt-dialog").addEventListener("click", (event) => {
  if (event.target === $("prompt-dialog")) $("prompt-dialog").close();
});
document.addEventListener("keydown", (event) => {
  if ((event.metaKey || event.ctrlKey) && event.key === "Enter") { event.preventDefault(); compare(); }
});

boot();
