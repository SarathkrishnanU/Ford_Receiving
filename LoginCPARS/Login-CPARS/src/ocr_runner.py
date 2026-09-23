import logging
import os
import re
from datetime import datetime

import pandas as pd
from openpyxl.styles import Font, PatternFill

from src.glyph_ocr import GlyphLibrary, read_screen

logger = logging.getLogger(__name__)
OCR_BACKEND = "glyph-template"
OCR_HIGHLIGHT_COLUMNS = {"DIV", "PLT", "DOC NO", "ITEM"}
OCR_HEADER_FILL = PatternFill(fill_type="solid", fgColor="C00000")
OCR_DATA_FILL = PatternFill(fill_type="solid", fgColor="FCE4D6")
OCR_HEADER_FONT = Font(bold=True, color="FFFFFF")
OCR_DATA_FONT = Font(color="C00000")

FOLDER_PATH = r"C:\Users\skrishnan1\Videos\Ford Project Test"

# '.' wildcards stand in for label letters that the glyph matcher occasionally
# misreads (e.g. a stray unrecognised cell inside 'DIV'/'ITEM') so a single bad
# cell in a label doesn't take down the whole field match.
_DIV = re.compile(r'D.V\s*:\s*(\S+)\s+P.T\s*:')
_PLT = re.compile(r'P.T\s*:\s*(\S+)\s+D.C\s+NO\s*:')
_DOC = re.compile(r'D.C\s+NO\s*:\s*(\S+)\s+(\S+)\s+.TEM\s*:')
_ITEM = re.compile(r'.TEM\s*:\s*(\S+)\s+L.NE\s*:')
_ORDER_QTY = re.compile(r'Order\s+Qty\s*:\s*(\S+)')

# Receipt detail occupies two screen lines per receipt.
_RECEIPT_HEAD = re.compile(
    r'^\s*[A-Z]\s+((?:MC|PA)\w+)\s+(\S{2})\s+'
    r'(\d{2}/\d{2}/\d{2})\s+(\d{2}/\d{2}/\d{2})\s+'
    r'[A-Z]{3}\s+(\S+)(?:\s+.*)?$')
_RECEIPT_TAIL = re.compile(r'^\s*(\S+)\s+(-?[\d,]+)\s+([\d,]+\.\d+)(?:\s+.*)?$')

# The DIV/PLT/DOC NO/ITEM header is always on this line, at these columns, for
# the CPARS Receipt History screen (fixed 3270 layout) — slicing by position
# survives OCR misreads of the label text itself, unlike the regexes above
# which need every label letter read correctly to match at all.
_HEADER_LINE_INDEX = 2
_COL_DIV = slice(5, 8)
_COL_PLT = slice(12, 16)
_COL_DOC1 = slice(24, 28)
_COL_DOC2 = slice(29, 35)
_COL_ITEM = slice(42, 57)


def _header_by_column(lines):
    if len(lines) <= _HEADER_LINE_INDEX:
        return None
    line = lines[_HEADER_LINE_INDEX]
    if len(line) < _COL_ITEM.stop:
        return None
    doc_no = (line[_COL_DOC1].strip() + line[_COL_DOC2].strip()).strip()
    item = line[_COL_ITEM].strip().rstrip("_")
    return {
        "DIV": line[_COL_DIV].strip() or None,
        "PLT": line[_COL_PLT].strip() or None,
        "DOC NO": doc_no or None,
        "ITEM": item or None,
    }


def _first(pattern, text, group=1):
    m = pattern.search(text)
    return m.group(group).strip() if m else None


