import logging
import os
import re
from datetime import datetime

import pandas as pd

from src.glyph_ocr import GlyphLibrary, read_screen

logger = logging.getLogger(__name__)

FOLDER_PATH = r"C:\Users\skrishnan1\Videos\Ford Project Test"

_DIV = re.compile(r'DIV:\s*(\S+)\s+PLT:')
_PLT = re.compile(r'PLT:\s*(\S+)\s+DOC\s+NO:')
_DOC = re.compile(r'DOC\s+NO:\s*(\S+)\s+(\S+)\s+ITEM:')
_ITEM = re.compile(r'ITEM:\s*(\S+)\s+LINE:')
_ORDER_QTY = re.compile(r'Order\s+Qty:\s*(\S+)')

# Receipt detail occupies two screen lines per receipt.
_RECEIPT_HEAD = re.compile(
    r'^\s*[A-Z]\s+((?:MC|PA)\w+)\s+(\S{2})\s+'
    r'(\d{2}/\d{2}/\d{2})\s+(\d{2}/\d{2}/\d{2})\s+'
    r'[A-Z]{3}\s+(\S+)(?:\s+.*)?$')
_RECEIPT_TAIL = re.compile(r'^\s*(\S+)\s+(-?[\d,]+)\s+([\d,]+\.\d+)(?:\s+.*)?$')


def _first(pattern, text, group=1):
    m = pattern.search(text)
    return m.group(group).strip() if m else None


def parse_screen(lines):
    """Extract the CPARS Receipt History fields from a recognised screen."""
    text = "\n".join(lines)

    doc_m = _DOC.search(text)
    item = _first(_ITEM, text)
    header = {
        "DIV": _first(_DIV, text),
        "PLT": _first(_PLT, text),
        # The document number is displayed as two space-separated halves.
        "DOC NO": (doc_m.group(1) + doc_m.group(2)) if doc_m else None,
        # Trailing underscores are unfilled field positions, not data.
        "ITEM": item.rstrip("_") if item else None,
        "Order Qty": _first(_ORDER_QTY, text),
    }

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


def run_ocr(folder_path=FOLDER_PATH):
    """Recognise every screenshot in folder_path and save OCR_Extracted.xlsx."""
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

        worksheet = writer.sheets['Summary']
        for col, width in [('A', 18), ('B', 8), ('C', 8), ('D', 20), ('E', 20), ('F', 12), ('G', 12)]:
            worksheet.column_dimensions[col].width = width

    logger.info(f"OCR: Extraction complete. {len(df)} rows saved to {output_excel}")
    logger.info(f"OCR: Summary sheet created with {len(summary_df)} unique combinations")
