import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { pathToFileURL } from "node:url";

const root = process.cwd();
process.env.PLAYWRIGHT_BROWSERS_PATH ||= path.join(root, ".tools/ms-playwright");
const { chromium } = await import(pathToFileURL(path.join(root, ".tools/demo-e2e/node_modules/playwright/index.mjs")).href);
const baseUrl = process.env.DEMO_URL || "http://127.0.0.1:17860";
const out = path.join(root, "artifacts/demo-checks");
fs.mkdirSync(out, { recursive: true });

const browser = await chromium.launch({ headless: true, args: ["--no-sandbox"] });
const context = await browser.newContext({ viewport: { width: 1440, height: 1050 }, deviceScaleFactor: 1 });
const page = await context.newPage();
const errors = [];
const compareRequests = [];
let expectsResultsFailure = false;
page.on("pageerror", (error) => errors.push(error.message));
page.on("console", (message) => {
  if (message.type() !== "error") return;
  if (expectsResultsFailure && message.text().includes("500 (Internal Server Error)")) return;
  errors.push(message.text());
});
page.on("requestfailed", (request) => errors.push(`request failed: ${request.url()}`));
page.on("request", (request) => { if (request.url().endsWith("/api/compare")) compareRequests.push(request); });

const question = "Toulouse has twice as many sheep as Charleston. Charleston has 4 times as many sheep as Seattle. How many sheep do Toulouse, Charleston, and Seattle have together if Seattle has 20 sheep?";
await page.route("**/api/sample?*", (route) => route.fulfill({ json: {
  id: "gsm8k:test:6", task: "gsm8k", question, options: [], passage: null, gold: "260",
} }));