def parse_screen(lines):
    """Extract the CPARS Receipt History fields from a recognised screen."""
    text = "\n".join(lines)

    header = _header_by_column(lines) or {"DIV": None, "PLT": None, "DOC NO": None, "ITEM": None}

    # Column slicing can come up empty on an unexpected screen layout (e.g. a
    # shifted/differently-sized capture) — fall back to label matching per field.
    if header["DIV"] is None:
        header["DIV"] = _first(_DIV, text)
    if header["PLT"] is None:
        header["PLT"] = _first(_PLT, text)
    if header["DOC NO"] is None:
        doc_m = _DOC.search(text)
        header["DOC NO"] = (doc_m.group(1) + doc_m.group(2)) if doc_m else None
    if header["ITEM"] is None:
        item = _first(_ITEM, text)
        header["ITEM"] = item.rstrip("_") if item else None
    header["Order Qty"] = _first(_ORDER_QTY, text)

    if header["DOC NO"] is None or header["ITEM"] is None:
        header_line = lines[_HEADER_LINE_INDEX] if len(lines) > _HEADER_LINE_INDEX else ""
        logger.warning(f"OCR: header fields not matched, raw line: {header_line!r}")

    receipts = []
    for i, line in enumerate(lines):
        head = _RECEIPT_HEAD.match(line)
        if not head:
            continue
        mc_num, status, rec_dt, ship_dt, _invoice_no = head.groups()
        qty_recd = None
        if i + 1 < len(lines):
            tail = _RECEIPT_TAIL.match(lines[i + 1])
            if tail:
                qty_recd = tail.group(2).replace(",", "")
        receipts.append({
            "MC/PA Number": mc_num,
            "Status": status,
            "Rec Dt": rec_dt,
            "Ship Dt": ship_dt,
            "Qty/Recd": qty_recd,
        })
    return header, receipts


def _style_ocr_columns(worksheet):
    """Highlight key OCR identity columns in red."""
    for header_cell in worksheet[1]:
        if header_cell.value not in OCR_HIGHLIGHT_COLUMNS:
            continue

        header_cell.fill = OCR_HEADER_FILL
        header_cell.font = OCR_HEADER_FONT

        for data_cell in worksheet.iter_cols(
            min_col=header_cell.column,
            max_col=header_cell.column,
            min_row=2,
            max_row=worksheet.max_row,
        ):
            for cell in data_cell:
                cell.fill = OCR_DATA_FILL
                cell.font = OCR_DATA_FONT


def run_ocr(folder_path=FOLDER_PATH):
    """Recognise every screenshot in folder_path and save OCR_Extracted.xlsx."""
    logger.info(f"OCR backend: {OCR_BACKEND} using src/glyph_templates.npz")
    library = GlyphLibrary.load()
    rows = []

    image_files = [f for f in os.listdir(folder_path)
                   if f.lower().endswith((".png", ".jpg", ".jpeg"))]
    logger.info(f"OCR: Found {len(image_files)} image(s) in folder: {folder_path}")

    for file_name in image_files:
        logger.info(f"OCR: Processing: {file_name}")
        try:
            lines = read_screen(os.path.join(folder_path, file_name), library)
        except Exception as exc:
            logger.error(f"OCR: Failed to read {file_name}: {exc}", exc_info=True)
            continue

        header, receipts = parse_screen(lines)
        logger.info(f"OCR: {file_name} -> DOC NO={header['DOC NO']} "
                    f"ITEM={header['ITEM']} receipts={len(receipts)}")

        stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        blank = {"MC/PA Number": None, "Status": None, "Rec Dt": None,
                 "Ship Dt": None, "Qty/Recd": None}
        for receipt in (receipts or [blank]):
            rows.append({"File Name": file_name, **header, **receipt, "Timestamp": stamp})

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
        for col, width in [('A', 18), ('B', 8), ('C', 8), ('D', 20), ('E', 20), ('F', 12),
                           ('G', 15), ('H', 10), ('I', 12), ('J', 12), ('K', 12), ('L', 20)]:
            worksheet.column_dimensions[col].width = width
        _style_ocr_columns(worksheet)

        worksheet = writer.sheets['Summary']
        for col, width in [('A', 18), ('B', 8), ('C', 8), ('D', 20), ('E', 20), ('F', 12), ('G', 12)]:
            worksheet.column_dimensions[col].width = width
        _style_ocr_columns(worksheet)

    logger.info(f"OCR: Extraction complete. {len(df)} rows saved to {output_excel}")
    logger.info(f"OCR: Summary sheet created with {len(summary_df)} unique combinations")
