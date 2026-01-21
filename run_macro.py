import os
import sys
import traceback
import win32com.client

EXCEL_FILE_PATH = r"C:\Users\skrishnan1\Videos\Proj\Email Status - Template - V1.6.xlsm"
MACRO_NAME = "ExtractEmailsFromMailbox"


def run_excel_macro():
    excel = None
    try:
        if not os.path.exists(EXCEL_FILE_PATH):
            print(f"Error: File not found: {EXCEL_FILE_PATH}")
            return 1

        excel = win32com.client.DispatchEx('Excel.Application')
        excel.Visible = False  # Run Excel invisibly
        excel.DisplayAlerts = False

        wb = excel.Workbooks.Open(EXCEL_FILE_PATH)
        try:
            excel.Application.Run(f"'{os.path.basename(EXCEL_FILE_PATH)}'!{MACRO_NAME}")
            print(f"Macro '{MACRO_NAME}' executed successfully.")
        except Exception as macro_err:
            print(f"Error running macro '{MACRO_NAME}': {macro_err}")
            wb.Close(SaveChanges=False)
            return 2

        wb.Save()
        wb.Close(SaveChanges=True)
        print("File saved and closed.")
        return 0
    except Exception as e:
        print("An error occurred:")
        traceback.print_exc()
        return 3
    finally:
        if excel:
            excel.Quit()

if __name__ == "__main__":
    sys.exit(run_excel_macro())
