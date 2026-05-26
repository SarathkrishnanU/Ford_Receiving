# LoginCPARS Project Instructions

This is a Python web automation project for logging into CPARS and capturing screenshots.

## Project Overview
- **Purpose**: Automate login to CPARS system and capture screenshots
- **Technology**: Python, Selenium WebDriver
- **Python Version**: 3.8+

## Setup and Installation

### Prerequisites
- Python 3.8 or higher
- pip (Python package manager)
- ChromeDriver or compatible WebDriver

### Installation Steps

1. Create a Python virtual environment:
   ```bash
   python -m venv venv
   ```

2. Activate the virtual environment:
   - **Windows**: `venv\Scripts\activate`
   - **macOS/Linux**: `source venv/bin/activate`

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Configure environment variables:
   - Copy `.env.example` to `.env`
   - Update `.env` with your CPARS credentials and settings

### Running the Project

```bash
python login_cpars.py
```

## Project Structure

```
Login-CPARS/
├── .env.example          # Environment variables template
├── .env                  # Local environment variables (not committed)
├── .gitignore            # Git ignore file
├── requirements.txt      # Python dependencies
├── README.md             # Project documentation
├── login_cpars.py        # Main automation script
├── src/                  # Source code modules
│   ├── __init__.py
│   ├── browser.py        # Browser management
│   ├── login.py          # Login logic
│   └── screenshot.py     # Screenshot utilities
└── screenshots/          # Output screenshots directory
```

## Key Features

- Automated login to CPARS system
- Browser automation with Selenium
- Screenshot capture functionality
- Configurable via environment variables
- Error handling and logging

## Development

To contribute or modify:
1. Activate the virtual environment
2. Install development dependencies
3. Run tests and validation

## Troubleshooting

- **WebDriver issues**: Make sure ChromeDriver version matches your Chrome browser
- **Credential issues**: Verify `.env` file has correct credentials
- **Screenshot path errors**: Ensure `screenshots/` directory exists

## Requirements

See `requirements.txt` for all dependencies.
