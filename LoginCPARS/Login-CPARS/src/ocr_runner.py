import os
import re
import logging
import shutil
import time
import pandas as pd
from PIL import Image, ImageEnhance
import pytesseract
from datetime import datetime
import cv2
import numpy as np

logger = logging.getLogger(__name__)

_TESSERACT_CANDIDATES = [
    os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "Tesseract-OCR", "tesseract.exe"),
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
]

_TESSERACT_FALLBACK_URL = (
    "https://github.com/UB-Mannheim/tesseract/releases/download/"
    "v5.4.0.20240606/tesseract-ocr-w64-setup-5.4.0.20240606.exe"
)


def _get_tesseract_download_url():
    """Fetch the latest Tesseract Windows x64 installer URL from the GitHub API."""
    try:
        import requests as _requests
        resp = _requests.get(
            "https://api.github.com/repos/UB-Mannheim/tesseract/releases/latest",
            timeout=15,
            headers={"Accept": "application/vnd.github+json"},
        )
        resp.raise_for_status()
        assets = resp.json().get("assets", [])
        for asset in assets:
            name = asset.get("name", "")
            if name.startswith("tesseract-ocr-w64-setup") and name.endswith(".exe"):
                url = asset["browser_download_url"]
                logger.info(f"Latest Tesseract installer: {url}")
                return url
    except Exception as exc:
        logger.warning(f"Could not fetch latest Tesseract release from GitHub API: {exc}")
    logger.warning(f"Falling back to hardcoded URL: {_TESSERACT_FALLBACK_URL}")
    return _TESSERACT_FALLBACK_URL


def _ensure_tesseract():
    """Return path to tesseract.exe, auto-downloading and installing it silently if not found."""
    found = next((p for p in _TESSERACT_CANDIDATES if os.path.isfile(p)), None)
    if not found:
        # Also check if tesseract is available on PATH
        found = shutil.which('tesseract')
    if found:
        logger.info(f"Tesseract found at: {found}")
        return found

    # Not installed — inform user and download silently
    import tempfile
    import subprocess
    import tkinter as tk
    from tkinter import messagebox

    root = tk.Tk()
    root.withdraw()
    messagebox.showinfo(
        "Installing Tesseract OCR",
        "Tesseract OCR was not found on this machine.\n\n"
        "It will now be downloaded and installed automatically.\n"
        "This may take a minute — please wait."
    )
    root.destroy()

    install_dir = os.path.join(os.environ.get("LOCALAPPDATA", "C:\\"), "Programs", "Tesseract-OCR")
    tmp_path = None
    try:
        import requests as _requests
        download_url = _get_tesseract_download_url()
        with tempfile.NamedTemporaryFile(suffix=".exe", delete=False) as tmp:
            tmp_path = tmp.name
        logger.info(f"Downloading Tesseract from: {download_url}")
        response = _requests.get(download_url, stream=True, timeout=120)
        response.raise_for_status()
        with open(tmp_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=65536):
                if chunk:
                    f.write(chunk)
        logger.info("Download complete. Running silent install...")
        try:
            subprocess.run(
                [tmp_path, "/S", f"/D={install_dir}"],
                check=True,
                timeout=180
            )
        except OSError as _ose:
            if getattr(_ose, 'winerror', None) == 740:
                # Installer requires elevation — request UAC via ShellExecuteW runas
                import ctypes
                logger.info("Elevation required — requesting UAC prompt for Tesseract install...")
                ret = ctypes.windll.shell32.ShellExecuteW(
                    None, "runas", tmp_path, f'/S /D="{install_dir}"', None, 1
                )
                if ret <= 32:
                    raise RuntimeError(
                        f"ShellExecuteW (runas) failed with code {ret}. "
                        "Please install Tesseract manually from https://github.com/UB-Mannheim/tesseract/wiki"
                    )
                # Poll for tesseract.exe (up to 3 minutes) since ShellExecuteW is async
                logger.info("Waiting for elevated Tesseract installation to complete...")
                for _i in range(60):
                    time.sleep(3)
                    if any(os.path.isfile(p) for p in _TESSERACT_CANDIDATES) or shutil.which('tesseract'):
                        break
            else:
                raise
        logger.info("Tesseract installation complete.")
    except Exception as exc:
        logger.error(f"Failed to auto-install Tesseract: {exc}")
        root2 = tk.Tk()
        root2.withdraw()
        messagebox.showerror(
            "Tesseract Install Failed",
            f"Could not automatically install Tesseract OCR.\n\n"
            f"Please install it manually from:\nhttps://github.com/UB-Mannheim/tesseract/wiki\n\nError: {exc}"
        )
        root2.destroy()
        return None
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass

    found = next((p for p in _TESSERACT_CANDIDATES if os.path.isfile(p)), None)
    if found:
        logger.info(f"Tesseract installed successfully at: {found}")
    else:
        logger.warning("Tesseract install finished but tesseract.exe not found in expected locations.")
    return found

