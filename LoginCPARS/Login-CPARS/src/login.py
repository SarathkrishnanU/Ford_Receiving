"""
CPARS Login automation module
"""

import logging
from selenium.webdriver.common.by import By
import time

logger = logging.getLogger(__name__)


class CPARSLogin:
    """Handles CPARS login automation"""
    
    def __init__(self, browser_manager):
        self.browser_manager = browser_manager
        self.driver = browser_manager.driver
    
    def login_to_cpars(self, username, password, cpars_url):
        """
        Automate login to CPARS system
        
        Args:
            username (str): CPARS username
            password (str): CPARS password
            cpars_url (str): CPARS login URL
        """
        try:
            logger.info("Starting CPARS login process...")
            
            # Navigate to login page
            self.browser_manager.navigate_to(cpars_url)
            time.sleep(2)
            
            # Wait for username field and enter credentials
            username_field = self.browser_manager.wait_for_element(
                By.ID, "username"
            )
            username_field.clear()
            username_field.send_keys(username)
            logger.info("Username entered")
            
            # Enter password
            password_field = self.driver.find_element(By.ID, "password")
            password_field.clear()
            password_field.send_keys(password)
            logger.info("Password entered")
            
            # Click login button
            login_button = self.browser_manager.wait_for_element_clickable(
                By.ID, "loginButton"
            )
            login_button.click()
            logger.info("Login button clicked")
            
            # Wait for page redirect
            time.sleep(3)
            
            logger.info("Login successful")
            return True
            
        except Exception as e:
            logger.error(f"Login failed: {str(e)}")
            raise
    
    def verify_login(self):
        """
        Verify if login was successful by checking for expected elements
        
        Returns:
            bool: True if login successful, False otherwise
        """
        try:
            # Check for dashboard or home element that appears after login
            # Modify this based on actual CPARS page structure
            dashboard = self.driver.find_elements(By.CLASS_NAME, "dashboard")
            
            if dashboard:
                logger.info("Login verification successful")
                return True
            else:
                logger.warning("Could not verify login state")
                return False
                
        except Exception as e:
            logger.error(f"Error verifying login: {str(e)}")
            return False
    
    def logout(self):
        """Logout from CPARS"""
        try:
            # Find and click logout button (modify selector as needed)
            logout_button = self.driver.find_element(By.CLASS_NAME, "logout")
            logout_button.click()
            logger.info("Logged out successfully")
            return True
        except Exception as e:
            logger.error(f"Logout failed: {str(e)}")
            return False
