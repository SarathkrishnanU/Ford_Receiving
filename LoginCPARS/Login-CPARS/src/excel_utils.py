import openpyxl
import time
import logging
from src.terminal_utils import send_terminal_text, press_terminal_enter

logger = logging.getLogger(__name__)

def paste_excel_values_to_terminal(driver, excel_path, sheet_name):
    """
    Reads values from an Excel file and pastes them into the terminal.

    Args:
        driver: Selenium WebDriver instance.
        excel_path: Path to the Excel file.
        sheet_name: Name of the sheet to read data from.
    """
    try:
        # Load the workbook and select the sheet
        workbook = openpyxl.load_workbook(excel_path)
        sheet = workbook[sheet_name]

        # Iterate through rows, starting from the second row (skipping header)
        for row in sheet.iter_rows(min_row=2, values_only=True):
            # Assuming columns D, E, F (index 3, 4, 5) contain the data
            values = row[3:6]  # Adjust indices if needed

            for value in values:
                if value is not None:
                    send_terminal_text(driver, str(value))
                    time.sleep(0.5)  # Small delay between inputs

            # Press ENTER after each row
            press_terminal_enter(driver)
            time.sleep(1)  # Delay to allow terminal to process

        logger.info("Excel values pasted into terminal successfully.")

    except Exception as e:
        logger.error(f"Failed to paste Excel values to terminal: {str(e)}", exc_info=True)
        raise