FOLDER_PATH = r"C:\Users\skrishnan1\Videos\Ford Project Test"

# ---------------------------------------------------------------------------
# CORRECTIONS FILE  (learning mechanism)
# ---------------------------------------------------------------------------
# corrections.json lives next to the exe (or script).  Add entries here to
# teach the system about recurring misreadings without changing any code.
#
# Structure:
#   {
#     "global": { "wrong": "right", ... },          <- applied to all raw OCR text
#     "DOC NO":  { "RL2614275l": "RL26142751", ... }, <- applied to that field only
#     "ORDER QTY": { "1OO": "100", ... },
#     "MC/PA Number": { "MC12345B": "MC123450", ... },
#     "Rec Dt": {},
#     "Ship Dt": {}
#   }

_DEFAULT_CORRECTIONS = {
    "_comment": (
        "Add known OCR misreadings as key->value pairs. "
        "'global' corrections apply to the whole raw OCR text. "
        "Field-name keys apply only to that extracted field."
    ),
    "global": {
        "@": "0"
    },
    "DOC NO": {},
    "ORDER QTY": {},
    "MC/PA Number": {},
    "Rec Dt": {},
    "Ship Dt": {}
}


def _corrections_path():
    import sys
    base = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) \
        else os.path.dirname(os.path.abspath(__file__))
    # For the installed exe the corrections file lives one level up (next to the exe)
    candidate = os.path.join(base, 'corrections.json')
    parent_candidate = os.path.join(os.path.dirname(base), 'corrections.json')
    if os.path.isfile(parent_candidate):
        return parent_candidate
    return candidate


def _load_corrections():
    """Load corrections.json, creating it with defaults if missing."""
    import json
    path = _corrections_path()
    if not os.path.isfile(path):
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(_DEFAULT_CORRECTIONS, f, indent=2)
            logger.info(f"Created default corrections file: {path}")
        except Exception as exc:
            logger.warning(f"Could not create corrections file: {exc}")
        return _DEFAULT_CORRECTIONS
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        logger.info(f"Loaded corrections file: {path} ({sum(len(v) for k, v in data.items() if k != '_comment' and isinstance(v, dict))} entries)")
        return data
    except Exception as exc:
        logger.warning(f"Could not read corrections file ({exc}) — using defaults")
        return _DEFAULT_CORRECTIONS


def _apply_global_corrections(text, corrections):
    """Apply global word-substitution corrections to raw OCR text."""
    global_map = corrections.get('global', {})
    for wrong, right in global_map.items():
        text = text.replace(wrong, right)
    return text


def _apply_field_correction(value, field_name, corrections):
    """Apply field-specific corrections to an already-extracted field value."""
    if value is None:
        return value
    field_map = corrections.get(field_name, {})
    for wrong, right in field_map.items():
        value = value.replace(wrong, right)
    return value


def preprocess_image(image_path):
    img = cv2.imread(image_path)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    height, width = gray.shape
    # Scale to at least 3000px wide for better character separation
    if width < 3000:
        scale = 3000 / width
        gray = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
    # Denoise slightly before contrast enhancement
    gray = cv2.fastNlMeansDenoising(gray, h=10)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
    enhanced = cv2.morphologyEx(enhanced, cv2.MORPH_CLOSE, kernel)
    _, thresh = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    pil_image = Image.fromarray(thresh)
    enhancer = ImageEnhance.Sharpness(pil_image)
    return enhancer.enhance(2.0)


def between(text, start, end):
    pattern = rf'{re.escape(start)}\s*(.*?)\s*(?={re.escape(end)})'
    match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
    return match.group(1).strip() if match else None


def extract_order_qty_confident(text):
    order_qty_match = re.search(r'Order\s*Qty:?\s*([\d OlI]+)', text, re.IGNORECASE)
    if not order_qty_match:
        return None
    # Normalise common character confusions in numeric fields: l/I -> 1, O -> 0
    qty_str = order_qty_match.group(1).strip()
    qty_str = re.sub(r'[lI]', '1', qty_str)
    qty_str = re.sub(r'O', '0', qty_str)
    qty_str = re.sub(r'\s', '', qty_str)  # remove accidental spaces
    if len(qty_str) == 3 and qty_str[1] in '68':
        return qty_str[0] + '0'
    return qty_str


