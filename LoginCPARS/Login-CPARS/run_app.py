"""Bootstrap and run the LoginCPARS application.

This file intentionally uses only the Python standard library so it can run in
a fresh environment before third-party packages are installed.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


APP_SCRIPT = "login_cpars_v2.py"
VENV_DIR = ".venv"
REQUIREMENTS_FILE = "requirements.txt"
GLYPH_TEMPLATE_FILE = Path("src") / "glyph_templates.npz"
MIN_PYTHON = (3, 10)


def _app_dir() -> Path:
    return Path(__file__).resolve().parent


def _python_exe(venv_dir: Path) -> Path:
    if os.name == "nt":
        return venv_dir / "Scripts" / "python.exe"
    return venv_dir / "bin" / "python"


def _run(command: list[str], cwd: Path) -> None:
    print("\n> " + " ".join(command), flush=True)
    subprocess.check_call(command, cwd=str(cwd))


def _ensure_required_files(app_dir: Path) -> None:
    if sys.version_info < MIN_PYTHON:
        required = ".".join(str(part) for part in MIN_PYTHON)
        current = ".".join(str(part) for part in sys.version_info[:3])
        raise RuntimeError(
            f"Python {required} or newer is required. Current Python is {current}."
        )

    missing = []
    for relative_path in (APP_SCRIPT, REQUIREMENTS_FILE, GLYPH_TEMPLATE_FILE):
        if not (app_dir / relative_path).exists():
            missing.append(str(relative_path))

    if missing:
        raise FileNotFoundError(
            "Required application file(s) are missing: " + ", ".join(missing)
        )


def _ensure_virtualenv(app_dir: Path) -> Path:
    venv_dir = app_dir / VENV_DIR
    python_exe = _python_exe(venv_dir)

    if not python_exe.exists():
        print(f"Creating Python virtual environment: {venv_dir}", flush=True)
        _run([sys.executable, "-m", "venv", str(venv_dir)], app_dir)

    return python_exe


def _install_dependencies(app_dir: Path, python_exe: Path) -> None:
    requirements = app_dir / REQUIREMENTS_FILE
    _run([str(python_exe), "-m", "pip", "install", "--upgrade", "pip"], app_dir)
    _run([str(python_exe), "-m", "pip", "install", "-r", str(requirements)], app_dir)


def _validate_runtime(app_dir: Path, python_exe: Path) -> None:
    validation_code = "\n".join(
        [
            "import cv2, numpy, openpyxl, pandas, PIL, selenium, webdriver_manager",
            "from src.glyph_ocr import GlyphLibrary",
            "GlyphLibrary.load()",
            "print('Runtime validation passed: packages and glyph OCR templates are available.')",
        ]
    )
    _run([str(python_exe), "-c", validation_code], app_dir)


def main() -> int:
    app_dir = _app_dir()
    _ensure_required_files(app_dir)
    python_exe = _ensure_virtualenv(app_dir)
    _install_dependencies(app_dir, python_exe)
    _validate_runtime(app_dir, python_exe)

    if "--bootstrap-only" in sys.argv[1:]:
        print("Bootstrap complete. Dependencies and OCR glyph templates are ready.")
        return 0

    _run([str(python_exe), str(app_dir / APP_SCRIPT)], app_dir)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except subprocess.CalledProcessError as exc:
        print(f"\nCommand failed with exit code {exc.returncode}.", file=sys.stderr)
        raise SystemExit(exc.returncode)
    except Exception as exc:
        print(f"\nStartup failed: {exc}", file=sys.stderr)
        raise SystemExit(1)