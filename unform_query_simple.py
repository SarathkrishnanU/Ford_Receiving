"""
UnForm Query Automation Script (Simplified)
Runs document query with values from Excel
Works with already-logged-in browser session
"""

import openpyxl
import time

def get_value_from_excel(file_path, sheet_name='Input', cell='A2'):
    """
    Read value from Excel file
    
    Args:
        file_path: Path to Excel file
        sheet_name: Name of the sheet
        cell: Cell reference (e.g., 'A2', 'B2')
    
    Returns:
        Value from the specified cell
    """
    try:
        workbook = openpyxl.load_workbook(file_path)
        sheet = workbook[sheet_name]
        value = sheet[cell].value
        workbook.close()
        return value
    except Exception as e:
        print(f"Error reading Excel: {e}")
        return None

def main():
    """
    Main automation function
    Reads Excel values and prints automation steps
    """
    
    # Configuration
    excel_path = r'C:\Users\skrishnan1\Videos\Proj\Unform Input Excel.xlsx'
    
    # Read values from Excel
    print("Reading values from Excel...")
    company_value = get_value_from_excel(excel_path, 'Input', 'A2')
    order_number = get_value_from_excel(excel_path, 'Input', 'B2')
    print(f"✓ Company: {company_value}")
    print(f"✓ Order Number: {order_number}")
    
    print("\n" + "="*60)
    print("AUTOMATION STEPS:")
    print("="*60)
    
    steps = [
        f"1. Company: Select '{company_value}' from Company dropdown",
        f"2. Library: Select 'OE - Order Entry' from Library dropdown",
        f"3. Document Type: Select 'OE Customer Invoice'",
        f"4. Order #: Enter '{order_number}'",
        f"5. Click 'Run' button to execute query"
    ]
    
    for step in steps:
        print(step)
    
    print("\n" + "="*60)
    print("✓ Browser Automation Instructions Complete")
    print("="*60)

if __name__ == "__main__":
    main()