def _fix_numeric(value):
    """Normalise common OCR confusions in a purely-numeric string."""
    if value is None:
        return value
    value = re.sub(r'[lI]', '1', value)
    value = re.sub(r'O', '0', value)
    value = re.sub(r'S', '5', value)   # S misread as 5 (or vice-versa) in numeric fields
    value = re.sub(r'B', '8', value)   # B misread as 8 in numeric fields
    value = re.sub(r'[Gg]', '9', value) # G/g misread as 9 in numeric fields
    return value


def _fix_div(value):
    """Fix common OCR confusions for the DIV field (single letter, e.g. 'B').

    OCR often reads letter 'B' as digit '8', 'G' as '6', etc.
    Apply digit-to-letter mapping so the division letter is preserved.
    """
    if value is None:
        return value
    _digit_to_letter = {'0': 'O', '1': 'I', '5': 'S', '8': 'B', '6': 'G', '2': 'Z'}
    return ''.join(_digit_to_letter.get(ch, ch) for ch in value.strip().upper())


def _fix_doc_no(value):
    """Fix DOC NO using its known fixed format: 2 alphabet chars + 8 digits.

    e.g.  RL26142751  (RL = letters, 26142751 = digits)

    First 2 positions: must be letters
      digit-like -> letter:  0->O, 1->I, 5->S, 8->B, 6->G, 2->Z
    Remaining positions: must be digits
      letter-like -> digit:  O->0, l/I->1, S->5, B->8, G/g->9, Z->2
    """
    if value is None:
        return value
    value = value.strip().upper()
    if len(value) < 2:
        return value

    _digit_to_letter = {'0': 'O', '1': 'I', '5': 'S', '8': 'B', '6': 'G', '2': 'Z'}
    _letter_to_digit = {'O': '0', 'I': '1', 'L': '1', 'S': '5', 'B': '8', 'G': '9', 'Z': '2'}

    prefix = ''.join(_digit_to_letter.get(ch, ch) for ch in value[:2])
    suffix = value[2:]
    suffix = re.sub(r'[lI]', '1', suffix)
    suffix = ''.join(_letter_to_digit.get(ch, ch) if not ch.isdigit() else ch for ch in suffix)

    return prefix + suffix


def _fix_alphanumeric(value):
    """Fix common OCR confusions in alphanumeric codes (DOC NO, MC number).

    In IBM 3270 monospace font:
      - digit 0 vs letter O  — context-dependent; digits after letters stay digits
      - lowercase l / I vs digit 1
      - S vs 5 when flanked by digits
      - B vs 8 when flanked by digits
    """
    if value is None:
        return value
    # Replace standalone lowercase l with 1 when surrounded by digits
    value = re.sub(r'(?<=\d)l(?=\d)', '1', value)
    value = re.sub(r'(?<=\d)I(?=\d)', '1', value)
    # Trailing lowercase l is almost always digit 1
    value = re.sub(r'l$', '1', value)
    # S between digits -> 5  (e.g. 2S3 -> 253)
    value = re.sub(r'(?<=\d)S(?=\d)', '5', value)
    # B between digits -> 8  (e.g. 1B2 -> 182)
    value = re.sub(r'(?<=\d)B(?=\d)', '8', value)
    return value


def _fix_date(value):
    """Fix common OCR confusions in MM/DD/YY date strings."""
    if value is None:
        return value
    # Replace l/I with 1, O with 0 in date positions
    value = re.sub(r'[lI]', '1', value)
    value = re.sub(r'O', '0', value)
    # Extra digit in middle segment: e.g. 07/113/26 -> 07/13/26
    value = re.sub(r'(\d{1,2})/(\d{3})/(\d{2})',
                   lambda m: f"{m.group(1)}/{m.group(2)[0]}{m.group(2)[2]}/{m.group(3)}",
                   value)
    return value


def _format_date_mmddyy(value):
    """Convert a 6-digit MMDDYY string (no slashes) to MM/DD/YY format.

    IBM 3270 OCR frequently drops the slash characters, yielding bare
    digit sequences such as '071026' instead of '07/10/26'.
    Falls back to _fix_date() for values that already contain slashes.
    """
    if value is None:
        return value
    v = str(value).strip()
    if re.match(r'^\d{6}$', v):
        return f"{v[:2]}/{v[2:4]}/{v[4:]}"
    return _fix_date(v)


