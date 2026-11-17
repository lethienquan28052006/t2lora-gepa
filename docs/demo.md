# Mistral adaptation playground

Live: **https://cs222.lethienquan.site**

## Start / stop

```bash
cd /mnt/home/quan.lt/dev/t2lora-gepa
./scripts/start_demo.sh --tunnel     # model + web + cloudflared
# Ctrl-C stops everything it started
```

Without `--tunnel` it serves only `http://localhost:7860`.

The script reuses a model server or web app that is already running on ports 8010/7860, so it
is safe to call twice. Logs land in `/tmp/t2l-demo/`.

## What it does

- Starts vLLM on **GPU 7** with the local Mistral copy and all five T2L adapters
  (`gpu_memory_utilization 0.35`, ~20–30GB VRAM), from `serve_demo.yaml`.
- Starts the FastAPI page on **:7860**.
- Optionally starts the named cloudflared tunnel `68bc1088`, whose config routes
  `cs222.lethienquan.site → localhost:7860`.

## The page

- Five task tabs (gsm8k, arc_challenge, boolq, hellaswag, winogrande).
- **Random test item** pulls an item from the test split and shows its gold answer, so every
  card is scored correct/wrong. Typing your own question switches to an unscored comparison.
- Three cards: **Base** (zero-shot), **T2L + ICL** (LoRA for that task + 3 demos),
  **GEPA + ICL** (the best prompt found by the GEPA sweep + the same 3 demos).
- Each card shows the raw output, extracted prediction, latency, token count, and a
  collapsible view of the exact prompt sent.
- The study results tables are rendered at the bottom.

## Files

| Path | Role |
|---|---|
| `src/t2lgepa/webapp/arms.py` | prompt construction per surface |
| `src/t2lgepa/webapp/service.py` | sampling, generation, scoring |
| `src/t2lgepa/webapp/app.py` | FastAPI routes + static mount |
| `src/t2lgepa/webapp/static/` | index.html, style.css, app.js |
| `scripts/start_demo.sh` | process orchestration |
| `scripts/write_demo_config.py` | writes `serve_demo.yaml` |
| `~/.cloudflared/config.yml` | ingress rule for cs222 (backup: `config.yml.bak-cs222`) |
