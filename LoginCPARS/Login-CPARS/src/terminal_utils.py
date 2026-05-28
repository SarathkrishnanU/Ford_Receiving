import time
import logging
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

logger = logging.getLogger(__name__)

TERMINAL_CONTEXT_INDEX = None

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
        strategies = ["active", "body", "action", "focus_then_action"]
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
        strategies = ["active", "body", "action", "focus_then_action"]
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
