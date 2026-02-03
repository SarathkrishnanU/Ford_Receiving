import os
import re
import pandas as pd
from PIL import Image, ImageEnhance
import pytesseract
from datetime import datetime
import cv2
import numpy as np

pytesseract.pytesseract.tesseract_cmd = r"C:\Users\skrishnan1\AppData\Local\Programs\Tesseract-OCR\tesseract.exe"

folder_path = r"C:\Users\skrishnan1\Videos\Ford Project Test"
rows = []

def preprocess_image(image_path):
    """Preprocess image for better OCR accuracy"""
    img = cv2.imread(image_path)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # Resize image for better OCR (upscaling)
    height, width = gray.shape
    if width < 2000:
        scale = 2000 / width
        gray = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
    
    # CLAHE for contrast enhancement (slightly less aggressive)
    clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)
    
    # Morphological operations (lighter touch)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
    enhanced = cv2.morphologyEx(enhanced, cv2.MORPH_CLOSE, kernel)
    
    # Use Otsu's thresholding
    _, thresh = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    
    # Convert to PIL Image
    pil_image = Image.fromarray(thresh)
    
    # Sharpening (moderate)
    enhancer = ImageEnhance.Sharpness(pil_image)
    sharpened = enhancer.enhance(2.5)
    
    return sharpened

def between(text, start, end):
    pattern = rf'{re.escape(start)}\s*(.*?)\s*(?={re.escape(end)})'
    match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
    return match.group(1).strip() if match else None

def extract_item_code(text):
    """Extract ITEM code - alphanumeric pattern that represents a valid product code"""
    item_raw = between(text, 'ITEM:', 'LINE:')
    if not item_raw:
        return None
    
    # Remove any garbage after special character sequences (——, --, @, etc.)
    item_cleaned = re.sub(r'(——|-{2,}|@).*', '', item_raw.strip())
    
    # Match valid item pattern: alphanumeric (8-20 chars) optionally followed by space + single letter/number
    # Examples: 97E733401, 84140245R, 5403297114 R, 038ZC3524 5
    match = re.match(r'^([A-Z0-9]{7,20}(?:\s+[A-Z0-9])?)', item_cleaned.strip(), re.IGNORECASE)
    if match:
        return match.group(1).strip()
    
    return None

def extract_order_qty_confident(text):
    """Extract Order Qty with confidence checking"""
    order_qty_match = re.search(r'Order\s*Qty:\s*(\d+)', text, re.IGNORECASE)
    if not order_qty_match:
        return None
    
    qty_str = order_qty_match.group(1)
    qty_int = int(qty_str)
    
    # Check for suspicious patterns that indicate OCR errors
    # Pattern like 360, 380, 260, 280 - suspiciously round numbers with 6/8 in middle
    if len(qty_str) == 3 and qty_str[1] in '68':
        # Likely OCR error: 360->30, 380->30, 260->20, 280->20, etc.
        corrected = qty_str[0] + '0'
        return corrected
    
    # Otherwise return as-is - be conservative with corrections
    return qty_str

def correct_ocr_errors(text):
    """Correct common OCR recognition errors for 0, 6, 8, @
    
    Patterns learned:
    - @ is often misread for 0 in invoice numbers and prices
    - 8 is confused with 0 at start of numbers
    - 6 is confused with 0 in dates and quantities
    - @ appears instead of 0 in invoice/account numbers
    - B becomes 8 in some cases
    """
    
    # 1. Invoice numbers: Fix @ to 0 when followed by many digits (5$xxxx -> 5$0xxxx pattern)
    text = re.sub(r'(USD\s+)@(\d)', r'\g<1>0\g<2>', text, flags=re.IGNORECASE)  # USD @xxxx -> USD 0xxxx
    text = re.sub(r'(\$)@(\d)', r'\g<1>0\g<2>', text)  # $@xxxxx -> $0xxxxx
    
    # 2. Fix @ in prices/amounts that should be 0
    text = re.sub(r'(\d+\.\d+)@(\d+)', r'\g<1>0\g<2>', text)  # 1036.650@ -> 1036.6500
    text = re.sub(r'(\d+\.?)@(\d+)', r'\g<1>0\g<2>', text)  # 61.950@00 -> 61.950000
    
    # 3. Fix dates with 6 or 8 where 0 is expected
    text = re.sub(r'(^|\D)([0-9])([6-8])/(\d{1,2}/\d{2})', r'\g<1>\g<2>0/\g<4>', text, flags=re.MULTILINE)  # X6/XX/XX -> X0/XX/XX
    
    # 4. Fix MC/PA numbers: 088 should be 088 or sometimes O88 (letter O misread as 0)
    # Don't change legitimate patterns like MC25318088, but fix MC25318@88 to MC25318088
    text = re.sub(r'(MC\d+)@(\d)', r'\g<1>0\g<2>', text)  # MC25318@88 -> MC25318088
    
    # 5. Fix @38 patterns (letter O misread as @)
    text = re.sub(r'@([0-9])', r'0\g<1>', text)  # @38 -> 038
    
    # 7. Fix line/sequence numbers that appear wrong
    text = re.sub(r'(LINE:\s*)([68])(\s)', r'\g<1>0\g<3>', text, flags=re.IGNORECASE)  # LINE: 8 -> LINE: 0
    
    return text