def correct_ocr_errors(text):
    # Strip degree symbol — Tesseract artifact on 3270 screens (e.g. '@°6' should be '06')
    text = text.replace('°', '')
    text = text.replace('\xb0', '')  # U+00B0 degree sign, same thing
    text = re.sub(r'(USD\s+)@(\d)', r'\g<1>0\g<2>', text, flags=re.IGNORECASE)
    text = re.sub(r'(\$)@(\d)', r'\g<1>0\g<2>', text)
    text = re.sub(r'(\d+\.\d+)@(\d+)', r'\g<1>0\g<2>', text)
    text = re.sub(r'(\d+\.?)@(\d+)', r'\g<1>0\g<2>', text)
    text = re.sub(r'(^|\D)([0-9])([6-8])/(\d{1,2}/\d{2})', r'\g<1>\g<2>0/\g<4>', text, flags=re.MULTILINE)
    text = re.sub(r'(MC\d+)@(\d)', r'\g<1>0\g<2>', text)
    text = re.sub(r'@([0-9])', r'0\g<1>', text)
    text = re.sub(r'(\s)8(\d{8,})', r'\g<1>5\g<2>', text)
    text = re.sub(r'(LINE:\s*)([68])(\s)', r'\g<1>0\g<3>', text, flags=re.IGNORECASE)
    # Fix extra digit in date middle segment
    text = re.sub(r'(\d{1,2})/(\d{3})/(\d{2})',
                  lambda m: f"{m.group(1)}/{m.group(2)[0]}{m.group(2)[2]}/{m.group(3)}",
                  text)
    # l/I -> 1 when flanked by digits
    text = re.sub(r'(?<=\d)[lI](?=\d)', '1', text)
    # S -> 5 when flanked by digits (e.g. in doc numbers or quantities)
    text = re.sub(r'(?<=\d)S(?=\d)', '5', text)
    # Trailing l in alphanumeric tokens (e.g. RL26142751 misread as RL2614275l)
    text = re.sub(r'([A-Z0-9]{6,})l(\b)', r'\g<1>1\g<2>', text)
    return text


# Pattern handles IBM 3270 HOD OCR output where:
#   - A selection indicator letter (e.g. 'S') may be merged before MC/PA: SMC26191066
#   - MC or PA prefix is supported: MC26191066, PA26191066
#   - Status (OK/PR/2-digit code) is directly concatenated with date: OK071026
#   - Dates may be 6-digit MMDDYY without slashes: 071026 (= 07/10/26)
#     OR already slashed MM/DD/YY: 07/10/26
#   - Two dates are concatenated without separator: 071026071026
# Groups: MC/PA Number, Status, Rec Dt (MMDDYY), Ship Dt (MMDDYY),
#         Invoice No, Extd Price, Packing Slip No, Qty/Recd
receipt_pattern = re.compile(
    r'[A-Z]?\s*((?:MC|PA)\d+\S*)\s+([A-Z]{2}|\d{2})\s*(\d{6}|\d{2}/\d{2}/\d{2})\s*(\d{6}|\d{2}/\d{2}/\d{2})\s*USD\s*(\S+)(?:\s+([\d,]+))?\s*\n\s*(\S+)\s+([-\d]+)',
    re.MULTILINE | re.IGNORECASE
)


