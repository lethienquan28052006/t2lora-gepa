# Mistral demo web — Design

Date: 2026-11-17
Status: approved in conversation (both open questions answered)

## 1. Intent

A public web page that lets anyone put the same Mistral-7B-Instruct-v0.2 question through three
adaptation surfaces side by side — no adapter, a T2L LoRA + 3-shot, and a GEPA-optimised
instruction + 3-shot — and see the answers, the latency, and (when the item comes from the
test set) whether each surface got it right.

Hosted at `cs222.lethienquan.site` through the user's existing named cloudflared tunnel.

## 2. Decisions

| Decision | Value |
|---|---|
| Item source | both: sample a random test item (scored) or type your own question (unscored) |
| Tasks | the five from the study: gsm8k, arc_challenge, boolq, hellaswag, winogrande |
| Arms | `base` (zero-shot), `t2l_icl` (LoRA + 3-shot), `gepa` (best prompt + 3-shot) |
| Serving | one vLLM process, GPU 7, demo settings (`gpu_memory_utilization 0.35`, ~20GB) |
| Web stack | FastAPI + static HTML/CSS/JS (no build step), port 7860 |
| GEPA prompts | `results/gepa_<task>_s0_best_prompt.txt` from the completed sweep |
| Tunnel | named tunnel `68bc1088`, new ingress rule + DNS CNAME for cs222 |
| Start-up | one script starts vLLM, waits, starts web, traps to shut both down |

## 3. What the page shows

- Task tabs; a question box; optional options box; a "random test item" button; "Compare".
- Three answer cards: **Base**, **T2L + ICL**, **GEPA + ICL**, each with latency and token count.
- When the item came from the test set: gold answer and a correct/incorrect badge per card.
- A collapsible "prompt sent" per card, so the mechanism difference is visible.
- A results tab: the accuracy and cost tables from the run (read from `results/`).

## 4. Non-goals

- No streaming, no chat history, no auth.
- No GPU selection UI: the page shows whichever server `start_demo.sh` started.
- No re-running GEPA from the web.

## 5. Risks

| Risk | Mitigation |
|---|---|
| Demo model config (0.35) cannot serve the load of a public page | vLLM batches; if it saturates, raise to 0.6 and restart |
| Tunnel restart interrupts the user's other three hostnames | confirm with the user (done); their rules are preserved verbatim |
| A GEPA prompt file missing | the card shows "no GEPA prompt for this task" and the arm is skipped |
| Free-text MCQ without options | options box is optional; prompt renders without choices |
