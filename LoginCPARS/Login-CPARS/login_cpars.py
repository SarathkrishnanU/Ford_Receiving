"""
LoginCPARS Automation
FINAL VERSION
IBM HOD IMS5 Automation
"""

import logging
import sys
import time
import os
import openpyxl
import tkinter as tk
from tkinter import filedialog, messagebox

from selenium import webdriver

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains

from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options

from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import InvalidSessionIdException, WebDriverException
from src.terminal_utils import send_terminal_text, press_terminal_enter
from src.excel_utils import paste_excel_values_to_terminal

from dotenv import load_dotenv

# Determine app directory next to the exe (or script during development)
_app_dir = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(_app_dir, '.env'), override=True)

PORTAL_USERNAME   = os.environ.get("PORTAL_USERNAME", "")
PORTAL_PASSWORD   = os.environ.get("PORTAL_PASSWORD", "")
TERMINAL_USERNAME = os.environ.get("TERMINAL_USERNAME", "")
TERMINAL_PASSWORD = os.environ.get("TERMINAL_PASSWORD", "")
CPARS_URL         = os.environ.get("CPARS_URL", "https://fsp.portal.covisint.com/ford_en_US/")


# =========================================================
# LOGGING
# =========================================================
_log_path = os.path.join(_app_dir, 'LoginCPARS.log')

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(_log_path, encoding='utf-8'),
    ]
)

logger = logging.getLogger(__name__)


# The terminal is often inside one specific frame. Once found, reuse it.
TERMINAL_CONTEXT_INDEX = None

# Retry state — set by main() instead of calling itself recursively.
# Handled by the while loop in __main__ so only one browser is ever open.
_pending_retry_state: dict = {}


# =========================================================
# HELPERS
# =========================================================

def click_element(wait, by, locator, description, sleep_time=3):

    try:

        element = wait.until(
            EC.element_to_be_clickable((by, locator))
        )

        logger.info(f"Clicking {description}")

        driver.execute_script(
            """
            arguments[0].scrollIntoView({
                block: 'center'
            });
            """,
            element
        )

        time.sleep(1)

        element.click()

        logger.info(f"{description} clicked")

        time.sleep(sleep_time)

        return True

    except Exception as e:

        logger.error(
            f"Failed clicking {description}: {str(e)}",
            exc_info=True
        )

        return False


def enter_text(wait, by, locator, value, description):

    try:

        element = wait.until(
            EC.presence_of_element_located((by, locator))
        )

        logger.info(f"Entering {description}")

        element.clear()

        element.send_keys(value)

        logger.info(f"{description} entered")

        return True

    except Exception as e:

        logger.error(
            f"Failed entering {description}: {str(e)}",
            exc_info=True
        )

        return False


def _terminal_contexts(driver):

    contexts = [None]

    try:
        contexts.extend(driver.find_elements(By.TAG_NAME, "iframe"))
    except Exception:
        pass

    return contexts


def _ordered_context_indices(contexts):

    global TERMINAL_CONTEXT_INDEX

    indices = list(range(len(contexts)))

    if TERMINAL_CONTEXT_INDEX is None:
        return indices

    if TERMINAL_CONTEXT_INDEX < 0 or TERMINAL_CONTEXT_INDEX >= len(contexts):
        TERMINAL_CONTEXT_INDEX = None
        return indices

    ordered = [TERMINAL_CONTEXT_INDEX]

    for idx in indices:
        if idx != TERMINAL_CONTEXT_INDEX:
            ordered.append(idx)

    return ordered


def _run_in_terminal_context(driver, operation, op_name):

    global TERMINAL_CONTEXT_INDEX

    # Always switch to the latest window before interacting with the terminal
    try:
        driver.switch_to.window(driver.window_handles[-1])
    except Exception as exc:
        logger.debug(f"Could not switch to latest window: {exc}")

    contexts = _terminal_contexts(driver)

    for idx in _ordered_context_indices(contexts):

        frame = contexts[idx]

        try:
            driver.switch_to.default_content()

            if frame is not None:
                driver.switch_to.frame(frame)

            body = WebDriverWait(driver, 8).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )

            if operation(body):
                TERMINAL_CONTEXT_INDEX = idx
                return True

        except Exception as exc:

            logger.debug(f"{op_name} failed in one context: {exc}")

    driver.switch_to.default_content()

    return False


def send_terminal_text(driver, command_text):

    def _type_chars(el):
        for ch in command_text:
            el.send_keys(ch)
            time.sleep(0.25)

    def _op(body):
        strategies = [
            "active",
            "body",
            "action",
            "focus_then_action"
        ]

        for strategy in strategies:
            try:
                if strategy == "active":
                    target = driver.switch_to.active_element
                    if target is None:
                        continue
                    _type_chars(target)
                    return True

                if strategy == "body":
                    _type_chars(body)
                    return True

                if strategy == "action":
                    ActionChains(driver).send_keys(command_text).perform()
                    return True

                # Last resort: click body to force focus, then send keys globally.
                body.click()
                time.sleep(0.2)
                ActionChains(driver).send_keys(command_text).perform()
                return True

            except Exception as exc:
                logger.debug(f"Text strategy {strategy} failed: {exc}")

        return False

    if _run_in_terminal_context(driver, _op, "Typing terminal text"):
        logger.info(f"Text typed in terminal: {command_text}")
        return True

    return False


