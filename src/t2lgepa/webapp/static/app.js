const state = { task: null, meta: null, item: null, busy: false };

const ARM_META = {
  base:     { label: "Base",        tag: "base", hint: "zero-shot, no adapter" },
  t2l_icl:  { label: "T2L + ICL",   tag: "t2l",  hint: "LoRA from task description + 3 demos" },
  gepa:     { label: "GEPA + ICL",  tag: "gepa", hint: "evolved instruction + 3 demos" },
};

const $ = (id) => document.getElementById(id);

function el(tag, props = {}, ...children) {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(props)) {
    if (k === "class") node.className = v;
    else if (k === "html") node.innerHTML = v;
    else if (k.startsWith("on")) node.addEventListener(k.slice(2), v);
    else if (v !== null && v !== undefined) node.setAttribute(k, v);
  }
  for (const child of children) {
    if (child !== null && child !== undefined) {
      node.append(child.nodeType ? child : document.createTextNode(String(child)));
    }
  }
  return node;
}

async function api(path, options) {
  const res = await fetch(path, options);
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(`${res.status}: ${detail}`);
  }
  return res.json();
}

function setStatus(text, kind) {
  $("status-text").textContent = text;
  const dot = document.querySelector("#status .dot");
  dot.className = "dot" + (kind ? " " + kind : "");
}

function renderTabs() {
  const nav = $("task-tabs");
  nav.replaceChildren();
  for (const task of state.meta.tasks) {
    const hasGepa = state.meta.gepa[task];
    const tab = el("button", {
      class: "tab" + (task === state.task ? " active" : ""),
      onclick: () => selectTask(task),
      title: hasGepa ? "GEPA prompt available" : "no GEPA prompt for this task",
    }, task.replace(/_/g, " "));
    nav.append(tab);
  }
}

function selectTask(task) {
  state.task = task;
  state.item = null;
  renderTabs();
  $("question").value = "";
  $("options").value = "";
  $("passage").value = "";
  $("gold").hidden = true;
  $("item-meta").textContent = "No item selected";
  $("options-field").hidden = !["arc_challenge", "hellaswag", "winogrande"].includes(task);
  $("passage-field").hidden = task !== "boolq";
  renderPlaceholders();
}

function renderPlaceholders() {
  $("cards").replaceChildren(
    ...Object.entries(ARM_META).map(([arm, meta]) => {
      if (arm === "gepa" && state.meta && !state.meta.gepa[state.task]) {
        return el("article", { class: "card placeholder" },
          el("h3", {}, meta.label),
          el("p", {}, "No GEPA prompt was produced for this task — GEPA could not beat its seed program on the validation set, so this surface is not shown."));
      }
      return el("article", { class: "card placeholder" },
        el("h3", {}, meta.label), el("p", {}, meta.hint));
    })
  );
}

async function sampleItem() {
  if (state.busy) return;
  state.busy = true;
  $("sample-btn").disabled = true;
  try {
    const item = await api(`/api/sample?task=${encodeURIComponent(state.task)}`);
    state.item = item;
    $("question").value = item.question;
    if (item.passage) $("passage").value = item.passage;
    if (item.options.length) $("options").value = item.options.join("\n");
    $("gold").hidden = false;
    $("gold").textContent = `gold: ${item.gold}`;
    $("item-meta").textContent = item.id;
    renderPlaceholders();
  } catch (err) {
    $("item-meta").textContent = "";
    $("item-meta").append(el("span", { class: "error" }, String(err.message)));
  } finally {
    state.busy = false;
    $("sample-btn").disabled = false;
  }
}

