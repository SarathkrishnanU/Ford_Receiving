# LoginCPARS - CPARS Automation Tool

A Python-based web automation tool for logging into the CPARS system and capturing screenshots.

## Features

- **Automated Login**: Securely logs into CPARS using credentials
- **Screenshot Capture**: Takes screenshots at various stages
- **Error Handling**: Robust error handling with detailed logging
- **Configurable**: Easy environment variable configuration
- **Browser Automation**: Uses Selenium for reliable browser control

## Quick Start

### Prerequisites

- Python 3.8 or higher
- Google Chrome browser (for default configuration)
- ChromeDriver matching your Chrome version

### Installation

1. Clone or download this project
2. Navigate to the project directory
3. Create a virtual environment:
   ```bash
   python -m venv venv
   ```
4. Activate it:
   - Windows: `venv\Scripts\activate`
   - macOS/Linux: `source venv/bin/activate`
5. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### Configuration

1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```
2. Edit `.env` and add your CPARS credentials:
   ```
   CPARS_USERNAME=your_username
   CPARS_PASSWORD=your_password
   CPARS_URL=https://your-cpars-url.com
   ```

### Running

```bash
python login_cpars.py
```

## Project Structure

```
Login-CPARS/
├── .env.example              # Template for environment variables
├── .gitignore               # Git ignore rules
├── requirements.txt         # Python dependencies
├── README.md                # This file
├── login_cpars.py           # Main entry point
├── src/
│   ├── __init__.py
│   ├── browser.py           # Browser management utilities
│   ├── login.py             # Login automation logic
│   └── screenshot.py        # Screenshot utilities
└── screenshots/             # Output directory for screenshots
```

## Usage Example

```python
from src.browser import BrowserManager
from src.login import CPARSLogin
from src.screenshot import ScreenshotManager

# Initialize browser
browser = BrowserManager()
driver = browser.create_driver()

# Login to CPARS
login = CPARSLogin(driver)
login.login_to_cpars("username", "password", "https://cpars.url")

# Take screenshot
screenshot = ScreenshotManager()
screenshot.take_screenshot(driver, "login_success")

# Cleanup
browser.close_driver(driver)
```

## Troubleshooting

### WebDriver Not Found
- Download ChromeDriver from: https://chromedriver.chromium.org/
- Ensure version matches your Chrome browser
- Add to PATH or specify path in configuration

### Login Fails
- Verify credentials in `.env` file
- Check CPARS_URL is correct
- Ensure the website is accessible
- Check browser console for JavaScript errors

### Screenshot Issues
- Verify `screenshots/` directory exists
- Check write permissions
- Ensure paths are correct in `.env`

## Dependencies

- **selenium**: Web browser automation
- **python-dotenv**: Environment variable management
- **Pillow**: Image processing
- **requests**: HTTP library

See `requirements.txt` for versions.

## Contributing

Feel free to submit issues and enhancement requests!

## License

This project is for authorized CPARS users only.

## Support

For issues or questions, check the logs and review the troubleshooting section above.