def press_terminal_enter(driver):

    def _op(body):
        strategies = [
            "active",
            "body",
            "action",
            "focus_then_action"
        ]

        for strategy in strategies:
            try:
                if strategy == "active":
                    target = driver.switch_to.active_element
                    if target is None:
                        continue
                    target.send_keys(Keys.ENTER)
                    return True

                if strategy == "body":
                    body.send_keys(Keys.ENTER)
                    return True

                if strategy == "action":
                    ActionChains(driver).send_keys(Keys.ENTER).perform()
                    return True

                body.click()
                time.sleep(0.2)
                ActionChains(driver).send_keys(Keys.ENTER).perform()
                return True

            except Exception as exc:
                logger.debug(f"ENTER strategy {strategy} failed: {exc}")

        return False

    if _run_in_terminal_context(driver, _op, "Sending ENTER"):
        logger.info("ENTER key sent in terminal")
        return True

    return False


def press_terminal_tab(driver):

    def _op(body):
        strategies = [
            "active",
            "body",
            "action",
            "focus_then_action"
        ]

        for strategy in strategies:
            try:
                if strategy == "active":
                    target = driver.switch_to.active_element
                    if target is None:
                        continue
                    target.send_keys(Keys.TAB)
                    return True

                if strategy == "body":
                    body.send_keys(Keys.TAB)
                    return True

                if strategy == "action":
                    ActionChains(driver).send_keys(Keys.TAB).perform()
                    return True

                body.click()
                time.sleep(0.2)
                ActionChains(driver).send_keys(Keys.TAB).perform()
                return True

            except Exception as exc:
                logger.debug(f"TAB strategy {strategy} failed: {exc}")

        return False

    if _run_in_terminal_context(driver, _op, "Sending TAB"):
        logger.info("TAB key sent in terminal")
        return True

    return False


def press_terminal_backtab(driver):

    def _op(body):
        strategies = [
            "active",
            "body",
            "action",
            "focus_then_action"
        ]

        for strategy in strategies:
            try:
                if strategy == "active":
                    target = driver.switch_to.active_element
                    if target is None:
                        continue
                    target.send_keys(Keys.SHIFT, Keys.TAB)
                    return True

                if strategy == "body":
                    body.send_keys(Keys.SHIFT, Keys.TAB)
                    return True

                if strategy == "action":
                    ActionChains(driver).key_down(Keys.SHIFT).send_keys(Keys.TAB).key_up(Keys.SHIFT).perform()
                    return True

                body.click()
                time.sleep(0.2)
                ActionChains(driver).key_down(Keys.SHIFT).send_keys(Keys.TAB).key_up(Keys.SHIFT).perform()
                return True

            except Exception as exc:
                logger.debug(f"BACKTAB strategy {strategy} failed: {exc}")

        return False

    if _run_in_terminal_context(driver, _op, "Sending BACKTAB"):
        logger.info("BACKTAB key sent in terminal")
        return True

    return False


def press_terminal_down_arrow(driver):

    def _op(body):
        strategies = [
            "active",
            "body",
            "action",
            "focus_then_action"
        ]

        for strategy in strategies:
            try:
                if strategy == "active":
                    target = driver.switch_to.active_element
                    if target is None:
                        continue
                    target.send_keys(Keys.ARROW_DOWN)
                    return True

                if strategy == "body":
                    body.send_keys(Keys.ARROW_DOWN)
                    return True

                if strategy == "action":
                    ActionChains(driver).send_keys(Keys.ARROW_DOWN).perform()
                    return True

                body.click()
                time.sleep(0.2)
                ActionChains(driver).send_keys(Keys.ARROW_DOWN).perform()
                return True

            except Exception as exc:
                logger.debug(f"DOWN ARROW strategy {strategy} failed: {exc}")

        return False

    if _run_in_terminal_context(driver, _op, "Sending DOWN ARROW"):
        logger.info("DOWN ARROW key sent in terminal")
        return True

    return False


def press_terminal_right_arrow(driver):

    def _op(body):
        strategies = [
            "active",
            "body",
            "action",
            "focus_then_action"
        ]

        for strategy in strategies:
            try:
                if strategy == "active":
                    target = driver.switch_to.active_element
                    if target is None:
                        continue
                    target.send_keys(Keys.ARROW_RIGHT)
                    return True

                if strategy == "body":
                    body.send_keys(Keys.ARROW_RIGHT)
                    return True

                if strategy == "action":
                    ActionChains(driver).send_keys(Keys.ARROW_RIGHT).perform()
                    return True

                body.click()
                time.sleep(0.2)
                ActionChains(driver).send_keys(Keys.ARROW_RIGHT).perform()
                return True

            except Exception as exc:
                logger.debug(f"RIGHT ARROW strategy {strategy} failed: {exc}")

        return False

    if _run_in_terminal_context(driver, _op, "Sending RIGHT ARROW"):
        logger.info("RIGHT ARROW key sent in terminal")
        return True

    return False