function card(run) {
  const meta = ARM_META[run.arm] || { label: run.arm, tag: "", hint: "" };
  const badge = run.correct === null
    ? el("span", { class: "badge na" }, "unscored")
    : el("span", { class: "badge " + (run.correct ? "ok" : "no") }, run.correct ? "correct" : "wrong");

  const body = el("div", { class: "answer" },
    run.text.trim() ? run.text.trim() : el("span", { class: "muted" }, "(empty)"));
  if (run.pred === null) {
    body.append(el("div", { class: "muted", style: "margin-top:8px;font-size:11px" },
      "no answer extractable — format did not match"));
  }

  return el("article", { class: "card" },
    el("header", {},
      el("h3", {}, meta.label, " ", el("span", { class: "tag " + meta.tag }, run.arm)),
      badge),
    body,
    el("div", { class: "stats" },
      el("span", {}, "latency ", el("b", {}, run.latency_ms + " ms")),
      el("span", {}, "tokens ", el("b", {}, run.tokens)),
      el("span", {}, "pred ", el("b", {}, run.pred === null ? "—" : run.pred))),
    el("details", { class: "prompt" },
      el("summary", {}, "prompt sent"),
      el("pre", {}, run.prompt))
  );
}

async function compare() {
  if (state.busy) return;
  const question = $("question").value.trim();
  if (!question) return;
  state.busy = true;
  $("compare-btn").disabled = true;
  $("compare-btn").textContent = "Comparing…";
  const options = $("options").value.split("\n").map((s) => s.trim()).filter(Boolean);
  const passage = $("passage-field").hidden ? null : $("passage").value.trim() || null;
  try {
    const out = await api("/api/compare", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({
        task: state.task,
        question,
        options,
        passage,
        example_id: state.item && state.item.question === question ? state.item.id : null,
      }),
    });
    $("gold").hidden = out.gold === null;
    if (out.gold !== null) $("gold").textContent = `gold: ${out.gold}`;
    $("cards").replaceChildren(...out.arms.map(card));
  } catch (err) {
    $("cards").replaceChildren(el("article", { class: "card" },
      el("h3", {}, "Error"), el("p", { class: "error" }, String(err.message))));
  } finally {
    state.busy = false;
    $("compare-btn").disabled = false;
    $("compare-btn").replaceChildren("Compare ", el("kbd", {}, "⌘↵"));
  }
}

function markdownTable(md) {
  const lines = md.split("\n").filter((l) => l.trim().startsWith("|"));
  if (!lines.length) return el("p", { class: "muted" }, "no rows");
  const rows = lines.filter((l) => !/^\|[\s:|-]+\|$/.test(l.trim()));
  const table = el("table");
  rows.forEach((line, i) => {
    const cells = line.split("|").slice(1, -1).map((c) => c.trim());
    const tr = el("tr");
    for (const cell of cells) {
      tr.append(el(i === 0 ? "th" : "td", { html: cell.replace(/\*\*/g, "") }));
    }
    table.append(tr);
  });
  return table;
}

async function loadResults() {
  const box = $("results");
  box.replaceChildren(el("p", { class: "muted" }, "Loading…"));
  try {
    const data = await api("/api/results");
    box.replaceChildren(
      el("div", { class: "md-h" }, "Accuracy (test items, 95% CI, delta vs base)"),
      markdownTable(data.accuracy_md),
      el("div", { class: "md-h" }, "Cost"),
      markdownTable(data.cost_md)
    );
  } catch (err) {
    box.replaceChildren(el("p", { class: "error" }, String(err.message)));
  }
}

async function boot() {
  try {
    state.meta = await api("/api/meta");
    state.task = state.meta.tasks[0];
    $("footer-model").textContent = state.meta.model;
    setStatus("server ready · " + state.meta.model, "ok");
    renderTabs();
    selectTask(state.task);
    loadResults();
  } catch (err) {
    setStatus("model server unreachable", "bad");
    $("cards").replaceChildren(el("article", { class: "card" },
      el("h3", {}, "Backend not ready"),
      el("p", { class: "error" }, String(err.message))));
  }
}

$("sample-btn").addEventListener("click", sampleItem);
$("compare-btn").addEventListener("click", compare);
$("reload-results").addEventListener("click", loadResults);
document.addEventListener("keydown", (e) => {
  if ((e.metaKey || e.ctrlKey) && e.key === "Enter") { e.preventDefault(); compare(); }
});

boot();