try {
  await page.goto(baseUrl, { waitUntil: "networkidle" });
  await page.waitForFunction(() => document.getElementById("status-text").textContent.includes("online"));
  await page.waitForSelector("#summary-cards .summary-card:nth-child(4)");
  assert.equal(await page.locator("#summary-cards .summary-card").count(), 4);
  assert.equal(await page.locator("#eval-chart .task-chart").count(), 5);
  assert.equal(await page.locator("#eval-chart .metric-row").count(), 20);
  assert.match(await page.locator('#summary-cards [data-arm="base"] .summary-score').innerText(), /62\.5/);
  assert.equal(await page.locator("#summary-cards").evaluate((node) => getComputedStyle(node).display), "grid",
    "summary cards must use the dashboard grid rather than rendering as an unstyled list");
  assert.equal(await page.locator("#cost-summary .cost-card").count(), 4);
  assert.match(await page.locator('#cost-summary [data-arm="base"]').innerText(), /797\.6\s*s/);
  assert.match(await page.locator('#cost-summary [data-arm="base"]').innerText(), /565\.5k\s*tokens/);
  assert.match(await page.locator('#cost-summary [data-arm="t2l_icl"]').innerText(), /427\.1\s*s/);
  assert.match(await page.locator('#cost-summary [data-arm="t2l_icl"]').innerText(), /204\.2k\s*tokens/);
  assert.match(await page.locator('#cost-summary [data-arm="gepa_3shot"]').innerText(), /757\.9\s*s/);
  assert.match(await page.locator('#cost-summary [data-arm="gepa_3shot"]').innerText(), /514\.4k\s*tokens/);
  assert.match(await page.locator('#cost-summary [data-arm="t2l_gepa_opt"]').innerText(), /466\.2\s*s/);
  assert.match(await page.locator('#cost-summary [data-arm="t2l_gepa_opt"]').innerText(), /221\.2k\s*tokens/);
  await page.locator('[data-eval-metric="delta"]').click();
  assert.equal(await page.locator("#eval-chart").getAttribute("data-mode"), "delta");
  assert.match((await page.locator('[data-task="arc_challenge"] .metric-row.t2l_gepa_opt .metric-score').innerText()).trim(), /^\+0\.1 pp/);
  const deltaTrack = page.locator('[data-task="arc_challenge"] .delta-track').first();
  assert.match(await deltaTrack.evaluate((node) => getComputedStyle(node).getPropertyValue("--zero")), /^32\.65/,
    "hidden icl3/t2l arms must not stretch the delta domain");
  assert.match(await deltaTrack.evaluate((node) => getComputedStyle(node).backgroundImage), /32\.65/,
    "the negative/positive background split must follow the computed zero point");
  await page.locator('[data-eval-metric="accuracy"]').click();
  assert.match((await page.locator('[data-task="arc_challenge"] .metric-row.t2l_gepa_opt .metric-score').innerText()).trim(), /^74\.3%/);
  assert.equal(await page.locator("#playground-view").isVisible(), true);
  assert.equal(await page.locator(".view-tab").count(), 2);
  await page.screenshot({ path: path.join(out, "01-playground.png"), fullPage: true });

  await page.click("#sample-btn");
  await page.waitForFunction(() => document.getElementById("question").value.includes("Toulouse"));
  // Two immediate activations must still produce exactly one comparison POST.
  await page.evaluate(() => {
    const button = document.getElementById("compare-btn");
    button.click(); button.click();
  });
  await page.waitForFunction(() => document.querySelectorAll("#cards .response-card[data-arm]").length === 4);
  assert.equal(compareRequests.length, 1);
  assert.equal(await page.locator("#cards .response-card[data-arm]").count(), 4);
  assert.match(await page.locator('#cards [data-arm="base"]').innerText(), /240/);
  assert.match(await page.locator('#cards [data-arm="t2l_gepa_opt"]').innerText(), /260/);
  await page.click('#cards [data-arm="t2l_gepa_opt"] .prompt-link');
  assert.equal(await page.locator("#prompt-dialog").isVisible(), true);
  assert.match(await page.locator("#dialog-prompt").innerText(), /Question: Toulouse/);
  await page.click("#dialog-close");
  await page.screenshot({ path: path.join(out, "02-four-methods.png"), fullPage: true });

  await page.fill("#question", "What is 1+1?");
  await page.click("#compare-btn");
  await page.waitForFunction(() => [...document.querySelectorAll("#cards .verdict")].every((v) => v.textContent === "UNSCORED") && document.querySelectorAll("#cards .verdict").length === 4);
  assert.equal(await page.locator("#cards .verdict:has-text('UNSCORED')").count(), 4);

  await page.click("#prompt-tab");
  await page.waitForSelector("#story-list .story-card:nth-child(4)");
  assert.equal(await page.locator("#story-list .story-card").count(), 4);
  assert.equal(await page.locator("#story-list .story-card").first().getAttribute("data-story"), "gepa-arc-challenge");
  assert.match(await page.locator("#story-method").innerText(), /ARC-C/);
  assert.notEqual(await page.locator("#gallery-best-prompt").innerText(), await page.locator("#gallery-seed-prompt").innerText());
  assert.ok(await page.locator("#story-changes li").count() >= 2);
  assert.equal(await page.locator("#case-list .case-card").count(), 3);
  assert.match(await page.locator("#before-verdict").innerText(), /WRONG/);
  assert.match(await page.locator("#after-verdict").innerText(), /CORRECT/);
  assert.match(await page.locator("#case-gold").innerText(), /gold/i);
  assert.match(await page.locator("#case-disclaimer").innerText(), /selected.*not.*aggregate/i);
  const firstCaseId = await page.locator("#case-detail").getAttribute("data-case");
  await page.locator("#case-list .case-card").nth(1).click();
  assert.notEqual(await page.locator("#case-detail").getAttribute("data-case"), firstCaseId);
  await page.locator("#case-list .case-card").nth(1).focus();
  await page.keyboard.press("Enter");
  assert.equal(await page.locator("#case-list .case-card").nth(1).getAttribute("aria-pressed"), "true");
  await page.screenshot({ path: path.join(out, "03-gepa-example-gallery.png"), fullPage: true });

  await page.locator('[data-story="t2l-gepa-boolq"]').click();
  assert.match(await page.locator("#story-title").innerText(), /BoolQ/);
  assert.match(await page.locator("#story-changes").innerText(), /passage/i);
  assert.notEqual(await page.locator("#gallery-best-prompt").innerText(), await page.locator("#gallery-seed-prompt").innerText());
  await page.locator("#raw-explorer > summary").click();
  await page.locator(".task-tab", { hasText: "GSM8K" }).click();
  await page.locator("[data-search-arm='gepa_3shot']").click();
  await page.waitForSelector("#unchanged-note:not([hidden])");
  assert.match(await page.locator("#unchanged-note").innerText(), /No better prompt found/);
  assert.equal(await page.locator("#selected-prompt").innerText(), await page.locator("#seed-prompt").innerText());
  await page.screenshot({ path: path.join(out, "03-library-unchanged.png"), fullPage: true });

  await page.locator(".task-tab", { hasText: "HellaSwag" }).click();
  await page.locator("[data-search-arm='t2l_gepa_opt']").click();
  await page.waitForFunction(() => document.getElementById("candidate-count").textContent.includes("4 stored") && document.getElementById("library-status").hidden);
  assert.match(await page.locator("#selected-title").innerText(), /Best instruction/);
  assert.doesNotMatch(await page.locator("#candidate-list").innerText(), /\d\.\d{6}/,
    "Pareto scores should stay compact instead of overflowing their candidate cards");
  await page.screenshot({ path: path.join(out, "04-library-optimized.png"), fullPage: true });
  const nonBest = await page.locator(".candidate").evaluateAll((nodes) =>
    nodes.find((node) => !node.querySelector(".best-label") && !node.textContent.includes("SEED")).dataset.candidate);
  await page.locator(`[data-candidate="${nonBest}"]`).click();
  assert.doesNotMatch(await page.locator("#selected-title").innerText(), /Best instruction/);
  assert.match(await page.locator("#selected-label").innerText(), /D_pareto/i);
  assert.ok(await page.locator("#selected-prompt .added").count() > 0);

  // A slow previous dataset must never overwrite the dataset selected most recently.
  await page.route("**/api/prompt-library?*", async (route) => {
    const requestUrl = new URL(route.request().url());
    const response = await route.fetch();
    const body = await response.json();
    if (requestUrl.searchParams.get("task") === "boolq") {
      body.best = "STALE BOOLQ RESPONSE";
      body.candidates[body.best_index].instruction = body.best;
      await new Promise((resolve) => setTimeout(resolve, 600));
    }
    await route.fulfill({ response, json: body });
  });
  await page.locator(".task-tab", { hasText: "BoolQ" }).click();
  await page.locator(".task-tab", { hasText: "HellaSwag" }).click();
  await page.waitForTimeout(800);
  assert.doesNotMatch(await page.locator("#selected-prompt").innerText(), /STALE BOOLQ RESPONSE/,
    "an older, slower history response must not overwrite the latest task selection");
  await page.unroute("**/api/prompt-library?*");

  await page.route("**/api/prompt-examples", (route) => route.fulfill({ json: { stories: [] } }));
  await page.click("#playground-tab");
  await page.click("#prompt-tab");
  await page.waitForSelector("#gallery-empty:not([hidden])");
  assert.match(await page.locator("#gallery-empty").innerText(), /No stored optimization stories/);
  assert.equal(await page.locator("#raw-explorer").isVisible(), true);
  await page.unroute("**/api/prompt-examples");
  await page.route("**/api/prompt-examples", (route) => route.fulfill({ json: { stories: [{ id: "broken" }] } }));
  await page.click("#playground-tab");
  await page.click("#prompt-tab");
  await page.waitForSelector("#gallery-status:not([hidden])");
  assert.match(await page.locator("#gallery-status").innerText(), /could not be displayed/i);
  await page.unroute("**/api/prompt-examples");
  await page.click("#playground-tab");
  await page.click("#prompt-tab");
  await page.waitForSelector("#story-list .story-card:nth-child(4)");

  // Malformed nested cases must be dropped without suppressing healthy stories in either order.
  for (const malformedIndex of [0, 2]) {
    await page.route("**/api/prompt-examples", async (route) => {
      const response = await route.fetch();
      const body = await response.json();
      const malformed = structuredClone(body.stories[0]);
      malformed.id = `broken-options-${malformedIndex}`;
      malformed.cases[0].options = { invalid: "shape" };
      body.stories.splice(malformedIndex, 0, malformed);
      await route.fulfill({ response, json: body });
    });
    await page.goto(baseUrl, { waitUntil: "networkidle" });
    await page.click("#prompt-tab");
    await page.waitForSelector("#story-list .story-card:nth-child(4)");
    assert.equal(await page.locator("#story-list .story-card").count(), 4);
    assert.equal(await page.locator(`[data-story="broken-options-${malformedIndex}"]`).count(), 0);
    for (const storyId of ["gepa-arc-challenge", "t2l-gepa-arc-challenge", "t2l-gepa-boolq", "t2l-gepa-hellaswag"]) {
      await page.locator(`[data-story="${storyId}"]`).click();
      assert.equal(await page.locator("#story-detail").isVisible(), true);
      assert.ok((await page.locator("#after-output").innerText()).length > 0);
    }
    await page.waitForFunction(() => document.getElementById("library-status").hidden);
    await page.unroute("**/api/prompt-examples");
  }
  await page.goto(baseUrl, { waitUntil: "networkidle" });
  await page.click("#prompt-tab");
  await page.waitForSelector("#story-list .story-card:nth-child(4)");

  await page.setViewportSize({ width: 390, height: 844 });
  await page.screenshot({ path: path.join(out, "05-mobile-library.png"), fullPage: true });
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1), true,
    "prompt history must not overflow a mobile viewport");
  await page.click("#playground-tab");
  await page.screenshot({ path: path.join(out, "06-mobile-playground.png"), fullPage: true });
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1), true,
    "playground must not overflow a mobile viewport");

  // Incomplete tasks are excluded instead of contributing fabricated zeroes or throwing.
  const results = await (await page.request.get(`${baseUrl}/api/results`)).json();
  const incompleteAccuracy = [
    "| arm | task | n | score | 95% CI | delta vs base | 95% CI |",
    "|---|---|---|---|---|---|---|",
    "| base | gsm8k | 1000 | 47.8% | [44.8, 50.9] | - | - |",
    "| t2l_icl | gsm8k | 1000 | 48.4% | [45.3, 51.5] | +0.6pp | [-2.9, +4.1] |",
    "| gepa_3shot | gsm8k | 1000 | 39.8% | [36.8, 42.9] | -8.0pp | [-11.6, -4.3] |",
    "| t2l_gepa_opt | gsm8k | 1000 | 48.0% | [44.8, 51.1] | +0.2pp | [-3.3, +3.6] |",
    "| base | arc_challenge | 1000 | 74.2% | [71.5, 76.9] | - | - |",
    "| t2l_icl | arc_challenge | 1000 | 73.7% | [70.9, 76.5] | -0.5pp | [-3.1, +2.0] |",
    "| gepa_3shot | arc_challenge | 1000 | 72.8% | [70.1, 75.6] | -1.4pp | [-3.9, +1.1] |",
    "| t2l_gepa_opt | arc_challenge | 1000 | 74.3% | [71.7, 77.0] | - | - |",
  ].join("\n");
  const incompleteCost = [
    "| arm | task | GPU seconds | generated tokens | metric calls | reflection calls |",
    "|---|---|---|---|---|---|",
    "| base | gsm8k | 332.6 | 245509 | 1000 | 0 |",
    "| t2l_icl | gsm8k | 261.4 | 141121 | 1000 | 0 |",
  ].join("\n");
  await page.route("**/api/results", (route) => route.fulfill({ json: {
    ...results, accuracy_md: incompleteAccuracy, cost_md: incompleteCost,
  } }));
  await page.goto(baseUrl, { waitUntil: "networkidle" });
  assert.equal(await page.locator("#eval-chart .task-chart").count(), 1,
    "a task with a missing non-base delta is incomplete and must not be charted");
  assert.match(await page.locator('#summary-cards [data-arm="base"] .summary-score').innerText(), /47\.8/);
  assert.equal((await page.locator('#cost-summary [data-arm="base"] .cost-time').innerText()).trim(), "—",
    "partial cost groups must not masquerade as a full-budget total");
  assert.equal(await page.locator('#cost-summary .cost-time:text-is("—")').count(), 4);
  assert.match(await page.locator("#cost-heading").innerText(), /unavailable/i);
  await page.unroute("**/api/results");

  await page.route("**/api/results", (route) => route.fulfill({ status: 500, json: { detail: "stored results unavailable" } }));
  expectsResultsFailure = true;
  await page.goto(baseUrl, { waitUntil: "networkidle" });
  expectsResultsFailure = false;
  assert.equal(await page.locator("#results-error").isVisible(), true);
  assert.match(await page.locator("#results-error").innerText(), /stored results unavailable/);
  assert.equal(await page.locator("#playground-view").isVisible(), true);
  assert.equal(await page.locator("#sample-btn").isEnabled(), true);
  await page.click("#sample-btn");
  await page.waitForFunction(() => document.getElementById("question").value.includes("Toulouse"));
  await page.click("#compare-btn");
  await page.waitForFunction(() => document.querySelectorAll("#cards .response-card[data-arm]").length === 4);
  assert.equal(await page.locator("#cards .response-card[data-arm]").count(), 4,
    "a results API failure must not disable live sampling or comparison");
  await page.unroute("**/api/results");

  assert.deepEqual(errors, [], "no browser runtime errors");
  console.log(JSON.stringify({ ok: true, screenshots: fs.readdirSync(out).sort(),
    comparePosts: compareRequests.length, pageErrors: errors }, null, 2));
} finally {
  await browser.close();
}