def send_terminal_credentials(driver, username, password):

    # Give the terminal login screen a moment to settle before typing credentials.
    time.sleep(2)

    logger.info("Sending terminal user id")

    if not send_terminal_text(driver, username):
        raise RuntimeError("Unable to send terminal user id")

    logger.info("Terminal user id entered")

    # Usually the terminal auto-advances to password after user id.
    # If it does not, fallback to TAB before retrying password.
    time.sleep(1)

    logger.info("Sending terminal password")

    if send_terminal_text(driver, password):
        time.sleep(0.7)

        if not press_terminal_enter(driver):
            raise RuntimeError("Unable to press ENTER after terminal password")

        logger.info("Terminal password entered")
        return

    logger.warning(
        "Password entry did not work on first attempt. Trying fallback cursor movement."
    )

    if not press_terminal_tab(driver):
        raise RuntimeError("Unable to move to terminal password field")

    time.sleep(0.7)

    if not send_terminal_text(driver, password):
        raise RuntimeError("Unable to send terminal password after fallback")

    time.sleep(0.7)

    if not press_terminal_enter(driver):
        raise RuntimeError("Unable to press ENTER after terminal password")

    logger.info("Terminal password entered after fallback")


def _terminal_contains_text(driver, text):
    """Return True if the given text is found anywhere in the terminal page."""
    try:
        driver.switch_to.window(driver.window_handles[-1])
    except Exception:
        pass

    # Check main content
    try:
        driver.switch_to.default_content()
        if text in driver.page_source:
            return True
    except Exception:
        pass

    # Check iframes
    try:
        iframes = driver.find_elements(By.TAG_NAME, "iframe")
        for iframe in iframes:
            try:
                driver.switch_to.default_content()
                driver.switch_to.frame(iframe)
                if text in driver.page_source:
                    driver.switch_to.default_content()
                    return True
            except Exception:
                continue
    except Exception:
        pass

    try:
        driver.switch_to.default_content()
    except Exception:
        pass

    return False


