# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['login_cpars.py'],
    pathex=['.'],
    binaries=[],
    datas=[],
    hiddenimports=[
        # selenium
        'selenium',
        'selenium.webdriver',
        'selenium.webdriver.chrome',
        'selenium.webdriver.chrome.webdriver',
        'selenium.webdriver.chrome.service',
        'selenium.webdriver.chrome.options',
        'selenium.webdriver.chrome.remote_connection',
        'selenium.webdriver.remote.webdriver',
        'selenium.webdriver.remote.remote_connection',
        'selenium.webdriver.remote.command',
        'selenium.webdriver.common.by',
        'selenium.webdriver.common.keys',
        'selenium.webdriver.common.action_chains',
        'selenium.webdriver.common.desired_capabilities',
        'selenium.webdriver.support.ui',
        'selenium.webdriver.support.expected_conditions',
        'selenium.common.exceptions',
        # webdriver_manager
        'webdriver_manager',
        'webdriver_manager.chrome',
        # openpyxl
        'openpyxl',
        'openpyxl.styles',
        'openpyxl.utils',
        # pandas
        'pandas',
        'pandas.io.formats.excel',
        # pytesseract
        'pytesseract',
        # PIL / Pillow
        'PIL',
        'PIL.Image',
        'PIL.ImageEnhance',
        'PIL.ImageChops',
        # cv2
        'cv2',
        # numpy
        'numpy',
        # src package
        'src',
        'src.browser',
        'src.login',
        'src.screenshot',
        'src.terminal_utils',
        'src.excel_utils',
        'src.ocr_runner',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    name='LoginCPARS',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,   # Keep True so the log output is visible
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='LoginCPARS',
)
