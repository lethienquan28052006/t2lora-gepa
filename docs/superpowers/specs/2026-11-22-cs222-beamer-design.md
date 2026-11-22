# Beamer deck for CS222 — Prompting & PEFT (T2L vs GEPA) — design

**Date:** 2026-11-22
**Goal:** Rebuild `slides/source/slide-cs222.pptx.pdf` as a cleaner Beamer (XeLaTeX) deck in
`slides/`, same content and storyline, with figures re-cropped from the two papers into
`slides/figure/`, tables typeset in LaTeX, and each section in its own `.tex` file pulled
together by one master file.

## Why

The current PDF was made from slides with screenshots pasted in: figures are low-res
bitmaps of the paper, several tables are screenshots, and some slides carry a figure with no
message. A native LaTeX deck is editable, vector-crisp when projected, and portable to
Overleaf.

## Goals

- Compile with `xelatex` on BasicTeX (macOS) and on Overleaf, no machine-specific paths.
- Easy Overleaf upload: one folder, compiles from the root file as-is.
- Same 6-block storyline as the source: title → outline → DTA → GEPA → T2L → cost/limits.
- Figures: vector crops from `slides/source/*.pdf` at 300 dpi, named by paper figure.
- Tables: real `booktabs` / `tabularx` tables with the paper's numbers, highlighted the way the
  paper highlights (green = beats oracle, bold = beats multi-task LoRA).
- Key diagrams that the original deck drew by hand (hypernetwork, batch size, architecture)
  are drawn natively in TikZ so they scale and recolor with the deck.

## Non-goals

- No animation, no `\pause`-heavy build (a few overlays only where they help).
- No new experiments, no repo results — this deck is about the two papers, like the source.
- Not reproducing the paper's appendix figures (task lists, descriptions, t-SNE).
- Not translating content: keep Vietnamese text, keep the paper terminology in English.

## Anti-goals (would make this a failure)

- A deck that compiles here but not on Overleaf (fonts, file names, absolute paths).
- Figures that are still screenshots of slides (fuzzy, with slide background baked in).
- A deck that is a wall of bullets where a figure carries the message.

## Constraints

- **Compiler:** XeLaTeX, `fontspec` + `babel[vietnamese]` (as in the existing demo), TeX Live 2026
  (BasicTeX 2026) so package names match Overleaf's TeX Live.
- **Fonts on Overleaf:** use Latin Modern (default), DejaVu, or TeX Gyre; **do not** rely on
  macOS system fonts. Metro theme + `Fira Sans` is the one goal: if Fira is not available, fall
  back to `\setmainfont{Latin Modern Roman}`; keep a `\IfFontExistsTF` guard.
- **File names:** ASCII only, lowercase, no spaces, no Vietnamese diacritics in paths.
- **Emoji:** avoid `twemojis` on body text (font dependency); use it only if it proves robust on
  Overleaf, otherwise pictograms via `fontawesome5` or plain text.

## Approaches considered

1. **XeLaTeX + Metro theme, sections as `\input` files, figures cropped from paper PDFs,
   hand-drawn TikZ for architecture diagrams.** (chosen)
   Pros: matches the existing demo toolchain, clean pro look, everything vector, Overleaf-friendly.
   Cons: more work than reusing images; needs a compile loop.
2. **LuaLaTeX + `luacolor`, custom minimal theme.** Pros: full control over typography.
   Cons: rarer on Overleaf, longer compile, no benefit for a class deck.
3. **pdflatex + `babel[vietnam]` + T5 encoding.** Pros: most universal.
   Cons: mangled diacritics and no fontspec; fights the existing demo.
4. **Keep the deck but re-export slides at higher DPI.** Pros: fast.
   Cons: still not editable, still bitmap — defeats the purpose.

## Design

### Layout