def _wait_for_terminal_text(driver, text, timeout=30, poll=1):
    """Poll until text appears in terminal or timeout (seconds) is reached."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        if _terminal_contains_text(driver, text):
            return True
        time.sleep(poll)
    return False


def _fatal_stop(message):
    """Show error messagebox, quit browser, and exit immediately — no retry."""
    global driver
    logger.error(f"Fatal stop: {message}")
    try:
        if driver is not None:
            driver.quit()
            driver = None
    except Exception:
        pass
    root = tk.Tk()
    root.withdraw()
    messagebox.showerror("Processing Stopped", message)
    root.destroy()
    sys.exit(1)


def _has_uncompleted_rows(excel_path, sheet_name="Sheet1"):
    """Return True if any row in the workbook is not yet marked Completed."""
    try:
        wb = openpyxl.load_workbook(excel_path)
        sheet = wb[sheet_name]
        for row in sheet.iter_rows(min_row=2):
            if row[0].value is not None:
                status = row[6].value if len(row) > 6 else None
                if status != "Completed":
                    logger.info(f"Uncompleted row found: {row[0].value}")
                    return True
        logger.info("All rows in Excel are marked Completed.")
        return False
    except Exception as e:
        logger.warning(f"Could not read Excel to check completion status: {e} — assuming rows need processing.")
        return True  # Assume there is work to do if the file can't be read


# =========================================================
# MAIN
# =========================================================

def main(_excel_path=None, _output_dir=None, _attempt=1, _max_retries=25):
    global driver

    logger.info(f"main() called — attempt {_attempt}, excel={_excel_path}, output_dir={_output_dir}")

    if _attempt > 1:
        logger.info(f"--- Retry attempt {_attempt}/{_max_retries} ---")

    # =====================================================
    # BROWSE FOR EXCEL INPUT FILE
    # =====================================================

    if _excel_path is None:
        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)

        _excel_path = filedialog.askopenfilename(
            title="Select Excel Input File",
            filetypes=[("Excel files", "*.xlsx *.xls"), ("All files", "*.*")],
            initialdir=r"C:\Users\skrishnan1\Videos\Proj\LoginCPARS\Login-CPARS\Input"
        )

        if not _excel_path:
            messagebox.showerror("No File Selected", "No Excel file was selected. Exiting.", parent=root)
            root.destroy()
            return

        logger.info(f"Excel file selected: {_excel_path}")

        _output_dir = filedialog.askdirectory(
            title="Select Output Folder for Screenshots",
            initialdir=os.path.dirname(_excel_path)
        )

        if not _output_dir:
            messagebox.showerror("No Folder Selected", "No output folder was selected. Exiting.", parent=root)
            root.destroy()
            return

        logger.info(f"Output folder selected: {_output_dir}")
        root.destroy()

    excel_path = _excel_path
    logger.info(f"Excel input file: {excel_path}")

    # Check upfront — if all rows are already completed, nothing to do
    if not _has_uncompleted_rows(excel_path, "Sheet1"):
        logger.info("All rows already completed — no input to process.")
        messagebox.showinfo("No Input to Process", "No input to process.")
        return

    driver = None
    try:
        chrome_options = Options()
        chrome_options.add_argument("--start-maximized")
        chrome_options.add_argument("--disable-component-update")
        chrome_options.add_argument("--no-first-run")
        chrome_options.add_argument("--no-default-browser-check")
        chrome_options.add_argument("--disable-features=ChromeWhatsNew,BackForwardCache")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option("useAutomationExtension", False)

        logger.info("Launching Chrome...")
        driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=chrome_options
        )
        driver.set_page_load_timeout(300)  # 5 minutes for slow portal pages
        logger.info("Chrome launched successfully")

        wait = WebDriverWait(driver, 30)
        # =====================================================
        # OPEN URL
        # =====================================================

        url = CPARS_URL

        logger.info(f"Opening URL: {url}")

        driver.get(url)

        # =====================================================
        # LOGIN
        # =====================================================

        click_element(
            wait,
            By.XPATH,
            "//a[@title='Login']",
            "Login Link"
        )

        enter_text(
            wait,
            By.ID,
            "user",
            PORTAL_USERNAME,
            "Username"
        )

        enter_text(
            wait,
            By.ID,
            "password",
            PORTAL_PASSWORD,
            "Password"
        )

        # =====================================================
        # COOKIE POPUP
        # =====================================================

        try:

            cookie_btn = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable(
                    (
                        By.XPATH,
                        "//button[contains(., 'Accept All')]"
                    )
                )
            )

            cookie_btn.click()

            logger.info("Cookie accepted")

            time.sleep(2)

        except Exception:

            logger.info("No cookie popup")

        # =====================================================
        # SIGN IN
        # =====================================================

        click_element(
            wait,
            By.ID,
            "signon",
            "SIGN IN Button",
            5
        )

        # =====================================================
        # 3270 ACCESS
        # =====================================================

        wait60 = WebDriverWait(driver, 120)
        click_element(
            wait60,
            By.XPATH,
            "//a[@title='3270 Access']",
            "3270 Access",
            5
        )

        # =====================================================
        # SWITCH WINDOW
        # =====================================================

        WebDriverWait(driver, 20).until(
            lambda d: len(d.window_handles) > 1
        )

        driver.switch_to.window(
            driver.window_handles[-1]
        )

        logger.info(
            f"Switched to window: {driver.current_url}"
        )

        time.sleep(5)

        # =====================================================
        # CLICK COVISINT
        # =====================================================

        covisint = wait.until(
            EC.element_to_be_clickable(
                (
                    By.XPATH,
                    "//div[contains(@class,'idp') and contains(@aria-label,'Covisint')]"
                )
            )
        )

        covisint.click()

        logger.info("Covisint clicked")

        time.sleep(8)

        # =====================================================
        # HACPEE 3270 ACCESS
        # =====================================================

        hacpee = wait.until(
            EC.element_to_be_clickable(
                (
                    By.XPATH,
                    "//a[contains(., 'HACPEE 3270 Access')]"
                )
            )
        )

        hacpee.click()

        logger.info("HACPEE clicked")

        time.sleep(8)

        # =====================================================
        # SWITCH WINDOW
        # =====================================================

        driver.switch_to.window(
            driver.window_handles[-1]
        )

        logger.info(
            f"Current URL: {driver.current_url}"
        )

        time.sleep(5)

        # =====================================================
        # HRD COVISINT
        # =====================================================

        hrd_covisint = wait.until(
            EC.element_to_be_clickable(
                (
                    By.XPATH,
                    "//div[contains(@class,'idp') and contains(@aria-label,'Covisint')]"
                )
            )
        )

        hrd_covisint.click()

        logger.info("HRD Covisint clicked")

        time.sleep(8)

        # =====================================================
        # NORTH AMERICA
        # =====================================================

        logger.info("Waiting for North America")

        north_america = wait60.until(
            EC.element_to_be_clickable(
                (
                    By.XPATH,
                    "//*[contains(text(),'North America')]"
                )
            )
        )

        driver.execute_script(
            "arguments[0].scrollIntoView(true);",
            north_america
        )

        time.sleep(2)

        north_america.click()

        logger.info("North America clicked")

        # =====================================================
        # WAIT FOR IBM TERMINAL
        # =====================================================

        logger.info("Waiting for IBM terminal")

        time.sleep(25)

        # =====================================================
        # SWITCH TO ACTIVE WINDOW
        # =====================================================

        driver.switch_to.window(
            driver.window_handles[-1]
        )

        logger.info(
            f"Current URL: {driver.current_url}"
        )

        # =====================================================
        # CLICK TERMINAL AREA
        # =====================================================

        # =====================================================
        # CHECK FOR FAC#A BEFORE SENDING IMS5
        # =====================================================
        time.sleep(4)
        logger.info("Checking terminal for 'FAC#A' before sending IMS5")

        if not _terminal_contains_text(driver, "FAC#A"):
            raise RuntimeError("'FAC#A' not found in terminal — cannot proceed with IMS5")

        logger.info("'FAC#A' confirmed in terminal")

        # =====================================================
        # SEND IMS5
        # =====================================================

        logger.info("Sending IMS5")

        if not send_terminal_text(driver, "IMS5"):
            raise RuntimeError("Unable to focus IBM terminal and send IMS5")

        time.sleep(0.7)

        if not press_terminal_enter(driver):
            raise RuntimeError("Unable to press ENTER after IMS5")

        logger.info("IMS5 entered")

        # After IMS5, terminal may take a few seconds to present the credential input state.
        # =====================================================
        # CHECK FOR 'IMS5  Logon' BEFORE SENDING CREDENTIALS
        # =====================================================

        logger.info("Checking terminal for 'IMS5  Logon' before entering credentials")

        if not _wait_for_terminal_text(driver, "IMS5  Logon", timeout=30):
            raise RuntimeError("'IMS5  Logon' not found in terminal — cannot proceed with credential entry")

        logger.info("'IMS5  Logon' confirmed in terminal")

        # =====================================================
        # SEND USER ID AND PASSWORD IN TERMINAL
        # =====================================================

        send_terminal_credentials(driver, TERMINAL_USERNAME, TERMINAL_PASSWORD)

        # =====================================================
        # ENTER 02 ON NEXT TERMINAL PAGE
        # =====================================================

        logger.info("Waiting for next terminal page after credential submit")

        # =====================================================
        # CHECK FOR 'IMS5  Application Menu' BEFORE ENTERING 02
        # =====================================================

        logger.info("Checking terminal for 'IMS5  Application Menu' before entering 02")

        if not _wait_for_terminal_text(driver, "IMS5  Application Menu", timeout=30):
            raise RuntimeError("'IMS5  Application Menu' not found in terminal — cannot proceed with entering 02")

        logger.info("'IMS5  Application Menu' confirmed in terminal")

        logger.info("Sending terminal code 02")

        if not send_terminal_text(driver, "02"):
            raise RuntimeError("Unable to send terminal code 02")

        time.sleep(3)

        if not press_terminal_enter(driver):
            raise RuntimeError("Unable to press ENTER after terminal code 02")

        logger.info("Terminal code 02 entered")

        # =====================================================
        # CHECK FOR 'CPARS  MASTER  MENU' BEFORE PRESSING F5
        # =====================================================

        logger.info("Checking terminal for 'CPARS  MASTER  MENU' before pressing F5")

        if not _wait_for_terminal_text(driver, "CPARS  MASTER  MENU", timeout=30):
            raise RuntimeError("'CPARS  MASTER  MENU' not found in terminal — cannot proceed with F5")

        logger.info("'CPARS  MASTER  MENU' confirmed in terminal")

        # Add a delay of 3 seconds before pressing F5
        
        logger.info("Sending F5 key to terminal")
        if not send_terminal_text(driver, Keys.F5):
            raise RuntimeError("Unable to send F5 key after terminal code 02")

        # =====================================================
        # CHECK FOR 'CPARS-O-GRAM' BEFORE PRESSING F11
        # =====================================================

        logger.info("Checking terminal for 'CPARS-O-GRAM' before pressing F11")

        if not _wait_for_terminal_text(driver, "CPARS-O-GRAM", timeout=30):
            raise RuntimeError("'CPARS-O-GRAM' not found in terminal — cannot proceed with F11")

        logger.info("'CPARS-O-GRAM' confirmed in terminal")

        # Add a delay of 4 seconds before pressing F11
        
        logger.info("Sending F11 key to terminal")
        if not send_terminal_text(driver, Keys.F11):
            raise RuntimeError("Unable to send F11 key after F5")

        # =====================================================
        # CHECK FOR 'CPARS REQUISITION MENU' BEFORE PRESSING '9'
        # =====================================================

        logger.info("Checking terminal for 'CPARS REQUISITION MENU' before pressing '9'")

        if not _wait_for_terminal_text(driver, "CPARS REQUISITION MENU", timeout=30):
            raise RuntimeError("'CPARS REQUISITION MENU' not found in terminal — cannot proceed with pressing '9'")

        logger.info("'CPARS REQUISITION MENU' confirmed in terminal")

        # Add a delay of 4 seconds before pressing '9'
        
        logger.info("Sending '9' to terminal")
        if not send_terminal_text(driver, "9"):
            raise RuntimeError("Unable to send '9' after F11")
        time.sleep(2)

        logger.info("Pressing ENTER after '9'")
        if not press_terminal_enter(driver):
            raise RuntimeError("Unable to press ENTER after '9'")

        # =====================================================
        # CHECK FOR 'DIVISION ==>' BEFORE SENDING 'B'
        # =====================================================

        logger.info("Checking terminal for 'DIVISION ==>' before sending 'B'")

        if not _wait_for_terminal_text(driver, "DIVISION", timeout=30):
            raise RuntimeError("'DIVISION ==>' not found in terminal — cannot proceed with sending 'B'")

        logger.info("'DIVISION ==>' confirmed in terminal")

        logger.info("Sending 'B' to terminal")
        if not send_terminal_text(driver, "B"):
            raise RuntimeError("Unable to send 'B' after ENTER")
        time.sleep(2)


        logger.info("Sending '00' to terminal")
        if not send_terminal_text(driver, "00"):
            raise RuntimeError("Unable to send '00' after 'B'")
        time.sleep(1)
        logger.info("Pressing ENTER after '00'")
        if not press_terminal_enter(driver):
            raise RuntimeError("Unable to press ENTER after '00'")
        time.sleep(2)

        # Switch to the HOD terminal window after ENTER (find it by URL)
        time.sleep(4)
        try:
            terminal_window = None
            for handle in driver.window_handles:
                try:
                    driver.switch_to.window(handle)
                    if "hodweb3270" in driver.current_url:
                        terminal_window = handle
                        break
                except Exception:
                    continue
            if terminal_window is None:
                # Fallback to last window if terminal not found by URL
                driver.switch_to.window(driver.window_handles[-1])
            logger.info(f"Switched to terminal window after '00' ENTER: {driver.current_url}")
        except (InvalidSessionIdException, WebDriverException) as e:
            logger.error(f"Browser session lost after ENTER on '00': {e}")
            raise
        time.sleep(2)

        # === PASTE EXCEL DATA INTO TERMINAL (D, E, F columns) ===
        sheet_name = "Sheet1"  # Update this sheet name if needed
        from datetime import datetime
        screenshots_dir = _output_dir
        os.makedirs(screenshots_dir, exist_ok=True)
        try:
            workbook = openpyxl.load_workbook(excel_path)
            sheet = workbook[sheet_name]
            status_col = 7  # Column G — status column (after data columns A-F)
            rows_processed = 0
            for row_index, row in enumerate(sheet.iter_rows(min_row=2)):
                col_a_value = str(row[0].value).strip() if row[0].value is not None else "unknown"
                # Skip rows already marked as Completed
                status_cell = sheet.cell(row=row_index + 2, column=status_col)
                if status_cell.value == "Completed":
                    logger.info(f"Skipping row '{col_a_value}' — already Completed")
                    continue
                # Secondary guard: if a screenshot file already exists for this row
                # (e.g. Excel status was not saved due to a locked file on a previous run),
                # mark Completed now and skip to avoid creating a duplicate.
                existing_screenshots = [
                    f for f in os.listdir(screenshots_dir)
                    if f.startswith(col_a_value + "_") and f.lower().endswith(".png")
                ]
                if existing_screenshots:
                    logger.info(
                        f"Screenshot(s) already exist for '{col_a_value}' "
                        f"({existing_screenshots}) — marking Completed and skipping"
                    )
                    status_cell.value = "Completed"
                    try:
                        workbook.save(excel_path)
                        logger.info(f"Row '{col_a_value}' marked as Completed in Excel (screenshot existed)")
                    except Exception as save_exc:
                        logger.warning(f"Could not save Completed status for '{col_a_value}': {save_exc}")
                    continue
                values = (row[3].value, row[4].value, row[5].value)  # Columns D, E, F
                try:
                    # Position cursor: BACKTAB×2 for the first row being processed this run,
                    # DOWN+RIGHT for every subsequent row (regardless of Excel row index).
                    if rows_processed == 0:
                        logger.info("Positioning cursor with BACKTAB×2 for first processed row")
                        if not press_terminal_backtab(driver):
                            raise RuntimeError("Unable to position cursor to first input field (BACKTAB 1)")
                        if not press_terminal_backtab(driver):
                            raise RuntimeError("Unable to position cursor to first input field (BACKTAB 2)")
                    else:
                        logger.info("Positioning cursor with DOWN+RIGHT for next row")
                        if not press_terminal_down_arrow(driver):
                            raise RuntimeError("Unable to send DOWN ARROW to position cursor")
                        if not press_terminal_right_arrow(driver):
                            raise RuntimeError("Unable to send RIGHT ARROW to position cursor")
                    time.sleep(2)
                    for value in values:
                        if value is not None:
                            send_terminal_text(driver, str(value))
                            time.sleep(5)
                            # Verify the typed value appears in the terminal
                            if _terminal_contains_text(driver, str(value)):
                                logger.info(f"Verified value '{value}' is visible in terminal")
                            else:
                                logger.warning(f"Value '{value}' NOT found in terminal after typing - cursor may be in wrong position")
                    press_terminal_enter(driver)
                    time.sleep(2)  # Wait for terminal to display result

                    # Check for error message after ENTER
                    if _terminal_contains_text(driver, "DOCUMENT NOT ON FILE"):
                        raise RuntimeError(f"'DOCUMENT NOT ON FILE' displayed in terminal for row '{col_a_value}' — stopping run")

                    if _terminal_contains_text(driver, "PLEASE INQUIRE BEFORE PAGING FORWARD"):
                        raise RuntimeError(f"'PLEASE INQUIRE BEFORE PAGING FORWARD' on initial page for row '{col_a_value}' — closing and restarting")

                    if _terminal_contains_text(driver, "INVALID COMMAND"):
                        raise RuntimeError(f"'INVALID COMMAND' displayed in terminal for row '{col_a_value}' — closing and restarting")

                    logger.info(f"'DOCUMENT NOT ON FILE' not detected — proceeding with screenshot for row '{col_a_value}'")

                    # Take screenshot named after Column A value
                    screenshot_taken = False

                    # Validate correct screen is shown before taking screenshot
                    if not (_terminal_contains_text(driver, "CCAPS Payment Approval / Receipt History") or
                            _terminal_contains_text(driver, "CPARS Receipt History")):
                        raise RuntimeError(
                            f"Expected screen not found for row '{col_a_value}' — "
                            f"neither 'CCAPS Payment Approval / Receipt History' nor 'CPARS Receipt History' "
                            f"is visible in terminal — closing and restarting"
                        )

                    logger.info(f"Screen validated — proceeding with screenshot for row '{col_a_value}'")

                    screenshot_name = f"{col_a_value}_{datetime.now().strftime('%Y%m%d')}.png"
                    screenshot_path = os.path.join(screenshots_dir, screenshot_name)

                    # Crop to just the black terminal area using Pillow
                    from PIL import Image, ImageChops
                    import io
                    import hashlib
                    png_bytes = driver.get_screenshot_as_png()
                    img = Image.open(io.BytesIO(png_bytes)).convert("RGB")
                    width, height = img.size

                    # Scan rows/cols to find the bounding box of the black terminal area
                    # Black terminal pixels are very dark (R+G+B < 30 threshold per channel)
                    pixels = img.load()
                    min_x, min_y, max_x, max_y = width, height, 0, 0
                    for y in range(height):
                        for x in range(width):
                            r, g, b = pixels[x, y]
                            if r < 30 and g < 30 and b < 30:
                                min_x = min(min_x, x)
                                min_y = min(min_y, y)
                                max_x = max(max_x, x)
                                max_y = max(max_y, y)

                    if max_x > min_x and max_y > min_y:
                        cropped = img.crop((min_x, min_y, max_x + 1, max_y + 1))
                    else:
                        # Fallback: save full screenshot if black area not detected
                        cropped = img

                    cropped.save(screenshot_path)
                    screenshot_taken = True
                    logger.info(f"Screenshot saved: {screenshot_path}")
                    # Hash raw pixel bytes — PNG compression is non-deterministic
                    # so hashing PNG bytes can differ for identical pixel content.
                    last_page_hash = hashlib.md5(cropped.tobytes()).hexdigest()
                    del png_bytes, img, cropped
                    rows_processed += 1

                    # Press F8 to page forward and capture additional pages
                    page_num = 1
                    while True:
                        try:
                            if not send_terminal_text(driver, Keys.F8):
                                logger.warning("Unable to send F8 key for paging")
                                break
                            time.sleep(2)

                            # Check BEFORE taking screenshot — stop if no more pages
                            if _terminal_contains_text(driver, "PAGING FORWARD INVALID"):
                                logger.info(f"'PAGING FORWARD INVALID' — no more pages for row '{col_a_value}', marking Completed")
                                if status_cell.value != "Completed":
                                    status_cell.value = "Completed"
                                    try:
                                        workbook.save(excel_path)
                                        logger.info(f"Row '{col_a_value}' marked as Completed in Excel")
                                    except Exception as save_exc:
                                        logger.warning(f"Could not save Completed status for row '{col_a_value}': {save_exc}")
                                break

                            # Stop paging if terminal says to inquire before paging forward
                            if _terminal_contains_text(driver, "PLEASE INQUIRE BEFORE PAGING FORWARD"):
                                raise RuntimeError(f"'PLEASE INQUIRE BEFORE PAGING FORWARD' after page {page_num} for row '{col_a_value}' — closing and restarting")

                            screenshot_name_paged = f"{col_a_value}_{datetime.now().strftime('%Y%m%d')}-{page_num}.png"
                            screenshot_path_paged = os.path.join(screenshots_dir, screenshot_name_paged)

                            png_bytes_paged = driver.get_screenshot_as_png()
                            img_paged = Image.open(io.BytesIO(png_bytes_paged)).convert("RGB")
                            width_p, height_p = img_paged.size
                            pixels_p = img_paged.load()
                            min_xp, min_yp, max_xp, max_yp = width_p, height_p, 0, 0
                            for yp in range(height_p):
                                for xp in range(width_p):
                                    rp, gp, bp = pixels_p[xp, yp]
                                    if rp < 30 and gp < 30 and bp < 30:
                                        min_xp = min(min_xp, xp)
                                        min_yp = min(min_yp, yp)
                                        max_xp = max(max_xp, xp)
                                        max_yp = max(max_yp, yp)

                            if max_xp > min_xp and max_yp > min_yp:
                                cropped_paged = img_paged.crop((min_xp, min_yp, max_xp + 1, max_yp + 1))
                            else:
                                cropped_paged = img_paged

                            # Hash raw pixel bytes for reliable duplicate detection
                            new_page_hash = hashlib.md5(cropped_paged.tobytes()).hexdigest()

                            if new_page_hash == last_page_hash:
                                logger.info("Duplicate page detected after F8 — stopping paging for this row")
                                status_cell.value = "Completed"
                                try:
                                    workbook.save(excel_path)
                                    logger.info(f"Row '{col_a_value}' marked as Completed in Excel")
                                except Exception as save_exc:
                                    logger.warning(f"Could not save Completed status for row '{col_a_value}' (close Excel and retry): {save_exc}")
                                del png_bytes_paged, img_paged, cropped_paged
                                break
                            last_page_hash = new_page_hash
                            cropped_paged.save(screenshot_path_paged)
                            logger.info(f"Paged screenshot saved: {screenshot_path_paged}")
                            del png_bytes_paged, img_paged, cropped_paged

                            # Post-save safety: DOM sometimes lags behind the visual render,
                            # so "PAGING FORWARD INVALID" may only appear in page_source AFTER
                            # the screenshot was already taken. Delete the spurious file here.
                            if _terminal_contains_text(driver, "PAGING FORWARD INVALID"):
                                logger.info(f"'PAGING FORWARD INVALID' detected after saving page {page_num} — removing spurious screenshot")
                                try:
                                    os.remove(screenshot_path_paged)
                                    logger.info(f"Removed spurious screenshot: {screenshot_path_paged}")
                                except Exception as del_exc:
                                    logger.warning(f"Could not delete spurious screenshot: {del_exc}")
                                status_cell.value = "Completed"
                                try:
                                    workbook.save(excel_path)
                                    logger.info(f"Row '{col_a_value}' marked as Completed in Excel")
                                except Exception as save_exc:
                                    logger.warning(f"Could not save Completed status: {save_exc}")
                                break

                            page_num += 1
                        except InvalidSessionIdException:
                            logger.warning(f"Browser session lost during F8 paging at page {page_num} - stopping paging for row '{col_a_value}'")
                            raise

                    # Guarantee the row is marked Completed after the paging loop
                    # regardless of which break path was taken (including the
                    # "send_terminal_text F8 returned False" path which previously
                    # exited without saving the status, causing duplicates on restart).
                    if screenshot_taken and status_cell.value != "Completed":
                        status_cell.value = "Completed"
                        try:
                            workbook.save(excel_path)
                            logger.info(f"Row '{col_a_value}' marked as Completed in Excel")
                        except Exception as save_exc:
                            logger.warning(f"Could not save Completed status for row '{col_a_value}': {save_exc}")

                    logger.info(f"Row '{col_a_value}' completed successfully.")

                except InvalidSessionIdException:
                    logger.error(f"Browser session lost while processing row '{col_a_value}' - stopping all remaining rows")
                    if screenshot_taken and status_cell.value != "Completed":
                        status_cell.value = "Completed"
                        try:
                            workbook.save(excel_path)
                            logger.info(f"Row '{col_a_value}' marked as Completed before stopping (screenshot was taken)")
                        except Exception as save_exc:
                            logger.warning(f"Could not save Completed status for row '{col_a_value}': {save_exc}")
                    raise  # Browser is dead; cannot continue with more rows
                except RuntimeError:
                    if screenshot_taken and status_cell.value != "Completed":
                        status_cell.value = "Completed"
                        try:
                            workbook.save(excel_path)
                            logger.info(f"Row '{col_a_value}' marked as Completed before stopping (screenshot was taken)")
                        except Exception as save_exc:
                            logger.warning(f"Could not save Completed status for row '{col_a_value}': {save_exc}")
                    raise  # Fatal terminal errors — stop run and trigger retry
                except Exception as row_exc:
                    logger.error(f"Error processing row '{col_a_value}': {row_exc}", exc_info=True)
                    # Continue to next row for non-fatal errors

            logger.info("Excel values pasted into terminal successfully.")
        except InvalidSessionIdException:
            logger.error("Browser session lost - automation stopped early")
            raise
        except Exception as e:
            logger.error(f"Failed to paste Excel values to terminal: {str(e)}", exc_info=True)
            raise

        # =====================================================
        # RUN OCR
        # =====================================================

        from src.ocr_runner import run_ocr
        logger.info("Running OCR extraction")
        try:
            run_ocr(_output_dir)
            logger.info("OCR extraction completed successfully")
        except Exception as ocr_exc:
            logger.error(f"OCR extraction failed: {ocr_exc}", exc_info=True)

        logger.info("Automation completed successfully")
        messagebox.showinfo("Automation Complete", "Automation Completed.")

        # =====================================================
        # KEEP OPEN
        # =====================================================

        while True:
            time.sleep(1)

    except Exception as e:

        logger.error(
            f"Automation failed: {str(e)}",
            exc_info=True
        )
        logger.info(f"See log file for details: {_log_path}")

        # Close the browser before retrying
        if driver is not None:
            try:
                driver.quit()
            except Exception:
                pass
            driver = None

        # Retry if there are uncompleted rows and attempts remain
        if _has_uncompleted_rows(excel_path, "Sheet1") and _attempt < _max_retries:
            logger.info(f"Restarting automation in 3 seconds (attempt {_attempt + 1}/{_max_retries})...")
            time.sleep(3)
            # Schedule retry via module-level state — the while loop in __main__
            # will call main() again so this call returns cleanly (no recursion).
            _pending_retry_state['retry'] = True
            _pending_retry_state['excel_path'] = excel_path
            _pending_retry_state['output_dir'] = _output_dir
            _pending_retry_state['attempt'] = _attempt + 1
            _pending_retry_state['max_retries'] = _max_retries
        elif not _has_uncompleted_rows(excel_path, "Sheet1"):
            # All rows completed — the error was on the last row but everything is done.
            # Run OCR and show success instead of the failure message.
            logger.info("All rows are Completed — running OCR and showing success.")
            try:
                from src.ocr_runner import run_ocr
                run_ocr(_output_dir)
                logger.info("OCR extraction completed successfully")
            except Exception as ocr_exc:
                logger.error(f"OCR extraction failed: {ocr_exc}", exc_info=True)
            messagebox.showinfo("Automation Complete", "Automation Completed.")
        else:
            if _attempt >= _max_retries:
                logger.error(f"Maximum retries ({_max_retries}) reached.")
            input("\nAutomation failed. Press Enter to close...")

    finally:

        logger.info("Script finished")
        # driver.quit()


if __name__ == "__main__":

    _excel_path_arg = None
    _output_dir_arg = None
    _attempt_arg = 1
    _max_retries_arg = 25

    while True:
        _pending_retry_state.clear()
        main(
            _excel_path=_excel_path_arg,
            _output_dir=_output_dir_arg,
            _attempt=_attempt_arg,
            _max_retries=_max_retries_arg,
        )
        if _pending_retry_state.get('retry'):
            _excel_path_arg = _pending_retry_state['excel_path']
            _output_dir_arg = _pending_retry_state['output_dir']
            _attempt_arg = _pending_retry_state['attempt']
            _max_retries_arg = _pending_retry_state['max_retries']
        else:
            break