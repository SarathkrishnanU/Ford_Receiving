"""
Screenshot utilities for capturing and processing images
"""

import logging
import os
from datetime import datetime
from PIL import Image
import io

logger = logging.getLogger(__name__)


class ScreenshotManager:
    """Manages screenshot capture and storage"""
    
    def __init__(self, screenshot_dir="screenshots"):
        self.screenshot_dir = screenshot_dir
        self._ensure_directory()
    
    def _ensure_directory(self):
        """Ensure screenshot directory exists"""
        if not os.path.exists(self.screenshot_dir):
            try:
                os.makedirs(self.screenshot_dir)
                logger.info(f"Created screenshot directory: {self.screenshot_dir}")
            except Exception as e:
                logger.error(f"Failed to create screenshot directory: {str(e)}")
                raise
    
    def take_screenshot(self, driver, name=None, full_page=True):
        """
        Take a screenshot of the current page
        
        Args:
            driver: Selenium WebDriver instance
            name (str): Optional name for the screenshot
            full_page (bool): Capture full page or just viewport
            
        Returns:
            str: Path to saved screenshot
        """
        try:
            if not name:
                name = f"screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            # Ensure name is valid for filename
            filename = f"{name}.png"
            filepath = os.path.join(self.screenshot_dir, filename)
            
            if full_page:
                # For Firefox and Chrome, save full page
                driver.save_screenshot(filepath)
            else:
                # Save viewport only
                driver.save_screenshot(filepath)
            
            logger.info(f"Screenshot saved: {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"Failed to take screenshot: {str(e)}")
            raise
    
    def take_element_screenshot(self, driver, element, name=None):
        """
        Take a screenshot of a specific element
        
        Args:
            driver: Selenium WebDriver instance
            element: WebElement to capture
            name (str): Optional name for the screenshot
            
        Returns:
            str: Path to saved screenshot
        """
        try:
            if not name:
                name = f"element_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            filename = f"{name}.png"
            filepath = os.path.join(self.screenshot_dir, filename)
            
            element.screenshot(filepath)
            
            logger.info(f"Element screenshot saved: {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"Failed to take element screenshot: {str(e)}")
            raise
    
    def list_screenshots(self):
        """List all screenshots in the directory"""
        try:
            screenshots = [f for f in os.listdir(self.screenshot_dir) 
                          if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
            logger.info(f"Found {len(screenshots)} screenshots")
            return screenshots
        except Exception as e:
            logger.error(f"Failed to list screenshots: {str(e)}")
            return []
    
    def get_screenshot_info(self, filename):
        """Get information about a screenshot"""
        try:
            filepath = os.path.join(self.screenshot_dir, filename)
            
            if not os.path.exists(filepath):
                raise FileNotFoundError(f"Screenshot not found: {filename}")
            
            file_size = os.path.getsize(filepath)
            created_time = os.path.getctime(filepath)
            
            # Try to get image dimensions
            try:
                img = Image.open(filepath)
                width, height = img.size
            except:
                width, height = None, None
            
            info = {
                'filename': filename,
                'path': filepath,
                'size_bytes': file_size,
                'created_timestamp': created_time,
                'dimensions': (width, height) if width else None
            }
            
            return info
            
        except Exception as e:
            logger.error(f"Failed to get screenshot info: {str(e)}")
            raise