```
slides/
  main.tex                 master: theme, metadata, footer, \input of parts
  parts/
    00_title.tex           titlepage + outline + section divider helper
    01_dta.tex             1. Bài toán Downstream Task (1.1, 1.2, 1.3)
    02_gepa.tex            2. GEPA (2.1–2.6)
    03_t2l.tex             3. Text-to-LoRA (3.1–3.4)
    04_cost.tex            chi phí & hạn chế
    05_references.tex      tài liệu tham khảo
  figure/
    t2l/  gepa/            crops from paper, named by figure
  source/                  (unchanged: the 3 source PDFs)
  tools/
    crop_figures.py        reproduces every crop from source/*.pdf (PyMuPDF)
    compile.sh             xelatex -interaction=nonstopmode -halt-on-error, twice
  Makefile                 `make` = crop + compile; `make zip` = Overleaf-ready zip
```

`tools/` and `Makefile` never end up in the Overleaf zip (`make zip` packages `main.tex`,
`parts/`, `figure/`).

### Theme

- `Madrid` + `beaver` was the demo; the deck gets a cleaner pair: **Metro** theme, one
  accent family (deep navy + one warm accent for highlights), light gray block bodies.
- Footer: three columns — *Nhóm 5 – UIT* | *CS222 – Prompting & PEFT* | page numbers, using the
  groups from the source title slide (Nhóm 5: Bùi Huỳnh Tây, Lê Thiên Quân, Đoàn Hồng Bảo;
  GV: TS. Nguyễn Thị Quý).
- `\AtBeginSection` divider with the slide's own section title and a thin rule.

### Figures (crop plan)

All crops come from `slides/source/2506.06105v2.pdf` (T2L) and `2507.19457v2.pdf` (GEPA).
Boxes are in PDF points; `crop_figures.py` holds them and renders at 300 dpi.

| file | source | region | used on |
|---|---|---|---|
| `t2l/fig2_arch.pdf` | T2L p3 | fig 2 area above caption | Module 1 architecture (replaces 6 hand-made sketches) |
| `t2l/fig1_train.pdf` | T2L p2 | left half of fig 1 | Training: recon vs SFT |
| `t2l/fig1_scaling.pdf` | T2L p2 | right half of fig 1 | scale with #tasks (module 4) |
| `t2l/table1_recon` | T2L p5 Table 1 | — (typeset) | recon vs task LoRA |
| `t2l/table2_zeroshot` | T2L p6 Table 2 | — (typeset) | 3.4 Experiments |
| `t2l/fig4_qualitative.pdf` | T2L p8 | fig 4 | Module 2: same problem, 3 descriptions |
| `t2l/fig3_error.pdf` | T2L p5 | fig 3 | reconstruction vs SFT evidence |
| `gepa/fig3_pipeline.pdf` | GEPA p5 | fig 3 above caption | 2.3 pipeline |
| `gepa/fig4_algo.pdf` | GEPA p6 | left half of fig 4 | 2.3.1 Pareto selection (algorithm) |
| `gepa/fig6_strategy.pdf` | GEPA p10 | fig 6 | 2.3.1 greedy vs Pareto |
| `gepa/fig1_learning.pdf` | GEPA p1 | fig 1 | 2.5 results |
| `gepa/table1` | GEPA p8 Table 1 | — (typeset) | 2.5 results |
| `gepa/table3` | GEPA p10 Table 3 | — (typeset) | 2.3.1 evidence (merge into same slide) |

### Slides that change shape

- p25–26 (GEPA pipeline dumped as two screenshots) → one pipeline figure + 3-step takeaway,
  then a zoomed "one iteration" slide.
- p40–44 (six separate hand sketches for Module 1) → Fig 2 crop + one TikZ decision box
  (L/M/S output size vs parameter count) whose numbers match the deck's own table (55M / 34M / 5M).
- p52–54 (three table screenshots) → two typeset tables (Table 1, Table 2 excerpts) + one figure.

### What's left to the builder

- Exact wording of takeaway sentences for slides that had none (must be sourced from the paper).
- Whether to keep the "câu hỏi tương tác" style of the original (p34–36, p43, p45–46) — kept, since
  it's a class presentation; rendered as a highlighted `\begin{block}` question.

## Verification

- `make` compiles with zero errors and no overfull boxes > 10 pt (checked in the log).
- Visual check: render every page to PNG and confirm no figure overflows the frame.
- Overleaf-check: no absolute paths, no system fonts, file names ASCII, `make zip` output
  uploaded to a scratch Overleaf project compiles unchanged.
