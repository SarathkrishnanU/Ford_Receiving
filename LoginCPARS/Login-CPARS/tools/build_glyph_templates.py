"""Rebuild src/glyph_templates.npz from labelled sample screenshots.

Run this only when the terminal font, emulator zoom level, or screen resolution
changes. Workflow:

  1. python tools/build_glyph_templates.py --cluster <folder-of-pngs>
     -> writes _glyphwork/contact_sheet.png and _glyphwork/clusters.npy
  2. Read the labels off the contact sheet, in index order, into LABELS below.
  3. python tools/build_glyph_templates.py --emit
"""

import argparse
import os
import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from src.glyph_ocr import (CELL_H, CELL_W, PAD, INK_LEVEL, BLANK_INK,  # noqa: E402
                           cell_windows, TEMPLATE_FILE)

WORK = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "_glyphwork")
CLUSTER_THRESHOLD = 0.06     # 1 - NCC; below this two cells are the same glyph

# Read off contact_sheet.png in index order. Duplicates are expected and fine:
# the same character appears more than once because 3270 field colours change
# the anti-aliasing. A space labels a glyph that carries no text (the field
# attribute mark rendered before a modifiable field).
LABELS = list(
    "-=e0S1P2tRirI_c3"
    "D/CAEpF9LT6oy::a"
    "7NU54MunOF8d6nBl"
    "xmNv5HsVQ,hk.Yvg"
    ";G> bfqZK"
)


def _cluster(folder):
    clusters = []
    for name in sorted(os.listdir(folder)):
        if not name.lower().endswith((".png", ".jpg", ".jpeg")) or name.startswith("_"):
            continue
        for _row, _col, win in cell_windows(os.path.join(folder, name)):
            core = win[PAD:PAD + CELL_H, PAD:PAD + CELL_W]
            if float(core.sum()) < BLANK_INK:
                continue
            best_d, hit = 1e9, None
            for cl in clusters:
                d = 1.0 - _best_ncc(win, cl["tpl"], cl["norm"])
                if d < best_d:
                    best_d, hit = d, cl
            if hit is not None and best_d < CLUSTER_THRESHOLD:
                hit["sum"] += core
                hit["count"] += 1
            else:
                clusters.append({"tpl": core.copy(), "sum": core.copy(), "count": 1,
                                 "norm": float(np.sqrt((core * core).sum()))})
    clusters.sort(key=lambda c: -c["count"])
    return np.stack([c["sum"] / c["count"] for c in clusters])


def _best_ncc(win, tpl, tnorm):
    best = 0.0
    for dy in range(2 * PAD + 1):
        for dx in range(2 * PAD + 1):
            a = win[dy:dy + CELL_H, dx:dx + CELL_W]
            na = float(np.sqrt((a * a).sum()))
            if na == 0.0:
                continue
            s = float((a * tpl).sum()) / (na * tnorm)
            if s > best:
                best = s
    return best


def _contact_sheet(templates, path, cols=16, scale=3):
    cw, ch = CELL_W * scale + 14, CELL_H * scale + 24
    rows = (len(templates) + cols - 1) // cols
    sheet = np.full((rows * ch, cols * cw, 3), 255, np.uint8)
    for i, tpl in enumerate(templates):
        gy, gx = divmod(i, cols)
        big = cv2.resize((tpl * 255).clip(0, 255).astype(np.uint8),
                         (CELL_W * scale, CELL_H * scale), interpolation=cv2.INTER_NEAREST)
        big = 255 - cv2.cvtColor(big, cv2.COLOR_GRAY2BGR)
        y, x = gy * ch + 20, gx * cw + 7
        sheet[y:y + CELL_H * scale, x:x + CELL_W * scale] = big
        cv2.rectangle(sheet, (x - 1, y - 1), (x + CELL_W * scale, y + CELL_H * scale),
                      (190, 190, 190), 1)
        cv2.putText(sheet, str(i), (gx * cw + 4, gy * ch + 15),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 220), 1, cv2.LINE_AA)
    cv2.imwrite(path, sheet)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cluster", metavar="FOLDER")
    ap.add_argument("--emit", action="store_true")
    args = ap.parse_args()
    os.makedirs(WORK, exist_ok=True)
    npy = os.path.join(WORK, "clusters.npy")

    if args.cluster:
        templates = _cluster(args.cluster)
        np.save(npy, templates)
        _contact_sheet(templates, os.path.join(WORK, "contact_sheet.png"))
        print(f"{len(templates)} clusters -> {npy} and contact_sheet.png")

    if args.emit:
        templates = np.load(npy)
        if len(LABELS) != len(templates):
            raise SystemExit(f"LABELS has {len(LABELS)} entries but there are "
                             f"{len(templates)} templates")
        np.savez_compressed(TEMPLATE_FILE,
                            templates=templates.astype(np.float32),
                            labels=np.array(LABELS))
        print(f"wrote {len(LABELS)} templates -> {TEMPLATE_FILE}")


if __name__ == "__main__":
    main()
