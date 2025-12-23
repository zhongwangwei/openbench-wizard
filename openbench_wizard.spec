# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec file for OpenBench Wizard

import os
import sys
import PySide6

block_cipher = None

# Get PySide6 installation path for platform plugins
pyside6_path = os.path.dirname(PySide6.__file__)

# Platform-specific Qt plugins
qt_plugins = []
if sys.platform == 'darwin':
    # macOS: cocoa plugin
    qt_plugins = [
        (os.path.join(pyside6_path, 'Qt', 'plugins', 'platforms'), 'PySide6/Qt/plugins/platforms'),
        (os.path.join(pyside6_path, 'Qt', 'plugins', 'styles'), 'PySide6/Qt/plugins/styles'),
    ]
elif sys.platform == 'linux':
    # Linux: xcb plugin
    qt_plugins = [
        (os.path.join(pyside6_path, 'Qt', 'plugins', 'platforms'), 'PySide6/Qt/plugins/platforms'),
        (os.path.join(pyside6_path, 'Qt', 'plugins', 'xcbglintegrations'), 'PySide6/Qt/plugins/xcbglintegrations'),
        (os.path.join(pyside6_path, 'Qt', 'plugins', 'platformthemes'), 'PySide6/Qt/plugins/platformthemes'),
    ]
elif sys.platform == 'win32':
    # Windows: windows plugin
    qt_plugins = [
        (os.path.join(pyside6_path, 'plugins', 'platforms'), 'PySide6/plugins/platforms'),
        (os.path.join(pyside6_path, 'plugins', 'styles'), 'PySide6/plugins/styles'),
    ]

# Filter out non-existent paths
qt_plugins = [(src, dst) for src, dst in qt_plugins if os.path.exists(src)]

# Explicit list of all hidden imports
hidden_imports = [
    # PySide6
    'PySide6.QtCore',
    'PySide6.QtGui',
    'PySide6.QtWidgets',
    # Third party
    'yaml',
    'psutil',
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
] + qt_plugins

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=[],
    datas=datas,
    hiddenimports=hidden_imports,
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
