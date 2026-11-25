"""Regenerate every slide figure from the source paper PDFs — as true vectors.

Each crop is a rectangle in PDF points (1/72 inch). Instead of rasterising, the
paper page itself is copied into a one-page PDF of exactly that size and moved
so the crop lands at the origin, with everything outside the crop clipped. The
result stays sharp at any projection resolution and keeps the paper's own
colours. Rectangles stop a few points above the figure caption, so no caption
text leaks into a slide.

Usage:
    .venv-slides/bin/python slides/tools/crop_figures.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pymupdf

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "source"
FIGURE = ROOT / "figure"

T2L = "2506.06105v2.pdf"
GEPA = "2507.19457v2.pdf"

# output path -> (source pdf, page, (x0, y0, x1, y1))
CROPS: dict[str, tuple[str, int, tuple[float, float, float, float]]] = {
    # --- Text-to-LoRA ---
    "t2l/fig1_train.pdf":       (T2L,  2, (55, 66, 316, 332)),
    "t2l/fig1_scaling.pdf":     (T2L,  2, (320, 66, 546, 332)),
    "t2l/fig2_arch.pdf":        (T2L,  3, (55, 66, 543, 182)),
    "t2l/fig3_error.pdf":       (T2L,  5, (330, 260, 545, 395)),
    "t2l/fig4_qualitative.pdf": (T2L,  8, (55, 66, 545, 392)),
    # tables the source deck shows as screenshots (kept as printed by the paper)
    "t2l/table1_recon.pdf":         (T2L, 5, (55, 103, 545, 250)),
    "t2l/table2_zeroshot_a.pdf":    (T2L, 6, (55, 122, 545, 208)),
    "t2l/table2_zeroshot_b.pdf":    (T2L, 6, (55, 208, 545, 314)),
    "t2l/table3_scaling.pdf":       (T2L, 7, (118, 84, 480, 212)),
    # --- GEPA ---
    "gepa/fig1_learning.pdf":   (GEPA, 1, (95, 458, 500, 600)),
    "gepa/fig3_pipeline.pdf":   (GEPA, 5, (92, 95, 520, 334)),
    "gepa/fig4_algo.pdf":       (GEPA, 6, (92, 121, 520, 382)),
    "gepa/fig6_strategy.pdf":   (GEPA, 10, (92, 300, 480, 492)),
    "gepa/fig9_merge.pdf":      (GEPA, 24, (92, 300, 530, 520)),
    "gepa/fig10_perf.pdf":      (GEPA, 28, (92, 90, 500, 393)),
    "gepa/fig16_gap.pdf":       (GEPA, 30, (88, 88, 523, 286)),
}


def vector_crop(page: pymupdf.Page, clip: pymupdf.Rect) -> pymupdf.Document:
    """One-page PDF of `clip` with the source page copied in, clipped."""
    out = pymupdf.open()
    target = out.new_page(width=clip.width, height=clip.height)
    target.show_pdf_page(
        target.rect, page.parent, page.number, clip=clip, keep_proportion=False
    )
    return out


def main() -> int:
    docs: dict[str, pymupdf.Document] = {}
    manifest = []
    for rel, (pdf, page_no, rect) in CROPS.items():
        doc = docs.setdefault(pdf, pymupdf.open(SOURCE / pdf))
        page = doc[page_no - 1]
        clip = pymupdf.Rect(*rect) & page.rect
        out_path = FIGURE / rel
        out_path.parent.mkdir(parents=True, exist_ok=True)
        cropped = vector_crop(page, clip)
        cropped.save(out_path, garbage=4, clean=True, deflate=True)
        manifest.append(
            {
                "file": rel,
                "source": pdf,
                "page": page_no,
                "rect_points": [round(v, 1) for v in clip],
                "aspect": round(clip.width / clip.height, 3),
            }
        )
        print(f"{rel:28s} p{page_no:<3d} {clip.width:6.1f} x {clip.height:5.1f} pt"
              f"  aspect {clip.width / clip.height:.2f}")
    (FIGURE / "crops.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
