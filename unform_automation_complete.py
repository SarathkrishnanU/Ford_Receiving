"""
UnForm Automation Script
Automates the UnForm Archiving process with Excel integration
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
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

def login_to_unform(driver, url, username, password):
    """
    Login to UnForm with credentials
    
    Args:
        driver: Selenium webdriver instance
        url: UnForm login URL
        username: Username
        password: Password
    """
    print("Step 1: Opening UnForm login page...")
    driver.get(url)
    time.sleep(3)
    
    print("Step 2: Logging in...")
    try:
        # Find username field by any text input or by name attribute
        username_field = driver.find_element(By.XPATH, "//input[contains(@placeholder, 'username') or @name='username'] | //input[@type='text'][1]")
        password_field = driver.find_element(By.XPATH, "//input[@type='password']")
        
        # Clear fields first
        username_field.clear()
        password_field.clear()
        
        username_field.send_keys(username)
        password_field.send_keys(password)
        
        # Click Login button
        login_button = driver.find_element(By.XPATH, "//button[text()='Login']")
        login_button.click()
        time.sleep(5)
        print("✓ Login successful")
        
    except Exception as e:
        print(f"Login error: {e}")
        raise

def select_company(driver, company_value):
    """
    Select company from dropdown
    
    Args:
        driver: Selenium webdriver instance
        company_value: Company code to select (e.g., 'Co 0001')
    """
    print(f"Step 3: Selecting company: {company_value}...")
    try:
        wait = WebDriverWait(driver, 10)
        
        # Wait for iframe to be present
        iframe = wait.until(EC.presence_of_element_located((By.TAG_NAME, "iframe")))
        driver.switch_to.frame(iframe)
        
        # Find and select company dropdown
        company_dropdown = wait.until(EC.presence_of_element_located((By.ID, "company")))
        select = Select(company_dropdown)
        select.select_by_value(company_value)
        
        driver.switch_to.default_content()
        time.sleep(1)
        print(f"✓ Company {company_value} selected")
        
    except Exception as e:
        print(f"Error selecting company: {e}")
        raise

def select_library(driver, library_value):
    """
    Select library from dropdown
    
    Args:
        driver: Selenium webdriver instance
        library_value: Library name (e.g., 'OE - Order Entry')
    """
    print(f"Step 4: Selecting library: {library_value}...")
    try:
        wait = WebDriverWait(driver, 10)
        
        # Get all iframes
        iframes = driver.find_elements(By.TAG_NAME, "iframe")
        if len(iframes) > 0:
            driver.switch_to.frame(iframes[0])
            
            # Find all select elements (company is 1st, library is 2nd)
            library_dropdown = wait.until(EC.presence_of_all_elements_located((By.TAG_NAME, "select")))[1]
            select = Select(library_dropdown)
            select.select_by_visible_text(library_value)
            
            driver.switch_to.default_content()
            time.sleep(1)
            print(f"✓ Library {library_value} selected")
            
    except Exception as e:
        print(f"Error selecting library: {e}")
        raise

def select_document_type(driver, document_type):
    """
    Select document type from listbox
    
    Args:
        driver: Selenium webdriver instance
        document_type: Document type to select (e.g., 'OE Customer Invoice')
    """
    print(f"Step 5: Selecting document type: {document_type}...")
    try:
        wait = WebDriverWait(driver, 10)
        
        # Switch to iframe
        iframes = driver.find_elements(By.TAG_NAME, "iframe")
        if len(iframes) > 0:
            driver.switch_to.frame(iframes[0])
            
            # Find listbox and select option
            listbox = wait.until(EC.presence_of_element_located((By.TAG_NAME, "listbox")))
            option = driver.find_element(By.XPATH, f"//option[contains(text(), '{document_type}')]")
            driver.execute_script("arguments[0].selected = true;", option)
            driver.execute_script("arguments[0].dispatchEvent(new Event('change', { bubbles: true }));", option)
            
            driver.switch_to.default_content()
            time.sleep(1)
            print(f"✓ Document type {document_type} selected")
            
    except Exception as e:
        print(f"Error selecting document type: {e}")
        raise

def enter_order_number(driver, order_number):
    """
    Enter order number in the search field
    
    Args:
        driver: Selenium webdriver instance
        order_number: Order number to search
    """
    print(f"Step 6: Entering order number: {order_number}...")
    try:
        wait = WebDriverWait(driver, 10)
        
        # Switch to iframe
        iframes = driver.find_elements(By.TAG_NAME, "iframe")
        if len(iframes) > 0:
            driver.switch_to.frame(iframes[0])
            
            # Find all inputs and locate the order number field (usually the 4th text input)
            inputs = driver.find_elements(By.TAG_NAME, "input")
            if len(inputs) >= 4:
                inputs[3].clear()
                inputs[3].send_keys(str(order_number))
            
            driver.switch_to.default_content()
            time.sleep(1)
            print(f"✓ Order number {order_number} entered")
            
    except Exception as e:
        print(f"Error entering order number: {e}")
        raise

def click_run_button(driver):
    """
    Click the Run button to execute the query
    
    Args:
        driver: Selenium webdriver instance
    """
    print("Step 7: Clicking Run button...")
    try:
        wait = WebDriverWait(driver, 10)
        
        # Switch to iframe
        iframes = driver.find_elements(By.TAG_NAME, "iframe")
        if len(iframes) > 0:
            driver.switch_to.frame(iframes[0])
            
            # Find and click Run button
            run_button = wait.until(EC.presence_of_element_located((By.XPATH, "//button[contains(text(), 'Run')]")))
            run_button.click()
            
            driver.switch_to.default_content()
            time.sleep(3)
            print("✓ Run button clicked")
            
    except Exception as e:
        print(f"Error clicking Run button: {e}")
        raise

def main():
    """
    Main automation function
    """
    # Configuration
    url = 'https://documentstorage.theegc.com:27392/arc'
    username = r'psmi\skrishnan1'
    password = 'Krishna071$$$'
    excel_path = r'C:\Users\skrishnan1\Videos\Proj\Unform Input Excel.xlsx'
    
    # Initialize Chrome driver
    driver = webdriver.Chrome()
    
    try:
        # Step 1: Login
        login_to_unform(driver, url, username, password)
        
        # Step 2: Read values from Excel
        print("\nStep 2: Reading values from Excel...")
        company_value = get_value_from_excel(excel_path, 'Input', 'A2')
        order_number = get_value_from_excel(excel_path, 'Input', 'B2')
        print(f"✓ Company: {company_value}")
        print(f"✓ Order Number: {order_number}")
        
        # Step 3: Select company
        select_company(driver, company_value)
        
        # Step 4: Select library
        select_library(driver, 'OE - Order Entry')
        
        # Step 5: Select document type
        select_document_type(driver, 'OE Customer Invoice')
        
        # Step 6: Enter order number
        enter_order_number(driver, order_number)
        
        # Step 7: Click Run button
        click_run_button(driver)
        
        print("\n" + "="*50)
        print("✓ Automation completed successfully!")
        print("="*50)
        
        # Keep browser open to see results
        time.sleep(10)
        
    except Exception as e:
        print(f"\n✗ Error occurred: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        # Close the browser (comment out to keep it open)
        # driver.quit()
        pass

if __name__ == "__main__":
    main()