# Receipt pattern - captures multi-line format where Qty/Recd is on the next line
# More flexible to handle variations in invoice numbers and packing slips
receipt_pattern = re.compile(
    r'S\s+(MC\d+\S*)\s+(.+?)(\d{1,2}/\d{1,2}/\d{2})\s+(\d{1,2}/\d{1,2}/\d{2})\s+USD\s*(\S*?).*?\n\s*(\d*)\s*([-\d]+)',
    re.MULTILINE | re.IGNORECASE | re.DOTALL
)

for file_name in os.listdir(folder_path):
    if not file_name.lower().endswith((".png", ".jpg", ".jpeg")):
        continue

    # Preprocess image
    preprocessed_img = preprocess_image(os.path.join(folder_path, file_name))
    
    # OCR with aggressive configuration
    # PSM 3 (automatic page segmentation) works best, with OEM 3
    config = '--psm 3 --oem 3 -c tessedit_write_output_file=0'
    text = pytesseract.image_to_string(preprocessed_img, config=config)

    # Normalize spacing
    text = re.sub(r'[ ]{2,}', ' ', text)
    
    # Correct common OCR errors
    text = correct_ocr_errors(text)

    # Extract header information
    div = between(text, 'DIV:', 'PLT:')
    plt = between(text, 'PLT:', 'DOC NO:')
    doc_no = between(text, 'DOC NO:', 'ITEM:')
    item = extract_item_code(text)

    order_qty_match = re.search(r'Order\s*Qty:\s*(\d+)', text, re.IGNORECASE)
    order_qty = extract_order_qty_confident(text) if order_qty_match else None

    # Extract receipt rows
    matches = receipt_pattern.findall(text)

    for match in matches:
        mc_num, status_info, rec_dt, ship_dt, invoice_num, packing_slip, qty_recd = match
        # Extract status from the middle part (usually OK, PR, @1, 01, 02, 61, 62, etc.)
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

# ---------------- SAVE TO EXCEL ----------------
df = pd.DataFrame(rows)
output_excel = os.path.join(folder_path, "OCR_Extracted.xlsx")

# Save with adjusted column widths
with pd.ExcelWriter(output_excel, engine='openpyxl') as writer:
    # Sheet 1: Original data with all rows
    df.to_excel(writer, index=False, sheet_name='Sheet1')
    
    # Sheet 2: Summary data with duplicates removed and Qty/Recd summed
    # Group by columns A-F (File Name, DIV, PLT, DOC NO, ITEM, Order Qty)
    summary_df = df.groupby(['File Name', 'DIV', 'PLT', 'DOC NO', 'ITEM', 'Order Qty'], as_index=False).agg({
        'Qty/Recd': lambda x: pd.to_numeric(x, errors='coerce').sum()
    })
    # Convert Qty/Recd to int for cleaner display
    summary_df['Qty/Recd'] = summary_df['Qty/Recd'].astype('Int64')  # Use Int64 to handle NaN if needed
    
    summary_df.to_excel(writer, index=False, sheet_name='Summary')
    
    # Adjust column widths for Sheet1
    worksheet = writer.sheets['Sheet1']
    column_widths = {
        'A': 18,  # File Name
        'B': 8,   # DIV
        'C': 8,   # PLT
        'D': 20,  # DOC NO
        'E': 20,  # ITEM
        'F': 12,  # Order Qty
        'G': 15,  # MC/PA Number
        'H': 10,  # Status
        'I': 12,  # Rec Dt
        'J': 12,  # Ship Dt
        'K': 12,  # Qty/Recd
        'L': 20   # Timestamp
    }
    for col, width in column_widths.items():
        worksheet.column_dimensions[col].width = width
    
    # Adjust column widths for Summary sheet
    worksheet = writer.sheets['Summary']
    column_widths_summary = {
        'A': 18,  # File Name
        'B': 8,   # DIV
        'C': 8,   # PLT
        'D': 20,  # DOC NO
        'E': 20,  # ITEM
        'F': 12,  # Order Qty
        'G': 12   # Qty/Recd (sum)
    }
    for col, width in column_widths_summary.items():
        worksheet.column_dimensions[col].width = width

print(f"Extraction complete. {len(df)} rows saved to {output_excel}")
print(f"Summary sheet created with {len(summary_df)} unique combinations")
