import os
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from PIL import Image
import pytesseract
import pandas as pd

# ---------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------
URL = "https://www.berkshirehathaway.com/"
SCREENSHOT_FOLDER = r"C:\Users\skrishnan1\Videos\Ford Project Test"
EXCEL_OUTPUT = r"C:\Users\skrishnan1\Videos\Ford Project Test\Extracted_Data.xlsx"

# Path to Tesseract executable
pytesseract.pytesseract.tesseract_cmd = r"C:\Users\skrishnan1\AppData\Local\Programs\Tesseract-OCR\tesseract.exe"

# Create folder if not exists
os.makedirs(SCREENSHOT_FOLDER, exist_ok=True)

# ---------------------------------------------------
# STEP 1: OPEN URL & TAKE SCREENSHOT
# ---------------------------------------------------
chrome_options = Options()
chrome_options.add_argument("--start-maximized")

driver = webdriver.Chrome(options=chrome_options)
driver.get(URL)

time.sleep(5)  # Allow page to fully load

screenshot_path = os.path.join(
    SCREENSHOT_FOLDER, "berkshire_hathaway_screenshot.png"
)
driver.save_screenshot(screenshot_path)

driver.quit()

print("Screenshot saved:", screenshot_path)

# ---------------------------------------------------
# STEP 2: READ SCREENSHOTS & EXTRACT TEXT
# ---------------------------------------------------
extracted_data = []

for file_name in os.listdir(SCREENSHOT_FOLDER):
    if file_name.lower().endswith((".png", ".jpg", ".jpeg")):
        image_path = os.path.join(SCREENSHOT_FOLDER, file_name)

        image = Image.open(image_path)
        extracted_text = pytesseract.image_to_string(image)

        extracted_data.append({
            "Screenshot Name": file_name,
            "Extracted Text": extracted_text.strip()
        })

# ---------------------------------------------------
# STEP 3: SAVE TO EXCEL
# ---------------------------------------------------
df = pd.DataFrame(extracted_data)
df.to_excel(EXCEL_OUTPUT, index=False)

print("Excel file created:", EXCEL_OUTPUT)