def run_ocr(folder_path=FOLDER_PATH):
    """Run OCR extraction on all images in folder_path and save results to OCR_Extracted.xlsx."""
    tesseract_path = _ensure_tesseract()
    if tesseract_path:
        pytesseract.pytesseract.tesseract_cmd = tesseract_path

    corrections = _load_corrections()
    rows = []

    image_files = [f for f in os.listdir(folder_path) if f.lower().endswith((".png", ".jpg", ".jpeg"))]
    logger.info(f"OCR: Found {len(image_files)} image(s) in folder: {folder_path}")

    for file_name in image_files:
        logger.info(f"OCR: Processing: {file_name}")
        preprocessed_img = preprocess_image(os.path.join(folder_path, file_name))
        # --oem 1: LSTM engine only (more accurate than combined)
        # --psm 6: uniform block of text (best for terminal screens)
        # whitelist covers all characters present on IBM 3270 CPARS screens
        config = (
            '--oem 1 --psm 6 -c tessedit_write_output_file=0 '
            '-c tessedit_char_whitelist='
            'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
            'abcdefghijklmnopqrstuvwxyz'
            '0123456789'
            r' /.-:$,()#=_@'
        )
        text = pytesseract.image_to_string(preprocessed_img, config=config)
        text = re.sub(r'[ ]{2,}', ' ', text)
        # 1. Apply systematic regex corrections
        text = correct_ocr_errors(text)
        # 2. Apply user-defined global corrections from corrections.json
        text = _apply_global_corrections(text, corrections)

        # Fields are often merged without colons in IBM 3270 OCR output
        # e.g. 'DIVBPLT43DOCNORL26442192ITEM012' — handle both spaced and merged forms
        _div_m  = re.search(r'DIV\s*:?\s*([A-Z\d]+?)\s*(?=PLT)', text, re.IGNORECASE)
        div     = _div_m.group(1).strip() if _div_m else between(text, 'DIV:', 'PLT:')

        _plt_m  = re.search(r'PLT\s*:?\s*(\d+)\s*(?=DOC)', text, re.IGNORECASE)
        plt     = _plt_m.group(1).strip() if _plt_m else between(text, 'PLT:', 'DOC NO:')

        _doc_m  = re.search(r'DOC\s*NO\s*:?\s*([A-Z]{1,3}\d+)', text, re.IGNORECASE)
        doc_no  = _doc_m.group(1).strip() if _doc_m else between(text, 'DOC NO:', 'ITEM:')

        _item_m = re.search(r'ITEM\s*:?\s*([A-Z\d]+?)\s*(?=LINE)', text, re.IGNORECASE)
        item    = _item_m.group(1).strip() if _item_m else between(text, 'ITEM:', 'LINE:')

        # Apply field-specific corrections + targeted fixups
        doc_no = _apply_field_correction(_fix_doc_no(doc_no), 'DOC NO', corrections)
        div    = _fix_div(div)
        plt    = _fix_numeric(plt)

        order_qty_match = re.search(r'Order\s*Qty:?\s*[\d OlI]+', text, re.IGNORECASE)
        order_qty = extract_order_qty_confident(text) if order_qty_match else None
        order_qty = _apply_field_correction(order_qty, 'ORDER QTY', corrections)

        matches = receipt_pattern.findall(text)
        logger.info(f"OCR: {len(matches)} match(es) found in {file_name}")

        if matches:
            for match in matches:
                mc_num, status, rec_dt_raw, ship_dt_raw, invoice_num, _extd_price, packing_slip, qty_recd = match
                # Fix confusions in each extracted field
                mc_num   = _apply_field_correction(_fix_alphanumeric(mc_num), 'MC/PA Number', corrections)
                rec_dt   = _apply_field_correction(_format_date_mmddyy(rec_dt_raw), 'Rec Dt', corrections)
                ship_dt  = _apply_field_correction(_format_date_mmddyy(ship_dt_raw), 'Ship Dt', corrections)
                qty_recd = _fix_numeric(qty_recd)
                status   = status.strip()
                rows.append({
                    "File Name": file_name,
                    "DIV": div,
                    "PLT": plt,
                    "DOC NO": doc_no,
                    "ITEM": item,
                    "Order Qty": order_qty,
                    "MC/PA Number": mc_num,
                    "Status": status,
                    "Rec Dt": rec_dt,
                    "Ship Dt": ship_dt,
                    "Qty/Recd": qty_recd,
                    "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                })
        else:
            # No receipt rows found — still include the image so all 27 appear in output
            rows.append({
                "File Name": file_name,
                "DIV": div,
                "PLT": plt,
                "DOC NO": doc_no,
                "ITEM": item,
                "Order Qty": order_qty,
                "MC/PA Number": None,
                "Status": None,
                "Rec Dt": None,
                "Ship Dt": None,
                "Qty/Recd": None,
                "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })

    df = pd.DataFrame(rows)
    output_excel = os.path.join(folder_path, "OCR_Extracted.xlsx")

    if df.empty:
        logger.info("OCR: No rows extracted — skipping Excel output")
        return

    with pd.ExcelWriter(output_excel, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Sheet1')

        summary_df = df.groupby(['DIV', 'PLT', 'DOC NO', 'ITEM', 'Order Qty'], as_index=False).agg({
            'Qty/Recd': lambda x: pd.to_numeric(x, errors='coerce').sum()
        })
        summary_df['Qty/Recd'] = summary_df['Qty/Recd'].astype('Int64')
        summary_df.to_excel(writer, index=False, sheet_name='Summary')

        worksheet = writer.sheets['Sheet1']
        for col, width in [('A',18),('B',8),('C',8),('D',20),('E',20),('F',12),('G',15),('H',10),('I',12),('J',12),('K',12),('L',20)]:
            worksheet.column_dimensions[col].width = width

        worksheet = writer.sheets['Summary']
        for col, width in [('A',18),('B',8),('C',8),('D',20),('E',20),('F',12),('G',12)]:
            worksheet.column_dimensions[col].width = width

    logger.info(f"OCR: Extraction complete. {len(df)} rows saved to {output_excel}")
    logger.info(f"OCR: Summary sheet created with {len(summary_df)} unique combinations")
