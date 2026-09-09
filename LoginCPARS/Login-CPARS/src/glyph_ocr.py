"""Character-cell OCR for IBM 3270 (Host On-Demand) screens.

The CPARS screens are a fixed 80x24 character grid rendered with a fixed-pitch
bitmap font, so recognition is done by locating the character grid and matching
each cell against a labelled glyph template library rather than by running a
general-purpose OCR engine. This is exact for the glyph pairs a general engine
confuses on this font (slashed 0 vs O, S vs 5, 1 vs l vs I, B vs 8).
"""

import logging
import os

import cv2
import numpy as np

logger = logging.getLogger(__name__)

CELL_H, CELL_W = 32, 20     # canonical template size
PAD = 2                     # +/- registration search margin, pixels
INK_LEVEL = 0.235           # normalised luminance above which a pixel is "lit"
BLANK_INK = 1.0             # total lit energy below which a cell is a space
MATCH_MIN_SCORE = 0.80      # NCC below this is reported as unrecognised

TEMPLATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             "glyph_templates.npz")
UNKNOWN = "\ufffd"


def crop_terminal(bgr):
    """Isolate the black terminal canvas from the surrounding emulator chrome."""
    dark = (bgr.max(axis=2) < 40).astype(np.uint8)
    count, _, stats, _ = cv2.connectedComponentsWithStats(dark, 8)
    if count <= 1:
        return bgr
    i = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
    x, y, w, h = stats[i, :4]
    return bgr[y:y + h, x:x + w]


def _fit_axis(profile, lo, hi, step=0.005):
    """Fit (offset, pitch) of the character grid on one axis.

    Cell boundaries in a fixed-pitch terminal fall in the gutters between
    glyphs, so the best grid is the one whose boundary lines carry the least
    ink.
    """
    n = len(profile)
    best = None
    for pitch in np.arange(lo, hi, step):
        k = np.arange(0, int(n / pitch) + 1)
        for off in np.arange(0.0, pitch, 0.25):
            idx = np.round(off + k * pitch).astype(int)
            idx = idx[(idx >= 0) & (idx < n)]
            if len(idx) < 5:
                continue
            cost = float(profile[idx].mean())
            if best is None or cost < best[2]:
                best = (float(off), float(pitch), cost)
    if best is None:
        raise ValueError("Could not locate a character grid in the image")
    off, pitch, _ = best
    while off - pitch > -pitch * 0.9:
        off -= pitch
    return off, pitch


def detect_grid(ink):
    """Return (x0, pitch_x, y0, pitch_y) of the character grid."""
    x0, px = _fit_axis(ink.sum(axis=0), 18.0, 22.0)
    y0, py = _fit_axis(ink.sum(axis=1), 28.0, 34.0)
    return x0, px, y0, py


def cell_windows(image_path):
    """Yield (row, col, window) for every character cell of the screen.

    Each window is the cell plus a PAD-pixel margin so the matcher can absorb
    the sub-pixel rounding of the fractional grid pitch.
    """
    bgr = cv2.imread(image_path)
    if bgr is None:
        raise ValueError(f"Could not read image: {image_path}")
    term = crop_terminal(bgr)
    # Phosphor text is cyan/green/white on black; the max channel preserves the
    # full stroke intensity that BGR->GRAY luma weighting would dim.
    lum = term.max(axis=2).astype(np.float32) / 255.0
    ink = (lum > INK_LEVEL).astype(np.float32)
    x0, px, y0, py = detect_grid(ink)

    h, w = lum.shape
    # Margin absorbs both the registration search and a grid origin that starts
    # left of / above the cropped canvas.
    margin = PAD + int(max(px, py)) + 1
    canvas = np.zeros((h + 2 * margin, w + 2 * margin), np.float32)
    canvas[margin:margin + h, margin:margin + w] = lum

    row = 0
    while y0 + (row + 1) * py <= h:
        col = 0
        while x0 + (col + 1) * px <= w:
            ya = int(round(y0 + row * py)) + margin
            xa = int(round(x0 + col * px)) + margin
            win = canvas[ya - PAD:ya + CELL_H + PAD, xa - PAD:xa + CELL_W + PAD]
            if win.shape == (CELL_H + 2 * PAD, CELL_W + 2 * PAD):
                yield row, col, win
            col += 1
        row += 1


def match_score(win, templates, norms):
    """Best NCC score and template index over all +/-PAD registration shifts."""
    best_score, best_idx = -1.0, -1
    flat = templates.reshape(len(templates), -1)
    for dy in range(2 * PAD + 1):
        for dx in range(2 * PAD + 1):
            patch = win[dy:dy + CELL_H, dx:dx + CELL_W].ravel()
            pn = float(np.sqrt(patch @ patch))
            if pn == 0.0:
                continue
            scores = (flat @ patch) / (pn * norms)
            i = int(np.argmax(scores))
            if scores[i] > best_score:
                best_score, best_idx = float(scores[i]), i
    return best_score, best_idx


class GlyphLibrary:
    def __init__(self, templates, labels):
        self.templates = templates.astype(np.float32)
        self.labels = list(labels)
        flat = self.templates.reshape(len(self.templates), -1)
        self.norms = np.sqrt((flat * flat).sum(axis=1))

    @classmethod
    def load(cls, path=TEMPLATE_FILE):
        data = np.load(path, allow_pickle=False)
        return cls(data["templates"], [str(s) for s in data["labels"]])


def read_screen(image_path, library=None):
    """Recognise a terminal screenshot and return it as a list of text lines."""
    library = library or GlyphLibrary.load()
    grid = {}
    unknown = 0
    for row, col, win in cell_windows(image_path):
        core = win[PAD:PAD + CELL_H, PAD:PAD + CELL_W]
        if float(core.sum()) < BLANK_INK:
            grid[(row, col)] = " "
            continue
        score, idx = match_score(win, library.templates, library.norms)
        if score < MATCH_MIN_SCORE:
            grid[(row, col)] = UNKNOWN
            unknown += 1
        else:
            grid[(row, col)] = library.labels[idx]
    if not grid:
        return []
    if unknown:
        logger.warning("%s: %d cell(s) below match threshold", os.path.basename(image_path), unknown)
    nrows = max(r for r, _ in grid) + 1
    ncols = max(c for _, c in grid) + 1
    return ["".join(grid.get((r, c), " ") for c in range(ncols)).rstrip()
            for r in range(nrows)]
