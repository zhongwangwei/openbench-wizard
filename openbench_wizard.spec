# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec file for OpenBench Wizard

import sys
import os

block_cipher = None

# Get PySide6 path for platform-specific plugin collection
import PySide6
pyside6_dir = os.path.dirname(PySide6.__file__)

# Collect only essential Qt plugins (platform + styles)
binaries = []
qt_plugins_datas = []

if sys.platform == 'win32':
    # Windows: plugins are in PySide6/plugins/
    plugins_dir = os.path.join(pyside6_dir, 'plugins')
    if os.path.exists(plugins_dir):
        # Platform plugins (required)
        platforms_dir = os.path.join(plugins_dir, 'platforms')
        if os.path.exists(platforms_dir):
            qt_plugins_datas.append((platforms_dir, 'PySide6/plugins/platforms'))
        # Style plugins (optional but recommended)
        styles_dir = os.path.join(plugins_dir, 'styles')
        if os.path.exists(styles_dir):
            qt_plugins_datas.append((styles_dir, 'PySide6/plugins/styles'))
elif sys.platform == 'darwin':
    # macOS: plugins are in PySide6/Qt/plugins/
    plugins_dir = os.path.join(pyside6_dir, 'Qt', 'plugins')
    if os.path.exists(plugins_dir):
        platforms_dir = os.path.join(plugins_dir, 'platforms')
        if os.path.exists(platforms_dir):
            qt_plugins_datas.append((platforms_dir, 'PySide6/Qt/plugins/platforms'))
        styles_dir = os.path.join(plugins_dir, 'styles')
        if os.path.exists(styles_dir):
            qt_plugins_datas.append((styles_dir, 'PySide6/Qt/plugins/styles'))
else:
    # Linux: plugins are in PySide6/Qt/plugins/
    plugins_dir = os.path.join(pyside6_dir, 'Qt', 'plugins')
    if os.path.exists(plugins_dir):
        # Platform plugins (xcb for Linux)
        platforms_dir = os.path.join(plugins_dir, 'platforms')
        if os.path.exists(platforms_dir):
            qt_plugins_datas.append((platforms_dir, 'PySide6/Qt/plugins/platforms'))
        # XCB GL integrations (required for some Linux systems)
        xcbgl_dir = os.path.join(plugins_dir, 'xcbglintegrations')
        if os.path.exists(xcbgl_dir):
            qt_plugins_datas.append((xcbgl_dir, 'PySide6/Qt/plugins/xcbglintegrations'))
        # Platform themes
        themes_dir = os.path.join(plugins_dir, 'platformthemes')
        if os.path.exists(themes_dir):
            qt_plugins_datas.append((themes_dir, 'PySide6/Qt/plugins/platformthemes'))

# Explicit list of all hidden imports
hidden_imports = [
    # PySide6
    'PySide6.QtCore',
    'PySide6.QtGui',
    'PySide6.QtWidgets',
    'PySide6.QtNetwork',
    'shiboken6',
    # Third party
    'yaml',
    'psutil',
    # Paramiko (SSH)
    'paramiko',
    'paramiko.transport',
    'paramiko.sftp',
    'paramiko.sftp_client',
    'paramiko.rsakey',
    'paramiko.ecdsakey',
    'paramiko.ed25519key',
    # Cryptography (required by paramiko)
    'cryptography',
    'cryptography.hazmat.backends.openssl',
    'cryptography.hazmat.bindings.openssl',
    'cryptography.hazmat.primitives.ciphers',
    # Core modules
    'core',
    'core.config_manager',
    'core.runner',
    # UI modules
    'ui',
    'ui.main_window',
    'ui.wizard_controller',
    # UI pages
    'ui.pages',
    'ui.pages.base_page',
    'ui.pages.page_general',
    'ui.pages.page_evaluation',
    'ui.pages.page_metrics',
    'ui.pages.page_scores',
    'ui.pages.page_comparisons',
    'ui.pages.page_statistics',
    'ui.pages.page_ref_data',
    'ui.pages.page_sim_data',
    'ui.pages.page_preview',
    'ui.pages.page_run_monitor',
    # UI widgets
    'ui.widgets',
    'ui.widgets.path_selector',
    'ui.widgets.checkbox_group',
    'ui.widgets.yaml_preview',
    'ui.widgets.progress_dashboard',
    'ui.widgets.data_source_editor',
    'ui.widgets.model_definition_editor',
]

# Data files to include
datas = [
    ('ui/styles', 'ui/styles'),
] + qt_plugins_datas

# Exclude heavy packages not needed by the app (avoids build issues)
excludes = [
    'numpy', 'matplotlib', 'scipy', 'pandas',
    'xarray', 'dask', 'pyarrow', 'PIL', 'tkinter',
]

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=[],
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='OpenBench_Wizard',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
