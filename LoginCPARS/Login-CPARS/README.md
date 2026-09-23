# LoginCPARS Automation App

LoginCPARS automates CPARS portal login, IBM HOD IMS5 navigation, receipt-history screenshot capture, row completion tracking in Excel, and glyph-based OCR extraction into `OCR_Extracted.xlsx`.

## What Is Included

- `login_cpars_v2.py` - main automation script.
- `run_app.py` - bootstrap launcher that creates `.venv`, installs packages, validates OCR/glyph files, then starts the app.
- `Start-LoginCPARS.bat` - Windows double-click launcher for remote desktops or fresh machines.
- `Build-LoginCPARS.bat` - optional PyInstaller build wrapper.
- `src/glyph_ocr.py` and `src/glyph_templates.npz` - fixed-grid IBM 3270 glyph OCR engine and trained glyph template library.
- `src/ocr_runner.py` - screenshot OCR parser and Excel summary writer.
- `tools/build_glyph_templates.py` - utility for rebuilding glyph templates if the terminal font, zoom, or resolution changes.

## Remote Server Requirements

Use a Windows remote desktop/server session with a visible GUI. The automation drives Microsoft Edge and uses file-selection dialogs, so it cannot run as a headless background service.

Install these once on the server:

- Python 3.10 or newer.
- Microsoft Edge.
- Network access to CPARS and to Python package downloads from PyPI.

The app installs Python packages automatically into a local `.venv` folder. Edge WebDriver is handled by `webdriver-manager`, with Selenium Manager as fallback.

## Configuration

1. Copy `.env.example` to `.env` in the same folder as `run_app.py`.
2. Fill in the values:

```env
PORTAL_USERNAME=your_portal_username
PORTAL_PASSWORD=your_portal_password
TERMINAL_USERNAME=your_terminal_username
TERMINAL_PASSWORD=your_terminal_password
CPARS_URL=https://fsp.portal.covisint.com/ford_en_US/
```

Do not commit or share `.env`.

## Run The App

On Windows, double-click:

```bat
Start-LoginCPARS.bat
```

Or run from PowerShell:

```powershell
python run_app.py
```

On first run, the launcher will:

1. Create `.venv` if it does not exist.
2. Upgrade `pip`.
3. Install every package from `requirements.txt`, including Selenium, WebDriver Manager, Excel libraries, Pillow, pandas, NumPy, OpenCV, and PyInstaller.
4. Validate the OCR chain by importing OpenCV/NumPy/pandas/openpyxl/Pillow/Selenium and loading `src/glyph_templates.npz`.
5. Start `login_cpars_v2.py`.

After startup, select the input Excel file and output screenshot folder when prompted. The app marks completed rows in the workbook, saves cropped terminal screenshots, then runs glyph OCR and writes `OCR_Extracted.xlsx` in the selected output folder.

## Build An EXE

To create a distributable executable folder, double-click:

```bat
Build-LoginCPARS.bat
```

The build script bootstraps dependencies first, validates the glyph OCR templates, then runs PyInstaller with `login_cpars_v2.spec`. The output is:

```text
dist\LoginCPARS_v2\LoginCPARS_v2.exe
```

The spec bundles the `src` folder, including `src/glyph_templates.npz`, so OCR/glyph recognition is included in the EXE build.

## OCR And Glyph Notes

This project does not use Tesseract. CPARS terminal screenshots are recognised using the fixed 80x24 IBM HOD character grid and the trained glyph library in `src/glyph_templates.npz`.

Only rebuild the glyph library if the IBM terminal font, browser zoom, emulator zoom, or remote desktop display scaling changes enough to affect recognition. The rebuild workflow is documented in `tools/build_glyph_templates.py`:

```powershell
.\.venv\Scripts\python.exe tools\build_glyph_templates.py --cluster <folder-of-screenshots>
# edit LABELS in tools\build_glyph_templates.py using _glyphwork\contact_sheet.png
.\.venv\Scripts\python.exe tools\build_glyph_templates.py --emit
```

## Troubleshooting

- If startup fails before the app opens, run `python run_app.py --bootstrap-only` from PowerShell and review the printed package or glyph validation error.
- If OCR fails, confirm `src/glyph_templates.npz` exists and the selected output folder contains readable `.png`, `.jpg`, or `.jpeg` screenshots.
- If the browser cannot start, confirm Microsoft Edge is installed and the server can download WebDriver packages.
- If package installation fails, confirm internet access to PyPI or preinstall packages into `.venv` from an approved internal package mirror.
- Review `LoginCPARS.log` for portal, terminal, screenshot, Excel, and OCR details.