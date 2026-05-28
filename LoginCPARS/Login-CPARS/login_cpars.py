"""
LoginCPARS Automation
FINAL VERSION
IBM HOD IMS5 Automation
"""

import logging
import time
import os
import openpyxl

from selenium import webdriver

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains

from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options

from webdriver_manager.chrome import ChromeDriverManager
from src.terminal_utils import send_terminal_text, press_terminal_enter
from src.excel_utils import paste_excel_values_to_terminal


# =========================================================
# LOGGING
# =========================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


# The terminal is often inside one specific frame. Once found, reuse it.
TERMINAL_CONTEXT_INDEX = None


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


# =========================================================
# MAIN
# =========================================================

def main():
    global driver

    chrome_options = Options()
    chrome_options.add_argument("--start-maximized")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option("useAutomationExtension", False)

    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=chrome_options
    )

    wait = WebDriverWait(driver, 30)

    try:
        # =====================================================
        # OPEN URL
        # =====================================================

        url = "https://fsp.portal.covisint.com/ford_en_US/"

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
            "JFERNANDEZ1",
            "Username"
        )

        enter_text(
            wait,
            By.ID,
            "password",
            "EGCGS@2022",
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

        click_element(
            wait,
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

        north_america = wait.until(
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
        time.sleep(8)

        # =====================================================
        # SEND USER ID AND PASSWORD IN TERMINAL
        # =====================================================

        send_terminal_credentials(driver, "SSFSL11", "EGCGS14")

        # =====================================================
        # ENTER 02 ON NEXT TERMINAL PAGE
        # =====================================================

        logger.info("Waiting for next terminal page after credential submit")

        time.sleep(4)

        logger.info("Sending terminal code 02")

        if not send_terminal_text(driver, "02"):
            raise RuntimeError("Unable to send terminal code 02")

        time.sleep(0.7)

        if not press_terminal_enter(driver):
            raise RuntimeError("Unable to press ENTER after terminal code 02")

        logger.info("Terminal code 02 entered")
        

        # Add a delay of 3 seconds before pressing F5
        time.sleep(3)
        logger.info("Sending F5 key to terminal")
        if not send_terminal_text(driver, Keys.F5):
            raise RuntimeError("Unable to send F5 key after terminal code 02")
        

        # Add a delay of 4 seconds before pressing F11
        time.sleep(4)
        logger.info("Sending F11 key to terminal")
        if not send_terminal_text(driver, Keys.F11):
            raise RuntimeError("Unable to send F11 key after F5")
        time.sleep(5)


        # Switch to the latest window after F11 (it may have opened a new window)
        driver.switch_to.window(driver.window_handles[-1])
        logger.info(f"Switched to window after F11: {driver.current_url}")

        # Add a delay of 4 seconds before pressing '9'
        time.sleep(4)
        logger.info("Sending '9' to terminal")
        if not send_terminal_text(driver, "9"):
            raise RuntimeError("Unable to send '9' after F11")
        time.sleep(0.7)

        logger.info("Pressing ENTER after '9'")
        if not press_terminal_enter(driver):
            raise RuntimeError("Unable to press ENTER after '9'")
        time.sleep(3)

        logger.info("Sending 'B' to terminal")
        if not send_terminal_text(driver, "B"):
            raise RuntimeError("Unable to send 'B' after ENTER")
        time.sleep(2)


        logger.info("Sending '00' to terminal")
        if not send_terminal_text(driver, "00"):
            raise RuntimeError("Unable to send '00' after 'B'")
        time.sleep(0.7)
        logger.info("Pressing ENTER after '00'")
        if not press_terminal_enter(driver):
            raise RuntimeError("Unable to press ENTER after '00'")
        time.sleep(2)

        # Switch to the latest window after ENTER (it may have opened a new window)
        driver.switch_to.window(driver.window_handles[-1])
        logger.info(f"Switched to window after '00' ENTER: {driver.current_url}")
        time.sleep(2)

        # On the next page, move to the first input field in the same row (backward field navigation).
        logger.info("Positioning cursor to first input field in current row on next terminal page")
        if not press_terminal_backtab(driver):
            raise RuntimeError("Unable to position cursor to first input field in row on next page")
        if not press_terminal_backtab(driver):
            raise RuntimeError("Unable to apply additional BACKTAB on next page")
        time.sleep(2)

        # === PASTE EXCEL DATA INTO TERMINAL (D, E, F columns) ===
        excel_path = r"C:\Users\skrishnan1\Videos\Proj\LoginCPARS\Login-CPARS\Input\Ford Receiving - Input.xlsx"
        sheet_name = "Sheet1"  # Update this sheet name if needed
        try:
            workbook = openpyxl.load_workbook(excel_path)
            sheet = workbook[sheet_name]
            for row in sheet.iter_rows(min_row=2, values_only=True):
                values = row[3:6]  # Columns D, E, F (0-based index)
                for value in values:
                    if value is not None:
                        send_terminal_text(driver, str(value))
                        time.sleep(0.5)
                press_terminal_enter(driver)
                time.sleep(1)
            logger.info("Excel values pasted into terminal successfully.")
        except Exception as e:
            logger.error(f"Failed to paste Excel values to terminal: {str(e)}", exc_info=True)
            raise

        logger.info(
            "Automation completed successfully"
        )

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

    finally:

        logger.info("Script finished")
        # driver.quit()


if __name__ == "__main__":

    main()