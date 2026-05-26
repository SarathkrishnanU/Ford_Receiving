"""
Browser management utilities for Selenium WebDriver
"""

import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import os

logger = logging.getLogger(__name__)


class BrowserManager:
    """Manages browser instance and WebDriver"""
    
    def __init__(self, headless=False, wait_time=10):
        self.headless = headless
        self.wait_time = wait_time
        self.driver = None
    
    def create_driver(self):
        """Create and return a new WebDriver instance"""
        try:
            options = Options()
            
            if self.headless:
                options.add_argument("--headless")
            
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-blink-features=AutomationControlled")
            options.add_argument("user-agent=Mozilla/5.0")
            
            self.driver = webdriver.Chrome(options=options)
            logger.info("WebDriver created successfully")
            
            return self.driver
        except Exception as e:
            logger.error(f"Failed to create WebDriver: {str(e)}")
            raise
    
    def close_driver(self):
        """Close the WebDriver instance"""
        if self.driver:
            try:
                self.driver.quit()
                logger.info("WebDriver closed successfully")
            except Exception as e:
                logger.error(f"Error closing WebDriver: {str(e)}")
    
    def navigate_to(self, url):
        """Navigate to a URL"""
        if not self.driver:
            raise ValueError("WebDriver not initialized")
        
        try:
            self.driver.get(url)
            logger.info(f"Navigated to: {url}")
        except Exception as e:
            logger.error(f"Failed to navigate to {url}: {str(e)}")
            raise
    
    def wait_for_element(self, by, value, timeout=None):
        """Wait for an element to be present"""
        if not self.driver:
            raise ValueError("WebDriver not initialized")
        
        timeout = timeout or self.wait_time
        
        try:
            element = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((by, value))
            )
            logger.debug(f"Element found: {by}={value}")
            return element
        except Exception as e:
            logger.error(f"Failed to find element {by}={value}: {str(e)}")
            raise
    
    def wait_for_element_clickable(self, by, value, timeout=None):
        """Wait for an element to be clickable"""
        if not self.driver:
            raise ValueError("WebDriver not initialized")
        
        timeout = timeout or self.wait_time
        
        try:
            element = WebDriverWait(self.driver, timeout).until(
                EC.element_to_be_clickable((by, value))
            )
            logger.debug(f"Element clickable: {by}={value}")
            return element
        except Exception as e:
            logger.error(f"Element not clickable {by}={value}: {str(e)}")
            raise
