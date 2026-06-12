import os
import re
import logging
import pandas as pd
from PIL import Image, ImageEnhance
import pytesseract
from datetime import datetime
import cv2
import numpy as np

logger = logging.getLogger(__name__)

pytesseract.pytesseract.tesseract_cmd = r"C:\Users\skrishnan1\AppData\Local\Programs\Tesseract-OCR\tesseract.exe"

FOLDER_PATH = r"C:\Users\skrishnan1\Videos\Ford Project Test"


def preprocess_image(image_path):
    img = cv2.imread(image_path)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    height, width = gray.shape
    if width < 2000:
        scale = 2000 / width
        gray = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
    clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
    enhanced = cv2.morphologyEx(enhanced, cv2.MORPH_CLOSE, kernel)
    _, thresh = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    pil_image = Image.fromarray(thresh)
    enhancer = ImageEnhance.Sharpness(pil_image)
    return enhancer.enhance(2.5)


def between(text, start, end):
    pattern = rf'{re.escape(start)}\s*(.*?)\s*(?={re.escape(end)})'
    match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
    return match.group(1).strip() if match else None


def extract_order_qty_confident(text):
    order_qty_match = re.search(r'Order\s*Qty:\s*(\d+)', text, re.IGNORECASE)
    if not order_qty_match:
        return None
    qty_str = order_qty_match.group(1)
    if len(qty_str) == 3 and qty_str[1] in '68':
        return qty_str[0] + '0'
    return qty_str


def correct_ocr_errors(text):
    text = re.sub(r'(USD\s+)@(\d)', r'\g<1>0\g<2>', text, flags=re.IGNORECASE)
    text = re.sub(r'(\$)@(\d)', r'\g<1>0\g<2>', text)
    text = re.sub(r'(\d+\.\d+)@(\d+)', r'\g<1>0\g<2>', text)
    text = re.sub(r'(\d+\.?)@(\d+)', r'\g<1>0\g<2>', text)
    text = re.sub(r'(^|\D)([0-9])([6-8])/(\d{1,2}/\d{2})', r'\g<1>\g<2>0/\g<4>', text, flags=re.MULTILINE)
    text = re.sub(r'(MC\d+)@(\d)', r'\g<1>0\g<2>', text)
    text = re.sub(r'@([0-9])', r'0\g<1>', text)
    text = re.sub(r'(\s)8(\d{8,})', r'\g<1>5\g<2>', text)
    text = re.sub(r'(LINE:\s*)([68])(\s)', r'\g<1>0\g<3>', text, flags=re.IGNORECASE)
    text = re.sub(r'(\d{1,2})/(\d{3})/(\d{2})', lambda m: f"{m.group(1)}/{m.group(2)[0]}{m.group(2)[2]}/{m.group(3)}", text)
    return text


receipt_pattern = re.compile(
    r'S\s+(MC\d+\S*)\s+(.+?)(\d{1,2}/\d{1,3}/\d{2})\s+(\d{1,2}/\d{1,3}/\d{2})\s+USD\s*(\S+).*?\n\s*(\d*)\s*([-\d]+)',
    re.MULTILINE | re.IGNORECASE | re.DOTALL
)


def run_ocr(folder_path=FOLDER_PATH):
    """Run OCR extraction on all images in folder_path and save results to OCR_Extracted.xlsx."""
    rows = []

    image_files = [f for f in os.listdir(folder_path) if f.lower().endswith((".png", ".jpg", ".jpeg"))]
    logger.info(f"OCR: Found {len(image_files)} image(s) in folder: {folder_path}")

    for file_name in image_files:
        logger.info(f"OCR: Processing: {file_name}")
        preprocessed_img = preprocess_image(os.path.join(folder_path, file_name))
        config = '--psm 3 --oem 3 -c tessedit_write_output_file=0'
        text = pytesseract.image_to_string(preprocessed_img, config=config)
        text = re.sub(r'[ ]{2,}', ' ', text)
        text = correct_ocr_errors(text)

        div = between(text, 'DIV:', 'PLT:')
        plt = between(text, 'PLT:', 'DOC NO:')
        doc_no = between(text, 'DOC NO:', 'ITEM:')
        item = between(text, 'ITEM:', 'LINE:')

        order_qty_match = re.search(r'Order\s*Qty:\s*(\d+)', text, re.IGNORECASE)
        order_qty = extract_order_qty_confident(text) if order_qty_match else None

        matches = receipt_pattern.findall(text)
        logger.info(f"OCR: {len(matches)} match(es) found in {file_name}")

        for match in matches:
            mc_num, status_info, rec_dt, ship_dt, invoice_num, packing_slip, qty_recd = match
            status_match = re.search(r'(OK|PR|@\d+|\d{2})', status_info)
            status = status_match.group(1) if status_match else status_info.strip()
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

    df = pd.DataFrame(rows)
    output_excel = os.path.join(folder_path, "OCR_Extracted.xlsx")

    with pd.ExcelWriter(output_excel, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Sheet1')

        summary_df = df.groupby(['File Name', 'DIV', 'PLT', 'DOC NO', 'ITEM', 'Order Qty'], as_index=False).agg({
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
